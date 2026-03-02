#!/bin/zsh

RESUME_DIR="/Users/sbecker11/Desktop/Resumes/2026/"
RESUME_NAME="Shawn_Becker_Full_Stack_Developer_AI_ML_Engineer.docx"
RESUME_FILE="$RESUME_DIR/$RESUME_NAME"
FLOCK_STATIC="/Users/sbecker11/workspace-flock/resume-flock/static_content"

# backup existing mjs files (jobs and skills)
TIMESTAMP=$(date +%Y%m%d%H%M%S)
for subdir in jobs skills; do
  dir="$FLOCK_STATIC/$subdir"
  if [[ -d "$dir" ]]; then
    mkdir -p "$dir/backups"
    for file in "$dir"/*.mjs; do
      [[ -f "$file" ]] && mv "$file" "$dir/backups/$(basename $file).$TIMESTAMP"
    done
  fi
done

# create new mjs files (writes to static_content/jobs/ and static_content/skills/)
cd "$(dirname "$0")/.."
python resume_to_flock.py "$RESUME_FILE" -o "$FLOCK_STATIC" --provider openai

