# resume-parser (resume-to-json)

Parse resumes (DOCX/PDF) into `jobs.json`, `skills.json`, `categories.json`, and `other-sections.json`.
LLM-driven skill term merges with manual approval.

## Installation (for consumers like resume-consumer)

Install the package so you get the CLI commands and the `resume_parser` Python API.

**From Git (branch or tag):**

```bash
pip install "resume-parser @ git+https://github.com/sbecker11/resume-parser.git@main"
# or pin a release: @v1.0.0
```

**From PyPI (once published):**

```bash
pip install resume-parser
# or pin: resume-parser==1.0.0
```

**In a consumer project (e.g. resume-consumer):**

- **requirements.txt:**  
  `resume-parser @ git+https://github.com/sbecker11/resume-parser.git@v1.0.0`
- **pyproject.toml:**  
  `dependencies = ["resume-parser @ git+https://github.com/sbecker11/resume-parser.git@v1.0.0"]`

After install, **root-level CLIs** are on your PATH: `resume-to-json`, `resume-from-json`, `render-resume-html`, `run-merge-on-parsed`, `validate-parsed-resume`. resume-consumer can invoke the renderer with `resume-from-json -i <folder>` (or `render-resume-html -i <folder>`) - see [contracts/RENDER_RESUME_HTML-v1.0.md](contracts/RENDER_RESUME_HTML-v1.0.md).

**Single source of truth for integration:** Schema, validator, and contract specs all live in **[contracts/](contracts/)** (see [contracts/README.md](contracts/README.md)). The package provides the CLIs only; contracts/ holds the documents consumers need.

---

## Setup (developers)

```bash
cd /path/to/resume-parser
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

Create `.env` and set the LLM provider key (LLM_PROVIDER=anthropic uses ANTHROPIC_API_KEY):

```
ANTHROPIC_API_KEY=your-anthropic-key-here
# Optional: LLM_PROVIDER=anthropic
```

## CLI utilities

When the package is installed, these commands are on your PATH. (Developers can also run the scripts in the repo.)

| Command | Purpose |
|--------|--------|
| **`resume-to-json`** | Parse a resume (DOCX/PDF) → write JSON (+ optional merge and HTML). |
| **`resume-from-json`** | Load parsed JSON into an in-memory resume model, then render `resume.html`. |
| **`render-resume-html`** | Generate `resume.html` from existing JSON in a folder. Contract: contracts/RENDER_RESUME_HTML-v1.0.md. Invoked by resume-consumer. |
| **`run-merge-on-parsed`** | Run skill merge on an existing parsed folder (read/write JSON, optional `--render`). |
| **`validate-parsed-resume`** | Validate a parsed-resume folder’s JSON against the schema. |

See [docs/SMOKE_TEST.md](docs/SMOKE_TEST.md) for manual smoke-test steps.

## Usage

Provide the path to your resume file (DOCX or PDF); there is no project `resumes/` folder.

```bash
resume-to-json /path/to/resume.docx -o /path/to/output-files
```

### Options

| Option | Description |
|-------|-------------|
| `-o`, `--output-dir` | Where to write .json files (default: resume-consumer/static_content if found, else cwd) |
| `--id` | Resume id for meta.json (default: output dir basename) |
| `--no-llm` | Skip LLM; only extract text (for testing) |
| `--no-enrich` | Skip LLM skill URL enrichment |
| `--provider` | Force LLM_PROVIDER: `anthropic` (requires ANTHROPIC_API_KEY) |
| `--no-merge` | Skip interactive skill merge step (for CI / non-interactive use) |
| `--render` | After writing .json, generate `resume.html` (calls `render-resume-html`) |

## Output

All files are written in the output folder (no subfolders). The output folder also includes a copy of the original resume file (DOCX or PDF) under its **original filename**.

**Data model (consistent across the three dicts):**

- **Skills** dictionary uses **skillID** as primary key. Skill item has display name (`name`), optional list of `categoryIDs`, optional list of `jobIDs`.
- **Jobs** dictionary uses **jobID** as primary key. Job item has display name (role, employer), optional list of `skillIDs`.
- **Categories** dictionary uses **categoryID** as primary key. Category item has display name (`name`), optional list of `skillIDs`.

- **jobs.json** - Jobs dict keyed by jobID (resume-consumer format). Each job has role, employer, start, end, Description, skillIDs, etc.
- **skills.json** - Skills dict keyed by skillID (slug): `{ "skillID": { "name": "Display Name", "url": "", "img": "", "categoryIDs": ["id1", ...], "jobIDs": [0, 1, ...] }, ... }`. Same structure as jobs and categories (ID as key, display name inside). Includes skills from job descriptions (with job indices in `jobIDs`) plus any from the resume’s skills section (`jobIDs` empty). `categoryIDs` reference **categories.json** for display names.
- **categories.json** - Categories dict keyed by categoryID (resume-consumer format). Each category has name, skillIDs.
- **other-sections.json** - Contact, title, summary, certifications, websites, custom_sections, skills (resume-consumer format).
- **meta.json** - Resume metadata for list UI: id, displayName, createdAt, fileName, jobCount, skillCount.
- **resume.html** - Rendered resume (generate with `render-resume-html -i /path/to/output` or `--render`).
- **resume_template.html** - Copy of the template (written when generating resume.html).

## Pipeline

1. **Extract** - python-docx (DOCX) or pdfplumber (PDF) → raw text
2. **Parse jobs** - LLM (Anthropic) extracts structured jobs with dates and descriptions
3. **Parse resume sections** - LLM extracts contact, summary, certifications, skills, other sections → `resume_meta.json`
4. **Extract skills** - Regex `[text]{img}(url)` from job descriptions; merge resume skills section
5. **Enrich** - Optional LLM pass to suggest URLs for skills without one
6. **Categorize** - LLM assigns each skill a list of categories (e.g. Programming Language, Framework) → `skills.json`

### HTML generation (optional)

Generate `resume.html` from the JSON files:

```bash
render-resume-html -i /path/to/output-folder
```

Or use `--render` with `resume-to-json` to run this step automatically after parsing. Contract for resume-consumer: [contracts/RENDER_RESUME_HTML-v1.0.md](contracts/RENDER_RESUME_HTML-v1.0.md).

### Run merge on existing parsed folder

To run the skill-merge step on a folder that already has parsed JSON (e.g. from a previous parse or from `parsed_resumes/`), use `run-merge-on-parsed`. It reads `jobs.json`, `skills.json`, and `categories.json`, runs the LLM merge (interactive or `--accept-all`), updates those files and job descriptions, and optionally re-renders `resume.html`.

```bash
# One folder (interactive prompts; re-render HTML after)
run-merge-on-parsed /path/to/parsed-folder --render

# All subfolders, apply all suggested merges, then render
run-merge-on-parsed parsed_resumes --all --accept-all --render
```

Requires `ANTHROPIC_API_KEY` in `.env`. Options: `--all` (each subfolder), `--accept-all` (no prompts), `--render` / `--render-after-merging` (run `render-resume-html` after merging).

### Validate parsed output

To check that a parsed-resume folder’s JSON conforms to the schema:

```bash
validate-parsed-resume /path/to/parsed-folder
```

Requires the package installed (`pip install -e .` or from Git). On success, prints the list of validated files (e.g. `jobs.json`, `skills.json`, `categories.json`, `other-sections.json`, `meta.json`).

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

The project enforces an 80% line-coverage floor per file (not just in
aggregate), including in CI — see `docs/TEST-COVERAGE.md`.

## Flyer integration

The generated output files can be read by `workspace-resume/resume-consumer`
