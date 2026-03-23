#!/usr/bin/env bash
set -euo pipefail

# Inter-project housekeeping:
# Apply the reconcile-only merged-term replacement pass to all parsed resumes
# under the resume-consumer workspace.

PARSED_RESUMES_DIR="/Users/sbecker11/workspace-resume/resume-consumer/parsed_resumes"

RENDER_FLAG=()
if [[ "${1:-}" == "--render" ]]; then
  RENDER_FLAG=(--render)
fi

if [[ ! -d "$PARSED_RESUMES_DIR" ]]; then
  echo "Error: parsed resumes dir not found: $PARSED_RESUMES_DIR" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if command -v run-merge-on-parsed >/dev/null 2>&1; then
  # Prefer the installed CLI.
  run-merge-on-parsed --reconcile-only --all "$PARSED_RESUMES_DIR" "${RENDER_FLAG[@]}"
else
  # Fallback to running from this repo (src/ layout).
  export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"
  cd "$REPO_ROOT"
  python -m resume_parser.run_merge_on_parsed --reconcile-only --all "$PARSED_RESUMES_DIR" "${RENDER_FLAG[@]}"
fi

echo "Done: reconciled merged skill terms in job descriptions under: $PARSED_RESUMES_DIR"

