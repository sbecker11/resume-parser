# render_resume_html — Standalone HTML Generator

Generate `resume.html` from existing .mjs files. Use when you have a resume folder (e.g. from `resume_to_flock.py`) and want to produce or refresh the HTML output without re-parsing.

## Requirements

- The input folder must contain: `jobs.mjs`, `skills.mjs`, `categories.mjs`, `other-sections.mjs`
- Python with `jinja2` and `markupsafe` installed (via `pip install -r requirements.txt`)

## Invocation

```bash
python render_resume_html.py -i <path-to-resume-folder>
```

| Argument | Required | Description |
|----------|----------|-------------|
| `-i`, `--input-dir` | yes | Directory containing the .mjs files and where output will be written |

## Behavior

1. Reads from the input folder: `jobs.mjs`, `skills.mjs`, `categories.mjs`, `other-sections.mjs`
2. Renders a Jinja2 template to HTML
3. Writes to the **same folder**:
   - `resume.html` — rendered resume
   - `resume_template.html` — copy of the template used

## Examples

```bash
# From repo root, render a previously parsed output folder
python render_resume_html.py -i /tmp/resume-output

# Output to parsed_resumes subfolder
python render_resume_html.py -i ./parsed_resumes/parsed-resume-1

# Refresh HTML after editing .mjs files manually
python render_resume_html.py -i ~/workspace-resume/parsed-resumes/parsed-resume-1
```

## Errors

- **FileNotFoundError** — One or more .mjs files are missing in the input folder
- **ValueError / JSONDecodeError** — A .mjs file has invalid syntax or doesn’t contain the expected export

## Integration

- **With resume_to_flock.py**: Pass `--render` to run this script after parsing
- **Without parsing**: Run this script directly on any folder that already has the four .mjs files
