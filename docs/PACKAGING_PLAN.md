# Packaging Plan: resume-parser as pip-installable package

Goal: Consumers install with `resume-parser==1.0.0` in `requirements.txt` and get CLI commands + importable API.

---

## 1. Package name and layout

- **PyPI / pip name:** `resume-parser` (hyphen; pip normalizes to `resume_parser` for import).
- **Import name:** `resume_parser` (one top-level package).
- **Layout:** **src layout** (recommended for avoiding accidental imports from repo root).

```
resume-parser/
  pyproject.toml
  src/
    resume_parser/
      __init__.py          # __version__ = "1.0.0"
      extractors.py        # (move from root)
      parsers.py           # (move from root)
      skill_merge.py       # (move from root)
      resume_to_flock.py   # (move from root) — or keep as CLI-only entry
      render_resume_html.py
      run_merge_on_parsed.py  # (move from scripts/)
      contracts/           # package data (see below)
        validate_parsed_resume.py
        parsed-resume-format-v1.0.json
        *.md
        requirements.txt
      templates/
        resume.html
  tests/                   # stay at repo root, not installed
  contracts/               # stay at repo root for dev; package gets copy from src/resume_parser/contracts
  ...
```

**Alternative (flat layout):** Keep current file positions and add `pyproject.toml` with `packages = find:` and `package-dir = {"": "."}` so `resume_parser` is a namespace that collects root modules. That requires introducing an actual `resume_parser/` directory and either moving code into it or using a namespace. **Recommended:** src layout and move code into `src/resume_parser/` for a clean boundary.

---

## 2. What gets installed

