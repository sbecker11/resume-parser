#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

usage() {
  cat <<'EOF'
Usage:
  parse_resumes_batch.sh <input-resumes-folder> <output-parsed-resumes-folder> [--render]

Description:
  Parses every .docx/.pdf resume in <input-resumes-folder> with resume-to-json
  and writes one parsed output folder per resume under <output-parsed-resumes-folder>.

Options:
  --render   Also render resume.html after parse
            NOTE: this script is non-interactive and will not run any prompts.
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

LOG_FILE="$OUTPUT_DIR/parse_resumes_batch_$(date -u +%Y%m%dT%H%M%SZ).log"
touch "$LOG_FILE"

_log() {
  local msg="$*"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "[$ts] $msg" | tee -a "$LOG_FILE"
}

run_parse() {
  if command -v resume-to-json >/dev/null 2>&1; then
    stdbuf -oL -eL resume-to-json "$@" 2>&1 | stdbuf -oL -eL tee -a "$LOG_FILE"
  else
    stdbuf -oL -eL python -u -m resume_parser.resume_to_json "$@" 2>&1 | stdbuf -oL -eL tee -a "$LOG_FILE"
  fi
}

run_validate() {
  if command -v validate-parsed-resume >/dev/null 2>&1; then
    stdbuf -oL -eL validate-parsed-resume "$@" 2>&1 | stdbuf -oL -eL tee -a "$LOG_FILE"
  else
    stdbuf -oL -eL python -u -m resume_parser.contracts.validate_parsed_resume "$@" 2>&1 | stdbuf -oL -eL tee -a "$LOG_FILE"
  fi
}

total=0
parsed_ok=0
validated_ok=0
education_found=0
failed=0

_log "Batch start: input=\"$INPUT_DIR\" output=\"$OUTPUT_DIR\" merge=\"${MERGE_FLAG[*]:-(--no-merge)}\" render=\"${RENDER_FLAG[*]}\" log=\"$LOG_FILE\""

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

  _log "[$total] Parsing: $resume_path -> \"$out_dir\""
  parse_start_ts="$(date +%s)"
  if run_parse "$resume_path" -o "$out_dir" "${MERGE_FLAG[@]}" "${RENDER_FLAG[@]}"; then
    parsed_ok=$((parsed_ok + 1))
    parse_elapsed=$(( $(date +%s) - parse_start_ts ))
    _log "Parse OK (elapsed ${parse_elapsed}s): $resume_path"
  else
    echo "  Parse failed: $resume_path" >&2
    failed=$((failed + 1))
    _log "Parse FAILED: $resume_path"
    continue
  fi

  validate_start_ts="$(date +%s)"
  if run_validate "$out_dir"; then
    validated_ok=$((validated_ok + 1))
    validate_elapsed=$(( $(date +%s) - validate_start_ts ))
    _log "Validation OK (elapsed ${validate_elapsed}s): $out_dir"
  else
    echo "  Validation failed: $out_dir" >&2
    failed=$((failed + 1))
    _log "Validation FAILED: $out_dir"
  fi

  if [[ -f "$out_dir/education.json" ]]; then
    education_found=$((education_found + 1))
    _log "education.json present for: $out_dir"
  else
    _log "education.json absent for: $out_dir"
  fi
done

echo ""
echo "Batch parse summary"
echo "  total resumes found:      $total"
echo "  parsed successfully:      $parsed_ok"
echo "  validated successfully:   $validated_ok"
echo "  with education.json:      $education_found"
echo "  failures:                 $failed"

_log "Batch summary: total=$total parsed_ok=$parsed_ok validated_ok=$validated_ok education_found=$education_found failures=$failed"

if [[ $total -eq 0 ]]; then
  echo "No DOCX/PDF files found in: $INPUT_DIR" >&2
  exit 1
fi

if [[ $failed -gt 0 ]]; then
  exit 2
fi

echo "Done: parsed resumes written under: $OUTPUT_DIR"
