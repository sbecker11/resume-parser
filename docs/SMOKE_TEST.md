# Manual Smoke Test: resume-parser

## Prerequisites

- Virtual environment activated: `source .venv/bin/activate`
- `.env` with `ANTHROPIC_API_KEY` set
- Run from repo root (so `tests/test-resume.docx` is available)

---

## 1. Full pipeline (parse → .mjs)

```bash
python resume_to_flock.py tests/test-resume.docx -o /tmp/resume-output
```

- [ ] Exits without errors
- [ ] Output folder has: `jobs.mjs`, `skills.mjs`, `categories.mjs`, `other-sections.mjs`
- [ ] Resume copy exists (same filename)

---

## 2. Full pipeline with `--no-merge` (non-interactive)

```bash
python resume_to_flock.py tests/test-resume.docx -o /tmp/resume-output --no-merge
```

- [ ] Runs without prompts
- [ ] Same four .mjs files generated

---

## 3. Full pipeline with HTML render

```bash
python resume_to_flock.py tests/test-resume.docx -o /tmp/resume-output --no-merge --render
```

- [ ] `resume.html` and `resume_template.html` exist
- [ ] Open `resume.html` in a browser; layout and content match the resume

---

## 4. Skill merge (interactive)

```bash
python resume_to_flock.py tests/test-resume.docx -o /tmp/resume-output
```

(Use a resume with multiple skills; skip `--no-merge` for this step.)

- [ ] Prompt appears: `Merge "X" + "Y" → "Z"? [y/n/a/q]:`
- [ ] `y` applies merge and continues
- [ ] `n` skips and continues
- [ ] `q` exits the merge loop
- [ ] Output `skills.mjs` reflects chosen merges

---

## 5. Standalone HTML render

```bash
# Ensure output folder has .mjs files from step 1, 2, or 3
python render_resume_html.py -i /tmp/resume-output
```

- [ ] Exits without errors
- [ ] `resume.html` and `resume_template.html` updated
- [ ] HTML content is consistent with .mjs data

---

## 6. Text extraction only

```bash
python resume_to_flock.py tests/test-resume.docx --no-llm
```

- [ ] Prints first ~500 characters of extracted text
- [ ] Exits 0 (no LLM calls)

---

## 7. Unit tests

```bash
python -m unittest discover -s tests
```

- [ ] All tests pass
