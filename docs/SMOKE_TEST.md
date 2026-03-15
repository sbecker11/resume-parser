# Manual Smoke Test: resume-parser

Covers all four CLI utilities: `resume_to_flock.py`, `render_resume_html.py`, `scripts/run_merge_on_parsed.py`, `contracts/validate_parsed_resume.py`.

## Prerequisites

- Virtual environment activated: `source .venv/bin/activate`
- `.env` with `ANTHROPIC_API_KEY` set (for parse and merge steps)
- Run from repo root (so `tests/test-resume.docx` is available)
- For validation: `pip install jsonschema` (see `contracts/requirements.txt` if needed)

---

## 1. Full pipeline (parse → JSON) — `resume_to_flock.py`

```bash
python resume_to_flock.py tests/test-resume.docx -o /tmp/resume-output
```

- [ ] Exits without errors
- [ ] Output folder has: `jobs.json`, `skills.json`, `categories.json`, `other-sections.json`
- [ ] Resume copy exists (same filename)

---

## 2. Full pipeline with `--no-merge` (non-interactive) — `resume_to_flock.py`

```bash
python resume_to_flock.py tests/test-resume.docx -o /tmp/resume-output --no-merge
```

- [ ] Runs without prompts
- [ ] Same four .json files generated

---

## 3. Full pipeline with HTML render — `resume_to_flock.py`

```bash
python resume_to_flock.py tests/test-resume.docx -o /tmp/resume-output --no-merge --render
```

- [ ] `resume.html` and `resume_template.html` exist
- [ ] Open `resume.html` in a browser; layout and content match the resume

---

## 4. Skill merge (interactive) — `resume_to_flock.py`

```bash
python resume_to_flock.py tests/test-resume.docx -o /tmp/resume-output
```

(Use a resume with multiple skills; skip `--no-merge` for this step.)

- [ ] Prompt appears: `Merge "X" + "Y" → "Z"? [y/n/a/q]:`
- [ ] `y` applies merge and continues
- [ ] `n` skips and continues
- [ ] `q` exits the merge loop
- [ ] Output `skills.json` reflects chosen merges

---

## 5. Standalone HTML render — `render_resume_html.py`

```bash
# Ensure output folder has .json files from step 1, 2, or 3
python render_resume_html.py -i /tmp/resume-output
```

- [ ] Exits without errors
- [ ] `resume.html` and `resume_template.html` updated
- [ ] HTML content is consistent with JSON data

---

## 6. Run merge on existing parsed folder — `scripts/run_merge_on_parsed.py`

`run_merge_on_parsed.py` reads `jobs.json`, `skills.json`, and `categories.json` from a parsed folder, runs the LLM skill-merge step (interactive or `--accept-all`), writes back updated JSON and job descriptions, and optionally re-renders HTML.

```bash
# One folder (interactive merge prompts)
python scripts/run_merge_on_parsed.py /tmp/resume-output --render

# All subfolders of parsed_resumes, apply all suggested merges, then render
python scripts/run_merge_on_parsed.py parsed_resumes --all --accept-all --render
```

- [ ] Exits without errors when `ANTHROPIC_API_KEY` is set
- [ ] Interactive: merge prompts appear; `y`/`n`/`a`/`q` work
- [ ] Output: `skills.json`, `categories.json`, `jobs.json` updated; skill count reported (e.g. `Skills: 162 → 161`)
- [ ] With `--render`: `resume.html` regenerated

---

## 7. Validate parsed resume folder — `contracts/validate_parsed_resume.py`

Validates a folder’s JSON files and `meta.json` against `contracts/parsed-resume-format-v1.0.json`. Requires `jsonschema` (`pip install jsonschema` or use `contracts/requirements.txt`).

```bash
# Use output from step 1, 2, or 3
python contracts/validate_parsed_resume.py /tmp/resume-output
```

- [ ] Exits 0 and prints e.g. `Validated: jobs.json, skills.json, categories.json, other-sections.json, meta.json`
- [ ] Invalid or missing files raise ValidationError or FileNotFoundError

---

## 8. Text extraction only — `resume_to_flock.py`

```bash
python resume_to_flock.py tests/test-resume.docx --no-llm
```

- [ ] Prints first ~500 characters of extracted text
- [ ] Exits 0 (no LLM calls)

---

## 9. Unit tests

```bash
python -m unittest discover -s tests
```

- [ ] All tests pass
