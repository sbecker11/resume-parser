# resume-parser (resume-to-flock)

Parse resume documents (DOCX/PDF) into flock-of-postcards data: `jobs.json`, `skills.json`, `categories.json`, `other-sections.json`.

## Setup

```bash
cd /Users/sbecker11/workspace-resume/resume-parser
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create `.env` and set the LLM provider key (LLM_PROVIDER=anthropic uses ANTHROPIC_API_KEY):

```
ANTHROPIC_API_KEY=your-anthropic-key-here
# Optional: LLM_PROVIDER=anthropic
```

## Usage

Provide the path to your resume file (DOCX or PDF); there is no project `resumes/` folder.

```bash
python resume_to_flock.py /path/to/resume.docx -o /path/to/output-files

```

### Options

| Option | Description |
|-------|-------------|
| `-o`, `--output-dir` | Where to write .json files (default: flock-of-postcards/static_content if found, else cwd) |
| `--id` | Resume id for meta.json (default: output dir basename) |
| `--no-llm` | Skip LLM; only extract text (for testing) |
| `--no-enrich` | Skip LLM skill URL enrichment |
| `--provider` | Force LLM_PROVIDER: `anthropic` (requires ANTHROPIC_API_KEY) |
| `--no-merge` | Skip interactive skill merge step (for CI / non-interactive use) |
| `--render` | After writing .json, generate `resume.html` (calls `render_resume_html`) |

## Output

All files are written in the output folder (no subfolders). The output folder also includes a copy of the original resume file (DOCX or PDF) under its **original filename**.

**Data model (consistent across the three dicts):**

- **Skills** dictionary uses **skillID** as primary key. Skill item has display name (`name`), optional list of `categoryIDs`, optional list of `jobIDs`.
- **Jobs** dictionary uses **jobID** as primary key. Job item has display name (role, employer), optional list of `skillIDs`.
- **Categories** dictionary uses **categoryID** as primary key. Category item has display name (`name`), optional list of `skillIDs`.

- **jobs.mjs** – `export const jobs = {...}` (resume-flock format). Jobs dict keyed by jobID; each job has role, employer, start, end, Description, skillIDs, etc.
- **skills.mjs** – Skills dict keyed by skillID (slug): `{ "skillID": { "name": "Display Name", "url": "", "img": "", "categoryIDs": ["id1", ...], "jobIDs": [0, 1, ...] }, ... }`. Same structure as jobs and categories (ID as key, display name inside). Includes skills from job descriptions (with job indices in `jobIDs`) plus any from the resume’s skills section (`jobIDs` empty). `categoryIDs` reference **categories.mjs** for display names.
- **categories.mjs** – `export const categories = {...}` (resume-flock format). Dict keyed by categoryID; each category has name, skillIDs.
- **other-sections.mjs** – `export const otherSections = {...}` (resume-flock format): contact, title, summary, certifications, websites, custom_sections, skills.
- **meta.json** – Resume metadata for list UI: id, displayName, createdAt, fileName, jobCount, skillCount.
- **resume.html** – Rendered resume (generate with `python render_resume_html.py -i /path/to/output` or `--render`).
- **resume_template.html** – Copy of the template (written when generating resume.html).

## Pipeline

1. **Extract** – python-docx (DOCX) or pdfplumber (PDF) → raw text
2. **Parse jobs** – LLM (Anthropic) extracts structured jobs with dates and descriptions
3. **Parse resume sections** – LLM extracts contact, summary, certifications, skills, other sections → `resume_meta.json`
4. **Extract skills** – Regex `[text]{img}(url)` from job descriptions; merge resume skills section
5. **Enrich** – Optional LLM pass to suggest URLs for skills without one
6. **Categorize** – LLM assigns each skill a list of categories (e.g. Programming Language, Framework) → `skills.json`

### HTML generation (optional)

Generate `resume.html` from the JSON files:

```bash
python render_resume_html.py -i /path/to/output-folder
```

Or use `--render` with `resume_to_flock.py` to run this step automatically after parsing.

## Tests

From the repo root (with venv activated):

```bash
python -m unittest discover -s tests
```

Tests in `tests/` cover `extractors.extract_text`, `parsers.extract_skills_from_text`, and `parsers.get_llm_provider` (no LLM calls).

### Coverage report

Install [coverage](https://coverage.readthedocs.io/) (add to venv if needed):

```bash
pip install coverage
```

Run tests under coverage and print a report:

```bash
coverage run -m unittest discover -s tests
coverage report
```

To generate an HTML report (opens in browser):

```bash
coverage run -m unittest discover -s tests
coverage html
# open htmlcov/index.html
```

## Flock integration

The generated output files can be read by `workspace-resume/resume-flock`
