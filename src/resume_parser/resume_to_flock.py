#!/usr/bin/env python3
"""
resume-to-flock: Parse resume (DOCX/PDF) into flock-of-postcards jobs.json, skills.json, categories.json, other-sections.json.

Usage:
  resume-to-flock <resume.docx|resume.pdf> [--output-dir PATH] [--no-llm] [--no-enrich] [--render]

  --output-dir   Where to write .json files (and optional resume copy)
  --no-llm       Skip LLM calls; use extraction only (for testing)
  --no-enrich    Skip LLM skill URL enrichment
  --no-merge     Skip skill merge step (non-interactive)
  --provider     Force LLM_PROVIDER (anthropic); requires ANTHROPIC_API_KEY
  --render       After writing .json, run render-resume-html to generate resume.html
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from cwd (consumer's project) or repo root when developing
load_dotenv(Path.cwd() / ".env")

from .extractors import extract_text
from .skill_merge import run_merge_interactive
from .parsers import (
    parse_jobs_with_llm,
    parse_resume_sections,
    extract_skills_from_text,
    expand_skill_parens,
    expand_parens_in_text,
    enrich_skills_with_llm,
    categorize_skills_with_llm,
    build_categories_dict,
    assign_skill_ids,
    jobs_to_flock_format,
    get_llm_provider,
)


def _default_output_dir() -> Path:
    """Default output: flock-of-postcards/static_content if it exists nearby."""
    tool_dir = Path(__file__).resolve().parent  # package dir when installed
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


def _write_json(path: Path, data: dict | list, out_dir: Path) -> Path:
    """Write data as UTF-8 JSON (resume-flock format)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _write_jobs_json(jobs: dict[str, dict], out_dir: Path) -> Path:
    """Write jobs dict keyed by jobID (resume-flock format)."""
    return _write_json(out_dir / "jobs.json", jobs, out_dir)


def _write_skills_json(skills_by_id: dict[str, dict], out_dir: Path) -> Path:
    """Write skills dict keyed by skillID (resume-flock format)."""
    return _write_json(out_dir / "skills.json", skills_by_id, out_dir)


def _write_categories_json(categories: dict[str, dict], out_dir: Path) -> Path:
    """Write categories dict (resume-flock format)."""
    return _write_json(out_dir / "categories.json", categories, out_dir)


def _build_other_sections_for_flock(resume_meta: dict) -> dict:
    """Transform parser meta to resume-flock otherSections schema."""
    contact = resume_meta.get("contact") or {}
    title = (resume_meta.get("title") or "").strip()
    summary = (resume_meta.get("summary") or "").strip()
    # Certifications: {name, issuer, date} -> {name, url?, description?}
    certs = []
    for c in resume_meta.get("certifications") or []:
        name = (c.get("name") or "").strip()
        issuer = (c.get("issuer") or "").strip()
        date = (c.get("date") or "").strip()
        desc = " ".join([x for x in [issuer, date] if x]).strip()
        certs.append({"name": name, "url": "", "description": desc})
    # Websites: already from parse_resume_sections
    websites = resume_meta.get("websites") or []
    # Custom sections: other_sections -> {title, content}
    custom_sections = []
    for s in resume_meta.get("other_sections") or []:
        t = (s.get("title") or "").strip()
        content = (s.get("content") or "").strip()
        if t:
            custom_sections.append({"title": t, "content": content})
    return {
        "contact": contact,
        "title": title,
        "summary": summary,
        "certifications": certs,
        "websites": websites,
        "custom_sections": custom_sections,
        "skills": resume_meta.get("skills") or [],
    }


def _write_other_sections_json(resume_meta: dict, out_dir: Path) -> Path:
    """Write other-sections.json in resume-flock schema."""
    other = _build_other_sections_for_flock(resume_meta)
    return _write_json(out_dir / "other-sections.json", other, out_dir)


def _write_meta_json(
    out_dir: Path,
    resume_id: str,
    display_name: str,
    file_name: str,
    job_count: int,
    skill_count: int,
) -> Path:
    """Write meta.json for resume-flock list UI."""
    from datetime import datetime, timezone
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": resume_id,
        "displayName": display_name,
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "fileName": file_name,
        "jobCount": job_count,
        "skillCount": skill_count,
    }
    path = out_dir / "meta.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return path


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
        "--id",
        type=str,
        default=None,
        help="Resume id for meta.json (default: output dir basename)",
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
        "--no-merge",
        action="store_true",
        help="Skip skill merge step (for non-interactive / CI use)",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic"],
        default=None,
        help="Force LLM_PROVIDER (anthropic); requires ANTHROPIC_API_KEY",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="After writing .json, run render-resume-html to generate resume.html",
    )
    args = parser.parse_args()

    if not args.resume.exists():
        print(f"Error: File not found: {args.resume}", file=sys.stderr)
        return 1

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    if not args.no_llm:
        try:
            get_llm_provider()
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

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
    provider = get_llm_provider()
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

    # Expand "Name (a, b, c)" -> "Name a", "Name b", "Name c" in skills list (for other-sections.json and skills dict)
    if resume_meta.get("skills"):
        resume_meta["skills"] = [
            n
            for name in resume_meta["skills"]
            for n in expand_skill_parens(str(name).strip())
            if n
        ]

    # Expand "Name (a, b, c)" -> "Name a, Name b, Name c" in each job description before converting
    for job in jobs:
        job["description"] = expand_parens_in_text((job.get("description") or "").strip())

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

    # Add skills from the resume's skills section (not from job descriptions); jobIDs [] for these.
    # resume_meta["skills"] already expanded above ("Name (a,b,c)" -> "Name a", "Name b", "Name c")
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

    if not args.no_merge and len(skills) >= 2:
        print("Suggesting skill merges...")
        replacements = run_merge_interactive(skills, flock_jobs, categories)
        for source_names, target_name in replacements:
            for job in flock_jobs:
                desc = job.get("Description") or ""
                for sn in source_names:
                    desc = desc.replace(sn, target_name)
                job["Description"] = desc

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

    # Copy original resume into output folder (original filename)
    out_dir.mkdir(parents=True, exist_ok=True)
    resume_copy_path = out_dir / args.resume.name
    # Only copy if source and destination are different (avoid SameFileError)
    if args.resume.resolve() != resume_copy_path.resolve():
        shutil.copy2(args.resume, resume_copy_path)

    # Write output: jobs.json, skills.json, categories.json, other-sections.json, meta.json
    jobs_path = _write_jobs_json(jobs_by_id, out_dir)
    skills_path = _write_skills_json(skills_by_id, out_dir)
    categories_path = _write_categories_json(categories, out_dir)
    other_path = _write_other_sections_json(resume_meta, out_dir)
    resume_id = args.id if args.id else out_dir.name
    display_name = (resume_meta.get("contact") or {}).get("name") or args.resume.stem or "Resume"
    meta_path = _write_meta_json(
        out_dir, resume_id, display_name, args.resume.name,
        len(jobs_by_id), len(skills_by_id),
    )
    print(f"Copied {resume_copy_path}")
    print(f"Wrote {jobs_path}")
    print(f"Wrote {skills_path}")
    print(f"Wrote {categories_path}")
    print(f"Wrote {other_path}")
    print(f"Wrote {meta_path}")
    if args.render:
        from .render_resume_html import render_resume_html
        resume_path, template_path = render_resume_html(out_dir)
        print(f"Wrote {resume_path}")
        print(f"Wrote {template_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