| Item | Location in repo (current) | In package |
|------|----------------------------|------------|
| Core logic | extractors.py, parsers.py, skill_merge.py | `src/resume_parser/*.py` |
| Main CLI | resume_to_flock.py | `resume_parser.resume_to_flock` + entry point |
| HTML render | render_resume_html.py | `resume_parser.render_resume_html` + entry point |
| Merge script | scripts/run_merge_on_parsed.py | `resume_parser.run_merge_on_parsed` + entry point |
| Validator | contracts/validate_parsed_resume.py | `resume_parser.contracts.validate_parsed_resume` + entry point |
| Schema | contracts/parsed-resume-format-v1.0.json | Package data under `resume_parser/contracts/` |
| Contract docs | contracts/*.md | Package data (optional; or docs-only, not installed) |
| Template | templates/resume.html | Package data under `resume_parser/templates/` |

- **Tests, docs/, .env, parsed_resumes/:** Not installed (excluded or outside package dir).

---

## 3. pyproject.toml (minimal)

```toml
[build-system]
requires = ["setuptools>=61", "setuptools-scm[toml]>=7"]
build-backend = "setuptools.build_meta"

[project]
name = "resume-parser"
version = "1.0.0"
description = "Parse resume documents (DOCX/PDF) into flock-of-postcards JSON and HTML"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
dependencies = [
  "python-docx>=1.0.0",
  "pdfplumber>=0.10.0",
  "anthropic>=0.18.0",
  "openai>=1.0.0",
  "python-dotenv>=1.0.0",
  "Jinja2>=3.0.0",
  "markupsafe>=2.0",
  "jsonschema>=4.0.0",
]

[project.optional-dependencies]
dev = [
  "coverage>=7.0.0",
  "pytest>=7.0.0",
]

[project.scripts]
resume-to-flock = "resume_parser.resume_to_flock:main"
render-resume-html = "resume_parser.render_resume_html:main"
run-merge-on-parsed = "resume_parser.run_merge_on_parsed:main"
validate-parsed-resume = "resume_parser.contracts.validate_parsed_resume:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
resume_parser = [
  "contracts/*.json",
  "contracts/*.md",
  "contracts/validate_parsed_resume.py",
  "contracts/requirements.txt",
  "templates/*.html",
]
```

- `main` for each script must be the callable that runs the CLI (e.g. `sys.exit(main())` or return int). Each module’s `if __name__ == "__main__": sys.exit(main())` stays; entry points will call `main()`.
- Validator and schema: validator lives at `resume_parser/contracts/validate_parsed_resume.py` and must resolve schema path relative to `__file__` (e.g. `Path(__file__).resolve().parent / "parsed-resume-format-v1.0.json"`) so it works when installed.

---

## 4. Versioning

- **Single source of truth:** `version = "1.0.0"` in `pyproject.toml` (or use `setuptools-scm` and derive from git tags, e.g. `version = { dynamic = ["version"] }` plus `[tool.setuptools_scm]`).
- Optional: `src/resume_parser/__init__.py` with `__version__ = "1.0.0"` for runtime (can be generated from pyproject in CI if desired).
- Consumer pins in `requirements.txt`: `resume-parser==1.0.0` (two equals for exact version).

---

## 5. Data files and paths

- **Templates:** `render_resume_html` currently uses `Path(__file__).resolve().parent / "templates"`. After move, `__file__` will be inside `src/resume_parser/`, so `resume_parser/templates/resume.html` must be included as package data; path stays correct.
- **Contracts:** Same idea: `contracts/validate_parsed_resume.py` will live under `resume_parser/contracts/` and load `parsed-resume-format-v1.0.json` from the same directory; include both in package data.
- **.env:** Not shipped; consumer sets env (e.g. `ANTHROPIC_API_KEY`) in their environment. Document in README.

---

## 6. Implementation steps (ordered)

1. **Create `src/resume_parser/`** and add `__init__.py` with `__version__ = "1.0.0"`.
2. **Move modules** from root into `src/resume_parser/`: extractors, parsers, skill_merge, resume_to_flock, render_resume_html. Move `scripts/run_merge_on_parsed.py` into `src/resume_parser/`. Adjust internal imports (e.g. `from extractors` → `from resume_parser.extractors` or relative).
3. **Copy contracts and templates** into `src/resume_parser/`: create `src/resume_parser/contracts/` (validator, schema, .md, requirements.txt) and `src/resume_parser/templates/` (resume.html). Update validator’s schema path to the same directory.
4. **Fix imports** in all moved modules (resume_to_flock, render_resume_html, run_merge_on_parsed, validate_parsed_resume) so they work when run as part of `resume_parser` (no `sys.path.insert` for repo root).
5. **Add `pyproject.toml`** at repo root with the content above; set `version` and entry points. Add `[tool.setuptools.package-data]` so contracts and templates are included.
6. **Ensure each CLI has a `main()`** that returns an int (or calls `sys.exit`). Entry points will call `main()`.
7. **Test local install:** From repo root, `pip install -e .` then run `resume-to-flock --help`, `render-resume-html --help`, `validate-parsed-resume --help`, `run-merge-on-parsed --help`. Run existing tests (adjust test imports to use `resume_parser`).
8. **Optional:** Add `setuptools-scm` and use git tags for version (e.g. `git tag 1.0.0` then build).
9. **Build and publish:** `python -m build` → upload to PyPI (or private index). Consumer then uses `resume-parser==1.0.0` in requirements.txt.

---

## 7. Consumer usage after publish

```text
# requirements.txt
resume-parser==1.0.0
```

```bash
pip install -r requirements.txt
resume-to-flock path/to/resume.docx -o ./out
render-resume-html -i ./out
validate-parsed-resume ./out
run-merge-on-parsed ./out --render
```

Optional programmatic use:

```python
from resume_parser import render_resume_html
from pathlib import Path
render_resume_html.render_resume_html(Path("./out"))
```

---

## 8. What stays outside the package

- **tests/** — Not installed; run with `pytest` from repo or `pip install -e ".[dev]"` in dev.
- **docs/** — Repo-only unless you add them as package data.
- **.env, .gitignore, parsed_resumes/** — Repo-only.
- **Root `contracts/` and `templates/`** — Can remain for development; the built wheel uses the copies under `src/resume_parser/`.

---

## 9. Checklist before first release

- [ ] All CLI entry points callable and documented.
- [ ] Validator and render_resume_html resolve schema/template paths when run from installed package.
- [ ] No hardcoded repo-root paths; use `__file__` or `importlib.resources`.
- [ ] README has install and usage for pip consumers.
- [ ] Version bumped and tagged (e.g. `1.0.0`).
- [ ] Optional: Add `markupsafe` and `jsonschema` to `dependencies` if not already (render + validator).

---

## 10. Note on requirements.txt syntax

Consumer line is **`resume-parser==1.0.0`** (two equals for exact version in pip/requirements.txt).
