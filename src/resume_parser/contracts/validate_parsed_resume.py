#!/usr/bin/env python3
"""
Validate parsed resume data against parsed-resume-format-v1.0.json (same folder).
FAIL FAST: raises ValidationError on first schema violation.

Usage:
  # CLI (after pip install resume-parser):
  validate-parsed-resume /path/to/parsed_resumes/resume-id

  # Or as module:
  python -m resume_parser.contracts.validate_parsed_resume /path/to/parsed_resumes/resume-id

  # Validate Python dicts programmatically:
  from resume_parser.contracts.validate_parsed_resume import validate_jobs, validate_skills, validate_other_sections
  validate_jobs(jobs_dict)
  validate_skills(skills_dict)
  validate_other_sections(other_sections_dict)

Contract: resume-parser owns this validator and the schema (contracts/parsed-resume-format-v1.0.json).
"""

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    raise ImportError(
        "jsonschema required. Install with: pip install jsonschema"
    ) from None

# Schema lives alongside this script (versioned)
_SCHEMA_DIR = Path(__file__).resolve().parent
_SCHEMA_PATH = _SCHEMA_DIR / "parsed-resume-format-v1.0.json"


def _load_schema():
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _build_validator(def_name: str):
    """Build a validator for a $defs entry. Uses full schema for $ref resolution."""
    schema = _load_schema()
    # Use referencing.Registry (no deprecation); fallback to RefResolver on older jsonschema
    try:
        from referencing import Registry
        from referencing.jsonschema import DRAFT202012
        resource = DRAFT202012.create_resource(schema)
        uri = schema.get("$id", "urn:resume-parser:parsed-resume-format-v1.0")
        registry = Registry().with_resource(uri=uri, resource=resource)
        ref_schema = {"$ref": f"{uri}#/$defs/{def_name}"}
        validator_cls = getattr(jsonschema, "Draft202012Validator", jsonschema.Draft7Validator)
        return validator_cls(ref_schema, registry=registry)
    except ImportError:
        ref_schema = {"$ref": f"#/$defs/{def_name}"}
        resolver = jsonschema.RefResolver.from_schema(schema)
        validator_cls = getattr(jsonschema, "Draft202012Validator", jsonschema.Draft7Validator)
        return validator_cls(ref_schema, resolver=resolver)


def _load_json(path: Path) -> dict | list:
    """Load JSON file. Returns parsed value."""
    return json.loads(path.read_text(encoding="utf-8"))


def validate_jobs(data: dict | list) -> None:
    """Validate jobs (array or object keyed by jobID). Raises ValidationError on failure."""
    validator = _build_validator("jobs")
    validator.validate(data)


def validate_skills(data: dict) -> None:
    """Validate skills (object keyed by skillID). Raises ValidationError on failure."""
    validator = _build_validator("skills")
    validator.validate(data)


def validate_categories(data: dict) -> None:
    """Validate categories (object keyed by categoryID). Raises ValidationError on failure."""
    validator = _build_validator("categories")
    validator.validate(data)


def validate_other_sections(data: dict) -> None:
    """Validate otherSections object. Raises ValidationError on failure."""
    validator = _build_validator("otherSections")
    validator.validate(data)


def validate_meta(data: dict) -> None:
    """Validate meta.json object. Raises ValidationError on failure."""
    validator = _build_validator("meta")
    validator.validate(data)


def validate_folder(folder: str | Path) -> list[str]:
    """
    Validate all files in a parsed-resume folder. FAIL FAST.
    Returns list of validated file names. Raises on first error.
    """
    folder = Path(folder)
    validated = []

    jobs_path = folder / "jobs.json"
    if jobs_path.exists():
        jobs = _load_json(jobs_path)
        validate_jobs(jobs)
        validated.append("jobs.json")

    skills_path = folder / "skills.json"
    if skills_path.exists():
        skills = _load_json(skills_path)
        validate_skills(skills)
        validated.append("skills.json")

    categories_path = folder / "categories.json"
    if categories_path.exists():
        categories = _load_json(categories_path)
        validate_categories(categories)
        validated.append("categories.json")

    other_path = folder / "other-sections.json"
    if other_path.exists():
        other = _load_json(other_path)
        validate_other_sections(other)
        validated.append("other-sections.json")

    meta_path = folder / "meta.json"
    if meta_path.exists():
        meta = _load_json(meta_path)
        validate_meta(meta)
        validated.append("meta.json")

    return validated


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate-parsed-resume <parsed-resume-folder>", file=sys.stderr)
        return 1
    folder = sys.argv[1]
    try:
        validated = validate_folder(folder)
        print(f"Validated: {', '.join(validated)}")
        return 0
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 1
    except jsonschema.ValidationError as e:
        print(f"Schema validation failed: {e.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
