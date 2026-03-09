#!/usr/bin/env python3
"""
resume-to-flock: Parse resume (DOCX/PDF) into flock-of-postcards jobs.mjs and skills.mjs.

Usage:
  python resume_to_flock.py <resume.docx|resume.pdf> [--output-dir PATH] [--no-llm] [--no-enrich]

  --output-dir   Where to write jobs.mjs and skills.mjs
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
    extract_skills_from_text,
    enrich_skills_with_llm,
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


def _write_jobs_mjs(jobs: list[dict], out_dir: Path) -> Path:
    jobs_dir = out_dir / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    path = jobs_dir / "jobs.mjs"
    with open(path, "w", encoding="utf-8") as f:
        f.write("const jobs = ")
        f.write(json.dumps(jobs, ensure_ascii=False))
        f.write(";")
    return path


def _write_skills_mjs(skills: dict[str, dict[str, str]], out_dir: Path) -> Path:
    skills_dir = out_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    path = skills_dir / "skills.mjs"
    with open(path, "w", encoding="utf-8") as f:
        f.write("const skills = ")
        f.write(json.dumps(skills, ensure_ascii=False))
        f.write(";")
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

    # Convert to flock format
    flock_jobs = jobs_to_flock_format(jobs)

    # Phase 3: Extract skills from descriptions
    all_desc = " ".join(j.get("Description", "") or "" for j in flock_jobs)
    skills = extract_skills_from_text(all_desc)
    print(f"Extracted {len(skills)} skills from descriptions")

    if not args.no_enrich and skills:
        print("Enriching skills with LLM...")
        skills = enrich_skills_with_llm(skills)

    # Write output
    jobs_path = _write_jobs_mjs(flock_jobs, out_dir)
    skills_path = _write_skills_mjs(skills, out_dir)
    print(f"Wrote {jobs_path}")
    print(f"Wrote {skills_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
