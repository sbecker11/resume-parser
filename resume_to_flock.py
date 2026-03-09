#!/usr/bin/env python3
"""
resume-to-flock: Parse resume (DOCX/PDF) into flock-of-postcards jobs.mjs, skills.mjs, other-sections.mjs, resume.html, and resume_template.html.

Usage:
  python resume_to_flock.py <resume.docx|resume.pdf> [--output-dir PATH] [--no-llm] [--no-enrich]

  --output-dir   Where to write jobs.mjs, skills.mjs, other-sections.mjs, resume.html, resume_template.html
  --no-llm       Skip LLM calls; use extraction only (for testing)
  --no-enrich    Skip LLM skill URL enrichment
  --provider     Force LLM_PROVIDER (anthropic); requires ANTHROPIC_API_KEY
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from script directory (reliable regardless of cwd)
load_dotenv(Path(__file__).resolve().parent / ".env")

# Add parent for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extractors import extract_text
from parsers import (
    parse_jobs_with_llm,
    parse_resume_sections,
    extract_skills_from_text,
    enrich_skills_with_llm,
    categorize_skills_with_llm,
    build_categories_dict,
    assign_skill_ids,
    jobs_to_flock_format,
    get_llm_provider,
)


def _default_output_dir() -> Path:
    """Default output: flock-of-postcards/static_content if it exists nearby."""
    tool_dir = Path(__file__).resolve().parent
    # Check workspace-resume, workspace-flock, or cwd
    candidates = [
        Path.home() / "workspace-flock" / "flock-of-postcards" / "static_content",
        tool_dir.parent.parent / "flock-of-postcards" / "static_content",
        tool_dir.parent / "flock-of-postcards" / "static_content",
        Path.cwd() / "static_content",
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path.cwd()


def _write_jobs_mjs(jobs: dict[str, dict], out_dir: Path) -> Path:
    """Write jobs dict keyed by jobID: { \"0\": job0, \"1\": job1, ... }."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "jobs.mjs"
    with open(path, "w", encoding="utf-8") as f:
        f.write("const jobs = ")
        f.write(json.dumps(jobs, ensure_ascii=False))
        f.write(";")
    return path


def _write_skills_mjs(skills_by_id: dict[str, dict], out_dir: Path) -> Path:
    """Write skills dict keyed by skillID: { \"skillID\": { \"name\": \"Display Name\", \"url\", \"img\", \"categoryIDs\", \"jobIDs\" }, ... }."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "skills.mjs"
    with open(path, "w", encoding="utf-8") as f:
        f.write("const skills = ")
        f.write(json.dumps(skills_by_id, ensure_ascii=False))
        f.write(";")
    return path


def _write_categories_mjs(categories: dict[str, dict], out_dir: Path) -> Path:
    """Write categories dict (categoryID -> { name, skillIDs }) to categories.mjs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "categories.mjs"
    with open(path, "w", encoding="utf-8") as f:
        f.write("const categories = ")
        f.write(json.dumps(categories, ensure_ascii=False))
        f.write(";")
    return path


def _write_other_sections_mjs(meta: dict, out_dir: Path) -> Path:
    """Write contact, summary, certifications, skills, other_sections to other-sections.mjs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "other-sections.mjs"
    with open(path, "w", encoding="utf-8") as f:
        f.write("const otherSections = ")
        f.write(json.dumps(meta, ensure_ascii=False))
        f.write(";")
    return path


def _template_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def _linkify(text: str) -> str:
    """Wrap valid http(s) URLs in text with <a href="...">...</a>. Returns markup-safe string."""
    import re
    from markupsafe import Markup, escape
    if not text:
        return ""
    # Match http:// or https:// URLs (no spaces or angle brackets)
    pattern = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
    parts = pattern.split(text)
    matches = pattern.findall(text)
    result = escape(parts[0])
    for i, url in enumerate(matches):
        safe_url = escape(url)
        result += Markup('<a href="') + safe_url + Markup('">') + safe_url + Markup("</a>")
        result += escape(parts[i + 1])
    return Markup(result)


def _render_resume_html(
    flock_jobs: list[dict],
    skills: dict,
    resume_meta: dict,
    categories: dict[str, dict[str, str]],
    out_dir: Path,
) -> tuple[Path, Path]:
    """Render resume from template; write resume.html and copy template to output. Returns (resume_path, template_copy_path)."""
    from jinja2 import Environment, FileSystemLoader
    out_dir.mkdir(parents=True, exist_ok=True)
    templates_path = _template_dir()
    env = Environment(loader=FileSystemLoader(str(templates_path)))
    env.filters["linkify"] = lambda s: _linkify(s) if s else ""
    template = env.get_template("resume.html")
    contact = resume_meta.get("contact") or {}
    title = resume_meta.get("title") or ""
    summary = resume_meta.get("summary") or ""
    certifications = resume_meta.get("certifications") or []
    other_sections = resume_meta.get("other_sections") or []

    def _description_bullets(desc: str) -> list[str]:
        if not desc or not desc.strip():
            return []
        text = desc.strip()
        if "•" in text:
            return [p.strip() for p in text.split("•") if p.strip()]
        parts = [p.strip() for p in text.split(". ") if p.strip()]
        return [p if p.endswith(".") else p + "." for p in parts]

    jobs_with_bullets = [
        {**job, "description_bullets": _description_bullets(job.get("Description") or "")}
        for job in flock_jobs
    ]

    # Group skills by category for template: list of { "name": category name, "skills": [skill names] }
    skills_by_category: list[dict] = []
    for cid, cat in categories.items():
        names = [name for name, data in skills.items() if cid in data.get("categoryIDs", [])]
        if names:
            skills_by_category.append({"name": cat["name"], "skills": names})
    skills_without_category = [name for name, data in skills.items() if not data.get("categoryIDs")]
    if skills_without_category:
        skills_by_category.append({"name": "Other", "skills": skills_without_category})
    html = template.render(
        contact=contact,
        title=title,
        summary=summary,
        jobs=jobs_with_bullets,
        skills=skills,
        categories=categories,
        skills_by_category=skills_by_category,
        certifications=certifications,
        other_sections=other_sections,
    )
    resume_path = out_dir / "resume.html"
    with open(resume_path, "w", encoding="utf-8") as f:
        f.write(html)
    template_src = templates_path / "resume.html"
    template_dest = out_dir / "resume_template.html"
    if template_src.exists():
        import shutil
        shutil.copy2(template_src, template_dest)
    return resume_path, template_dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse resume into flock-of-postcards data")
    parser.add_argument("resume", type=Path, help="Path to resume.docx or resume.pdf")
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: flock-of-postcards/static_content or cwd)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM; extract text only (no job parsing)",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip LLM skill URL enrichment",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic"],
        default=None,
        help="Force LLM_PROVIDER (anthropic); requires ANTHROPIC_API_KEY",
    )
    args = parser.parse_args()

    if not args.resume.exists():
        print(f"Error: File not found: {args.resume}", file=sys.stderr)
        return 1

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    out_dir = args.output_dir or _default_output_dir()
    print(f"Output directory: {out_dir}")

    # Phase 1: Extract text
    print("Extracting text...")
    raw_text = extract_text(args.resume)
    if not raw_text.strip():
        print("Error: No text extracted from document", file=sys.stderr)
        return 1
    print(f"Extracted {len(raw_text)} characters")

    if args.no_llm:
        print("--no-llm: Skipping job parsing. Extracted text (first 500 chars):")
        print(raw_text[:500])
        return 0

    # Phase 2: Parse jobs with LLM
    try:
        provider = get_llm_provider()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"Parsing jobs with LLM ({provider})...")
    try:
        jobs = parse_jobs_with_llm(raw_text)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"Parsed {len(jobs)} jobs")

    # Parse contact, summary, certifications, skills, other sections
    resume_meta: dict = {}
    print("Parsing resume sections (contact, summary, certifications, skills, other)...")
    try:
        resume_meta = parse_resume_sections(raw_text)
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"Warning: could not parse resume sections: {e}", file=sys.stderr)

    # Convert to flock format
    flock_jobs = jobs_to_flock_format(jobs)

    # Phase 3: Extract skills per job so we can assign jobIDs
    skills: dict = {}
    for i, job in enumerate(flock_jobs):
        desc = (job.get("Description") or "").strip()
        job_skills = extract_skills_from_text(desc)
        for name, data in job_skills.items():
            if name not in skills:
                skills[name] = {"url": data["url"], "img": data["img"], "jobIDs": [i]}
            else:
                if i not in skills[name]["jobIDs"]:
                    skills[name]["jobIDs"].append(i)
                if data["url"] and not skills[name]["url"]:
                    skills[name]["url"] = data["url"]
                if data["img"] and not skills[name]["img"]:
                    skills[name]["img"] = data["img"]
    print(f"Extracted {len(skills)} skills from descriptions")

    # Add resume-level skills (from skills section); no job reference -> jobIDs []
    for name in resume_meta.get("skills") or []:
        name = str(name).strip()
        if name and name not in skills:
            skills[name] = {"url": "", "img": "", "jobIDs": []}

    if not args.no_enrich and skills:
        print("Enriching skills with LLM...")
        skills = enrich_skills_with_llm(skills)

    print("Categorizing skills with LLM...")
    skills = categorize_skills_with_llm(skills)
    categories = build_categories_dict(skills)
    assign_skill_ids(skills)

    # Add skillIDs list to each category (skills that belong to that category)
    for cid, cat in categories.items():
        cat["skillIDs"] = [
            data["id"]
            for name, data in skills.items()
            if cid in data.get("categoryIDs", [])
        ]

    # Each job gets optional skillIDs (skill ids for skills that appear in that job)
    for job in flock_jobs:
        job["skillIDs"] = [
            data["id"]
            for name, data in skills.items()
            if job["index"] in data.get("jobIDs", [])
        ]
    jobs_by_id: dict[str, dict] = {str(job["index"]): job for job in flock_jobs}
    # Skills output keyed by skillID (slug), with "name" as display name; matches jobs/categories structure
    skills_by_id: dict[str, dict] = {
        data["id"]: {
            "name": name,
            "url": data.get("url", ""),
            "img": data.get("img", ""),
            "categoryIDs": data.get("categoryIDs", []),
            "jobIDs": data.get("jobIDs", []),
        }
        for name, data in skills.items()
    }

    # Write output: jobs.mjs, skills.mjs, categories.mjs, other-sections.mjs, resume.html, resume_template.html
    jobs_path = _write_jobs_mjs(jobs_by_id, out_dir)
    skills_path = _write_skills_mjs(skills_by_id, out_dir)
    categories_path = _write_categories_mjs(categories, out_dir)
    other_path = _write_other_sections_mjs(resume_meta, out_dir)
    resume_path, template_path = _render_resume_html(flock_jobs, skills, resume_meta, categories, out_dir)
    print(f"Wrote {jobs_path}")
    print(f"Wrote {skills_path}")
    print(f"Wrote {categories_path}")
    print(f"Wrote {other_path}")
    print(f"Wrote {resume_path}")
    print(f"Wrote {template_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
