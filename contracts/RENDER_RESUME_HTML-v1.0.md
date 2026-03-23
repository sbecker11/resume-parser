# render_resume_html — Standalone HTML Generator

Generate `resume.html` from existing JSON files. Use when you have a resume folder (e.g. from `resume-to-json`) and want to produce or refresh the HTML output without re-parsing.

**Contract:** Owned and maintained by resume-parser; consumers implement against this specification.

**Version:** 1.0

## Requirements

- The input folder must contain: `jobs.json`, `skills.json`, `categories.json`, `other-sections.json`
- Python with `jinja2` and `markupsafe` installed (via `pip install -r requirements.txt`)

## Invocation

Run from the resume-parser repo root (resume-consumer invokes this path):

```bash
render-resume-html -i <path-to-resume-folder>
```

| Argument | Required | Description |
|----------|----------|-------------|
| `-i`, `--input-dir` | yes | Directory containing the JSON files and where output will be written |
| `--show-brackets` | no | Keep square brackets in job descriptions, summary, and other section content. Default: strip them (e.g. `[Python]` → `Python`). |

## Behavior

1. Reads from the input folder: `jobs.json`, `skills.json`, `categories.json`, `other-sections.json`
2. Renders a Jinja2 template to HTML
3. Writes to the **same folder**:
   - `resume.html` — rendered resume
   - `resume_template.html` — copy of the template used

## Examples

```bash
# From repo root, render a previously parsed output folder
render-resume-html -i /tmp/resume-output

# Output to parsed_resumes subfolder
render-resume-html -i ./parsed_resumes/parsed-resume-1

# Refresh HTML after editing JSON files manually
render-resume-html -i ~/workspace-resume/parsed-resumes/parsed-resume-1

# Render with square brackets kept in body text (default is to strip them)
render-resume-html -i ./parsed_resumes/shawn-becker --show-brackets
```

## Errors

- **FileNotFoundError** — One or more JSON files are missing in the input folder (`jobs.json`, `skills.json`, `categories.json`, `other-sections.json`)
- **ValueError / JSONDecodeError** — A JSON file is invalid or does not match the expected schema

## Integration

- **With resume-to-json**: Pass `--render` to run the renderer after parsing
- **Without parsing**: Run this script directly on any folder that already has the four JSON files

## Revision history

| Version | Date       | Change |
|---------|------------|--------|
| 1.0     | 2025-03-08 | Initial version under contracts/. |
