#!/usr/bin/env python3
"""
resume-to-json: Parse resume (DOCX/PDF) into resume-output jobs.json, skills.json, categories.json, other-sections.json.

Usage:
  resume-to-json <resume.docx|resume.pdf> [--output-dir PATH] [--no-llm] [--no-enrich] [--render]
  # Or from repo: python resume_to_json.py ...

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
import re
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from script directory (reliable regardless of cwd)
load_dotenv(Path(__file__).resolve().parent / ".env")

# Add parent for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extractors import extract_text
from skill_merge import run_merge_interactive
from parsers import (
    parse_jobs_with_llm,
    parse_resume_sections,
    extract_skills_from_text,
    expand_skill_parens,
    expand_parens_in_text,
    enrich_skills_with_llm,
    categorize_skills_with_llm,
    build_categories_dict,
    assign_skill_ids,
    jobs_to_json_format,
    get_llm_provider,
)

_SCHOOL_RE = re.compile(r"\b(university|college|institute|school|academy|polytechnic)\b", re.IGNORECASE)
_DEGREE_RE = re.compile(
    r"\b("
    r"a\.?\s?a\.?|associate|"
    r"b\.?\s?a\.?|b\.?\s?s\.?|bachelor|"
    r"m\.?\s?a\.?|m\.?\s?s\.?|master|mba|"
    r"ph\.?\s?d\.?|doctorate|"
    r"j\.?\s?d\.?|juris\s+doctor|"
    r"m\.?\s?d\.?|doctor\s+of\s+medicine|"
    r"d\.?\s?d\.?\s?s\.?|d\.?\s?v\.?\s?m\.?|d\.?\s?p\.?\s?t\.?|"
    r"b\.?\s?eng\.?|m\.?\s?eng\.?|b\.?\s?tech\.?|m\.?\s?tech\.?"
    r")\b",
    re.IGNORECASE,
)
_NON_DEGREE_ROLE_RE = re.compile(
    r"\b("
    r"resident\s+assistant|"
    r"vice\s+president|"
    r"president|"
    r"economics\s+tutor|"
    r"research\s+assistant"
    r")\b",
    re.IGNORECASE,
)


def _default_output_dir() -> Path:
    """Default output: resume-output/static_content if it exists nearby."""
    tool_dir = Path(__file__).resolve().parent
    # Check workspace-resume, workspace-resume, or cwd
    candidates = [
        Path.home() / "workspace-resume" / "resume-output" / "static_content",
        tool_dir.parent.parent / "resume-output" / "static_content",
        tool_dir.parent / "resume-output" / "static_content",
        Path.cwd() / "static_content",
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path.cwd()


def _write_json(path: Path, data: dict | list, out_dir: Path) -> Path:
    """Write data as UTF-8 JSON (resume-consumer format)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _write_jobs_json(jobs: dict[str, dict], out_dir: Path) -> Path:
    """Write jobs dict keyed by jobID (resume-consumer format)."""
    return _write_json(out_dir / "jobs.json", jobs, out_dir)


def _write_skills_json(skills_by_id: dict[str, dict], out_dir: Path) -> Path:
    """Write skills dict keyed by skillID (resume-consumer format)."""
    return _write_json(out_dir / "skills.json", skills_by_id, out_dir)


def _write_categories_json(categories: dict[str, dict], out_dir: Path) -> Path:
    """Write categories dict (resume-consumer format)."""
    return _write_json(out_dir / "categories.json", categories, out_dir)


def _write_education_json(education_by_id: dict[str, dict], out_dir: Path) -> Path:
    """Write education dict keyed by educationID."""
    return _write_json(out_dir / "education.json", education_by_id, out_dir)


def _looks_like_education_entry(item: dict) -> bool:
    role = str(item.get("role") or "")
    employer = str(item.get("employer") or "")
    if not _DEGREE_RE.search(role):
        return False
    if _NON_DEGREE_ROLE_RE.search(role):
        return False
    return bool(_SCHOOL_RE.search(employer) or _SCHOOL_RE.search(role))


def _split_jobs_and_education(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split parsed entries into work jobs and education entries."""
    jobs: list[dict] = []
    education: list[dict] = []
    for item in items:
        if _looks_like_education_entry(item):
            education.append(item)
        else:
            jobs.append(item)
    return jobs, education


def _build_other_sections_for_json(resume_meta: dict) -> dict:
    """Transform parser meta to resume-consumer otherSections schema."""
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
    """Write other-sections.json in resume-consumer schema."""
    other = _build_other_sections_for_json(resume_meta)
    return _write_json(out_dir / "other-sections.json", other, out_dir)


def _write_meta_json(
    out_dir: Path,
    resume_id: str,
    display_name: str,
    file_name: str,
    job_count: int,
    skill_count: int,
) -> Path:
    """Write meta.json for resume-consumer list UI."""
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
    parser = argparse.ArgumentParser(description="Parse resume into resume-output data")
    parser.add_argument("resume", type=Path, help="Path to resume.docx or resume.pdf")
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: resume-output/static_content or cwd)",
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
        help="After writing .json, run render_resume_html.py to generate resume.html",
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

    # Split entries so education is written to education.json and excluded from jobs.json.
    jobs, education_entries = _split_jobs_and_education(jobs)

    # Expand "Name (a, b, c)" -> "Name a, Name b, Name c" in each job description before converting
    for job in jobs:
        job["description"] = expand_parens_in_text((job.get("description") or "").strip())

    # Convert to JSON format
    json_jobs = jobs_to_json_format(jobs)
    education_by_id: dict[str, dict] = {}
    for i, edu in enumerate(education_entries):
        degree = (edu.get("role") or "").strip()
        institution = (edu.get("employer") or "").strip()
        education_by_id[str(i)] = {
            "index": i,
            "degree": degree,
            "institution": institution,
            "start": str(edu.get("start") or ""),
            "end": str(edu.get("end") or ""),
            "description": (edu.get("description") or "").strip(),
        }

    # Phase 3: Extract skills per job so we can assign jobIDs
    skills: dict = {}
    for i, job in enumerate(json_jobs):
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
        replacements = run_merge_interactive(skills, json_jobs, categories)
        for source_names, target_name in replacements:
            for job in json_jobs:
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
    for job in json_jobs:
        job["skillIDs"] = [
            data["id"]
            for name, data in skills.items()
            if job["index"] in data.get("jobIDs", [])
        ]
    jobs_by_id: dict[str, dict] = {str(job["index"]): job for job in json_jobs}
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
    # education.json is optional and only written when education entries exist.
    jobs_path = _write_jobs_json(jobs_by_id, out_dir)
    education_path = None
    # If a previous run wrote education.json, ensure we don't leave stale/invalid entries
    # when the new parse contains no education items.
    education_file = out_dir / "education.json"
    if education_by_id:
        education_path = _write_education_json(education_by_id, out_dir)
    else:
        if education_file.exists():
            education_file.unlink()
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
    if education_path:
        print(f"Wrote {education_path}")
    print(f"Wrote {skills_path}")
    print(f"Wrote {categories_path}")
    print(f"Wrote {other_path}")
    print(f"Wrote {meta_path}")
    if args.render:
        from render_resume_html import render_resume_html
        resume_path, template_path = render_resume_html(out_dir)
        print(f"Wrote {resume_path}")
        print(f"Wrote {template_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
