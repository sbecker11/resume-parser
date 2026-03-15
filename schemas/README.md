# Parsed Resume Format — Schema & Validator

Shared with **resume-parser** and used by **resume-flock** for format conformance.

## Files

- **PARSED-RESUME-JSON-FORMAT.md** — Contract spec (directory layout, schemas, validation rules)
- **parsed-resume-format.json** — JSON Schema (draft 2020-12) with `$defs` for jobs, skills, categories, otherSections, meta
- **validate_parsed_resume.py** — Python validator; FAIL FAST on schema violations

## Resume-Parser Integration

Copy or symlink this folder into the resume-parser repo:

```bash
# From resume-flock repo root
cp -r schemas /path/to/resume-parser/schemas
# or
ln -s /path/to/resume-flock/schemas /path/to/resume-parser/schemas
```

Install dependency (in resume-parser venv or env):

```bash
pip install -r schemas/requirements.txt
# or: pip install jsonschema
```

Validate after writing output:

```python
from schemas.validate_parsed_resume import validate_jobs, validate_skills, validate_other_sections

# After parser produces jobs, skills, etc.
validate_jobs(jobs)       # dict or list
validate_skills(skills)   # dict
validate_other_sections(other_sections)  # dict
```

Or validate a folder from the command line:

```bash
python schemas/validate_parsed_resume.py /path/to/parsed_resumes/resume-id
```

## Spec

See `PARSED-RESUME-JSON-FORMAT.md` in this folder.
