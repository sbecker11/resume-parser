#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  parse_resumes_batch.sh <input-resumes-folder> <output-parsed-resumes-folder> [--render] [--merge]

Description:
  Parses every .docx/.pdf resume in <input-resumes-folder> with resume-to-json
  and writes one parsed output folder per resume under <output-parsed-resumes-folder>.

Options:
  --render   Also render resume.html after parse
  --merge    Enable interactive skill-merge step (default is --no-merge for batch safety)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 ]]; then
  usage >&2
  exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
shift 2

RENDER_FLAG=()
MERGE_FLAG=(--no-merge)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --render)
      RENDER_FLAG=(--render)
      ;;
    --merge)
      MERGE_FLAG=()
      ;;
    *)
      echo "Error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ! -d "$INPUT_DIR" ]]; then
  echo "Error: input folder not found: $INPUT_DIR" >&2
  exit 1
fi

if [[ ! -d "$OUTPUT_DIR" ]]; then
  mkdir -p "$OUTPUT_DIR"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"

run_parse() {
  if command -v resume-to-json >/dev/null 2>&1; then
    resume-to-json "$@"
  else
    python -m resume_parser.resume_to_json "$@"
  fi
}

run_validate() {
  if command -v validate-parsed-resume >/dev/null 2>&1; then
    validate-parsed-resume "$@"
  else
    python -m resume_parser.contracts.validate_parsed_resume "$@"
  fi
}

total=0
parsed_ok=0
validated_ok=0
education_found=0
failed=0

shopt -s nullglob
for resume_path in "$INPUT_DIR"/*; do
  if [[ ! -f "$resume_path" ]]; then
    continue
  fi

  lower_name="$(basename "$resume_path" | tr '[:upper:]' '[:lower:]')"
  case "$lower_name" in
    *.docx|*.pdf) ;;
    *) continue ;;
  esac

  total=$((total + 1))
  base_name="$(basename "$resume_path")"
  stem="${base_name%.*}"
  safe_stem="$(echo "$stem" | tr ' ' '-' | tr -cd '[:alnum:]_.-')"
  out_dir="$OUTPUT_DIR/$safe_stem"
  mkdir -p "$out_dir"

  echo ""
  echo "[$total] Parsing: $resume_path"
  if run_parse "$resume_path" -o "$out_dir" "${MERGE_FLAG[@]}" "${RENDER_FLAG[@]}"; then
    parsed_ok=$((parsed_ok + 1))
  else
    echo "  Parse failed: $resume_path" >&2
    failed=$((failed + 1))
    continue
  fi

  if run_validate "$out_dir" >/dev/null; then
    validated_ok=$((validated_ok + 1))
  else
    echo "  Validation failed: $out_dir" >&2
    failed=$((failed + 1))
  fi

  if [[ -f "$out_dir/education.json" ]]; then
    education_found=$((education_found + 1))
  fi
done

echo ""
echo "Batch parse summary"
echo "  total resumes found:      $total"
echo "  parsed successfully:      $parsed_ok"
echo "  validated successfully:   $validated_ok"
echo "  with education.json:      $education_found"
echo "  failures:                 $failed"

if [[ $total -eq 0 ]]; then
  echo "No DOCX/PDF files found in: $INPUT_DIR" >&2
  exit 1
fi

if [[ $failed -gt 0 ]]; then
  exit 2
fi

echo "Done: parsed resumes written under: $OUTPUT_DIR"
