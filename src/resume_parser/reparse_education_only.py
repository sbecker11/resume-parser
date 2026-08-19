#!/usr/bin/env python3
"""
Reparse education.json only for existing parsed-resume folders.

This script is non-interactive: it never asks for user input.
It loads each folder's copied resume (.pdf/.docx), extracts text, calls the LLM
for job+education extraction, and writes education.json (when legitimate degrees are found).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts.validate_parsed_resume import validate_education
from .education_rules import has_legitimate_degree, sanitize_education_description
from .extractors import extract_text
from .parsers import parse_jobs_with_llm
from .resume_to_json import _split_jobs_and_education


def _find_resume_file(folder: Path) -> Path | None:
    for p in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_file():
            continue
        if p.suffix.lower() in (".pdf", ".docx"):
            return p
    return None


def _write_education_json(education_entries: list[dict], out_path: Path) -> None:
    education_by_id: dict[str, dict] = {}
    for i, edu in enumerate(education_entries):
        degree = (edu.get("role") or "").strip()
        # Extra safety: only write legitimate degrees.
        if not degree or not has_legitimate_degree(degree):
            continue

        institution = (edu.get("employer") or "").strip()
        education_by_id[str(i)] = {
            "index": i,
            "degree": degree,
            "institution": institution,
            "start": str(edu.get("start") or ""),
            "end": str(edu.get("end") or ""),
            "description": sanitize_education_description(edu.get("description") or ""),
        }

    out_path.write_text(json.dumps(education_by_id, ensure_ascii=False, indent=2), encoding="utf-8")
    # Validate written output (schema-only)
    validate_education(education_by_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reparse education.json for existing parsed folders")
    parser.add_argument("parsed_resumes_root", type=Path, help="Folder containing per-resume subfolders")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite education.json even if it exists",
    )
    args = parser.parse_args()

    root: Path = args.parsed_resumes_root
    if not root.exists() or not root.is_dir():
        print(f"Error: not a directory: {root}", file=sys.stderr)
        return 1

    subdirs = [p for p in root.iterdir() if p.is_dir()]
    if not subdirs:
        print(f"No subfolders found under: {root}", file=sys.stderr)
        return 1

    total = 0
    updated = 0
    skipped_existing = 0
    failures = 0

    for folder in sorted(subdirs, key=lambda p: p.name.lower()):
        total += 1
        edu_path = folder / "education.json"

        if edu_path.exists() and not args.overwrite:
            skipped_existing += 1
            print(f"[{total}] Skip (exists): {folder.name}")
            continue

        resume_path = _find_resume_file(folder)
        if resume_path is None:
            print(f"[{total}] Fail (no resume file): {folder.name}", file=sys.stderr)
            failures += 1
            continue

        print(f"[{total}] Reparse education: {folder.name} (resume={resume_path.name})")
        try:
            raw_text = extract_text(resume_path)
            if not raw_text.strip():
                raise ValueError("No text extracted from resume")

            jobs = parse_jobs_with_llm(raw_text)
            jobs_after_split, education_entries = _split_jobs_and_education(jobs)
            _ = jobs_after_split  # jobs are not re-written; education.json only

            if not education_entries:
                # Write nothing when no legitimate degrees are found.
                # If overwrite was requested, remove old file to keep behavior consistent.
                if edu_path.exists():
                    edu_path.unlink()
                print(f"[{total}] No legitimate education found: {folder.name}")
                continue

            _write_education_json(education_entries, edu_path)
            updated += 1
            print(f"[{total}] Wrote education.json: {folder.name}")
        except Exception as e:
            failures += 1
            print(f"[{total}] Fail: {folder.name}: {e}", file=sys.stderr)

    print("")
    print("Education reparse summary")
    print(f"  total folders:   {total}")
    print(f"  updated:         {updated}")
    print(f"  skipped existing:{skipped_existing}")
    print(f"  failures:        {failures}")

    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

