#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  reparse_education_only.sh <parsed-resumes-root> [--overwrite]

Description:
  For each per-resume subfolder under <parsed-resumes-root>, find the copied
  .pdf/.docx resume file, run education extraction, and write education.json.

  Non-interactive: no prompts.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

ROOT_DIR="$1"
shift

OVERWRITE_FLAG=()
if [[ "${1:-}" == "--overwrite" ]]; then
  OVERWRITE_FLAG=(--overwrite)
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"

python -m resume_parser.reparse_education_only "$ROOT_DIR" "${OVERWRITE_FLAG[@]}"

