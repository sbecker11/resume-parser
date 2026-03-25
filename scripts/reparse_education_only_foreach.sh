#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  reparse_education_only_foreach.sh

Description:
  Reparse education.json for a fixed set of subfolders (hardcoded paths)
  under output-parsed-resumes-folder.

  Non-interactive: it regenerates education.json in each folder (no prompts)
  and overwrites any existing education.json.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

OVERWRITE_FLAG=()
OVERWRITE_FLAG=(--overwrite)

ROOT_DIR_BASE="/Users/sbecker11/workspace-resume/resume-parser/output-parsed-resumes-folder"
FOLDERS=(
  "$ROOT_DIR_BASE/joe-student-business"
  "$ROOT_DIR_BASE/kelly-victory-public-service"
  "$ROOT_DIR_BASE/kenya-rios-arts-admin"
  "$ROOT_DIR_BASE/ben-pierce-functional"
  "$ROOT_DIR_BASE/janette-powell-chronological"
  "$ROOT_DIR_BASE/pr_resume_example.docx_"
  "$ROOT_DIR_BASE/resume-and-cover-letter-examples"
  "$ROOT_DIR_BASE/stephen-olsted-science"
  "$ROOT_DIR_BASE/Shawn_Becker_Full_Stack_Developer_AI_ML_Engineer"
)

export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)/src:${PYTHONPATH:-}"

for d in "${FOLDERS[@]}"; do
  [[ -d "$d" ]] || { echo "Skip (missing folder): $d"; continue; }

  name="$(basename "$d")"
  echo "Reparse education: $name"

  PYTHONPATH="$PYTHONPATH" python -u - <<PY
from pathlib import Path
import json
import sys

from resume_parser.education_rules import has_legitimate_degree
from resume_parser.extractors import extract_text
from resume_parser.parsers import parse_jobs_with_llm
from resume_parser.resume_to_json import _split_jobs_and_education
from resume_parser.contracts.validate_parsed_resume import validate_education

folder = Path(r"$d")
edu_path = folder / "education.json"
overwrite = bool(r"${OVERWRITE_FLAG:+1}")

def find_resume_file(f: Path) -> Path | None:
    # prefer pdf then docx, deterministic ordering
    pdfs = sorted([p for p in f.iterdir() if p.is_file() and p.suffix.lower()==".pdf"], key=lambda x: x.name.lower())
    if pdfs:
        return pdfs[0]
    docxs = sorted([p for p in f.iterdir() if p.is_file() and p.suffix.lower()==".docx"], key=lambda x: x.name.lower())
    return docxs[0] if docxs else None

resume_path = find_resume_file(folder)
if resume_path is None:
    raise SystemExit(f"No .pdf/.docx found in {folder}")

if edu_path.exists() and not overwrite:
    print(f"[SKIP] education.json exists: {folder.name}")
    sys.exit(0)

raw_text = extract_text(resume_path)
if not raw_text or not raw_text.strip():
    raise ValueError(f"No text extracted from {resume_path}")

jobs = parse_jobs_with_llm(raw_text)
_, education_entries = _split_jobs_and_education(jobs)

education_by_id = {}
for i, edu in enumerate(education_entries):
    degree = (edu.get("role") or "").strip()
    if not degree or not has_legitimate_degree(degree):
        continue
    education_by_id[str(i)] = {
        "index": i,
        "degree": degree,
        "institution": (edu.get("employer") or "").strip(),
        "start": str(edu.get("start") or ""),
        "end": str(edu.get("end") or ""),
        "description": (edu.get("description") or "").strip(),
    }

if not education_by_id:
    if edu_path.exists():
        edu_path.unlink()
    print(f"[NO EDU] none found: {folder.name}")
    sys.exit(0)

edu_path.write_text(json.dumps(education_by_id, ensure_ascii=False, indent=2), encoding="utf-8")
validate_education(education_by_id)
print(f"[OK] Wrote education.json: {folder.name}")
PY
done

