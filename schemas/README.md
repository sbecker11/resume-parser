# Schemas (moved to contracts)

The JSON Schema and validator are now owned and versioned under **contracts/**:

- **contracts/parsed-resume-format-v1.0.json** — JSON Schema for parsed resume output
- **contracts/validate_parsed_resume.py** — Python validator
- **contracts/requirements.txt** — `jsonschema` dependency

Run validation from repo root:

```bash
python contracts/validate_parsed_resume.py /path/to/parsed_resumes/resume-id
```

See **contracts/README.md** for the full contract list.
