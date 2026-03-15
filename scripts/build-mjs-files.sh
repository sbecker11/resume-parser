#!/bin/zsh

RESUME_DIR="/Users/sbecker11/Desktop/Resumes/2026/"
RESUME_NAME="Shawn_Becker_Full_Stack_Developer_AI_ML_Engineer.docx"
RESUME_FILE="$RESUME_DIR/$RESUME_NAME"
FLOCK_STATIC="/Users/sbecker11/workspace-flock/resume-flock/static_content"

# backup existing output files (jobs.json, skills.json, categories.json, other-sections.json, resume.html, resume_template.html)
TIMESTAMP=$(date +%Y%m%d%H%M%S)
mkdir -p "$FLOCK_STATIC/backups"
for f in jobs.json skills.json categories.json other-sections.json resume.html resume_template.html; do
  if [[ -f "$FLOCK_STATIC/$f" ]]; then
    mv "$FLOCK_STATIC/$f" "$FLOCK_STATIC/backups/$f.$TIMESTAMP"
  fi
done

# create new output files (jobs.json, skills.json, categories.json, other-sections.json, resume.html, resume_template.html)
cd "$(dirname "$0")/.."
# --provider openai (commented out; Anthropic only)
python resume_to_flock.py "$RESUME_FILE" -o "$FLOCK_STATIC"

