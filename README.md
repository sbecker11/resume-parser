# resume-parser (resume-to-flock)

Parse resume documents (DOCX/PDF) into flock-of-postcards data: `jobs.mjs` and `skills.mjs`.

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

```bash
python resume_to_flock.py /path/to/resume.docx -o /path/to/output-files

```

### Options

| Option | Description |
|-------|-------------|
| `-o`, `--output-dir` | Where to write `jobs.mjs` and `skills.mjs` (default: flock-of-postcards/static_content if found, else cwd) |
| `--no-llm` | Skip LLM; only extract text (for testing) |
| `--no-enrich` | Skip LLM skill URL enrichment |
| `--provider` | Force LLM_PROVIDER: `anthropic` (requires ANTHROPIC_API_KEY) |

## Output

- **jobs/jobs.mjs** – Flock job objects (role, employer, start, end, Description, etc.)
- **skills/skills.mjs** – Skills dict: `{ "SkillName": { "url": "", "img": "" } }`

## Pipeline

1. **Extract** – python-docx (DOCX) or pdfplumber (PDF) → raw text
2. **Parse jobs** – LLM (Anthropic) extracts structured jobs with dates and descriptions
3. **Extract skills** – Regex `[text]{img}(url)` from descriptions
4. **Enrich** – Optional LLM pass to suggest URLs for skills without one

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
