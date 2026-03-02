# resume-parser (resume-to-flock)

Parse resume documents (DOCX/PDF) into flock-of-postcards data: `jobs.mjs` and `skills.mjs`.

## Setup

```bash
cd /Users/sbecker11/workspace-resume/resume-parser
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create `.env` and add at least one LLM API key:

```
ANTHROPIC_API_KEY=your-anthropic-key-here
# or
OPENAI_API_KEY=your-openai-key-here
```

Anthropic is preferred if both are set. Use `--provider openai` to force OpenAI.

## Usage

```bash
python resume_to_flock.py /path/to/resume.docx
python resume_to_flock.py /path/to/resume.pdf -o /path/to/output
```

### Options

| Option | Description |
|-------|-------------|
| `-o`, `--output-dir` | Where to write `jobs.mjs` and `skills.mjs` (default: flock-of-postcards/static_content if found, else cwd) |
| `--no-llm` | Skip LLM; only extract text (for testing) |
| `--no-enrich` | Skip LLM skill URL enrichment |
| `--provider` | Force LLM provider: `anthropic` or `openai` |

## Output

- **jobs/jobs.mjs** – Flock job objects (role, employer, start, end, Description, etc.)
- **skills/skills.mjs** – Skills dict: `{ "SkillName": { "url": "", "img": "" } }`

## Pipeline

1. **Extract** – python-docx (DOCX) or pdfplumber (PDF) → raw text
2. **Parse jobs** – LLM (Anthropic Claude or OpenAI GPT) extracts structured jobs with dates and descriptions
3. **Extract skills** – Regex `[text]{img}(url)` from descriptions
4. **Enrich** – Optional LLM pass to suggest URLs for skills without one

## Flock integration

When run from `workspace-resume/resume-parser`, the default output is `flock-of-postcards/static_content` if that path exists. Otherwise output goes to the current directory.

See [flock-of-postcards/docs/RESUME_TO_FLOCK_DESIGN.md](https://github.com/sbecker11/flock-of-postcards/blob/master/docs/RESUME_TO_FLOCK_DESIGN.md) for the full design.
