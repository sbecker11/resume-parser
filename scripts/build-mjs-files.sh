#!/bin/zsh

RESUME_DIR="/Users/sbecker11/Desktop/Resumes/2026/"
RESUME_NAME="Shawn_Becker_Full_Stack_Developer_AI_ML_Engineer.docx"
RESUME_FILE="$RESUME_DIR/$RESUME_NAME"
output_STATIC="/Users/sbecker11/workspace-resume/resume-consumer/static_content"

# backup existing output files (jobs.json, skills.json, categories.json, other-sections.json, resume.html, resume_template.html)
TIMESTAMP=$(date +%Y%m%d%H%M%S)
mkdir -p "$output_STATIC/backups"
for f in jobs.json skills.json categories.json other-sections.json resume.html resume_template.html; do
  if [[ -f "$output_STATIC/$f" ]]; then
    mv "$output_STATIC/$f" "$output_STATIC/backups/$f.$TIMESTAMP"
  fi
done

# create new output files (jobs.json, skills.json, categories.json, other-sections.json, resume.html, resume_template.html)
cd "$(dirname "$0")/.."
# --provider openai (commented out; Anthropic only)
resume-to-json "$RESUME_FILE" -o "$output_STATIC"

