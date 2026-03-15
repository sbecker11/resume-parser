#!/usr/bin/env python3
"""
Generate resume.html from .mjs files. Run separately after resume_to_flock.py.

Usage:
  python render_resume_html.py -i /path/to/output-folder

Reads jobs.mjs, skills.mjs, categories.mjs, other-sections.mjs from the input dir.
Writes resume.html and resume_template.html to the same dir.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Script dir for templates
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"


def _load_mjs(path: Path, var_name: str) -> dict | list:
    """Load a .mjs file and return the JSON value. Accepts 'export const varName = ...' or 'const varName = ...'."""
    text = path.read_text(encoding="utf-8")
    # Match optional "export " then "const varName = " then capture JSON
    pattern = rf"(?:export\s+)?const\s+{re.escape(var_name)}\s*=\s*(.+)"
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        raise ValueError(f"Could not find const {var_name} = ... in {path}")
    json_str = m.group(1).strip().rstrip(";").strip()
    return json.loads(json_str)


def _linkify(text: str):
    """Wrap http(s) URLs in <a> tags. Returns markup-safe string."""
    from markupsafe import Markup, escape
    if not text:
        return ""
    pattern = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
    parts = pattern.split(text)
    matches = pattern.findall(text)
    result = escape(parts[0])
    for i, url in enumerate(matches):
        safe_url = escape(url)
        result += Markup('<a href="') + safe_url + Markup('">') + safe_url + Markup("</a>")
        result += escape(parts[i + 1])
    return Markup(result)


def _description_bullets(desc: str) -> list[str]:
    """Split job description into bullet points."""
    if not desc or not str(desc).strip():
        return []
    text = str(desc).strip()
    if "•" in text:
        return [p.strip() for p in text.split("•") if p.strip()]
    parts = [p.strip() for p in text.split(". ") if p.strip()]
    return [p if p.endswith(".") else p + "." for p in parts]


def _jobs_dict_to_list(jobs: dict) -> list[dict]:
    """Convert jobs dict (jobID -> job) to list ordered by jobID."""
    def sort_key(k):
        try:
            return int(k)
        except ValueError:
            return k
    return [jobs[k] for k in sorted(jobs.keys(), key=sort_key)]


def _build_skills_by_name(skills: dict) -> dict[str, dict]:
    """Convert skills (id-keyed) to name-keyed for template."""
    return {data["name"]: data for data in skills.values()}


def _build_skills_by_category(categories: dict, skills: dict) -> list[dict]:
    """Build list of {name: category name, skills: [skill names]} for template."""
    result = []
    for cat in categories.values():
        names = [skills[sid]["name"] for sid in cat.get("skillIDs", []) if sid in skills]
        if names:
            result.append({"name": cat["name"], "skills": names})
    # Skills without category
    catted = {sid for cat in categories.values() for sid in cat.get("skillIDs", [])}
    uncatted = [data["name"] for sid, data in skills.items() if data.get("name") and sid not in catted]
    if uncatted:
        result.append({"name": "Other", "skills": uncatted})
    return result


def render_resume_html(input_dir: Path) -> tuple[Path, Path]:
    """
    Read .mjs files from input_dir, render HTML, write resume.html and resume_template.html.
    Returns (resume_path, template_copy_path).
    """
    from jinja2 import Environment, FileSystemLoader

    jobs_path = input_dir / "jobs.mjs"
    skills_path = input_dir / "skills.mjs"
    categories_path = input_dir / "categories.mjs"
    other_path = input_dir / "other-sections.mjs"

    for p in (jobs_path, skills_path, categories_path, other_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing {p.name} in {input_dir}")

    jobs_dict = _load_mjs(jobs_path, "jobs")
    skills_dict = _load_mjs(skills_path, "skills")
    categories_dict = _load_mjs(categories_path, "categories")
    other = _load_mjs(other_path, "otherSections")

    jobs_list = _jobs_dict_to_list(jobs_dict)
    jobs_with_bullets = [
        {**job, "description_bullets": _description_bullets(job.get("Description") or "")}
        for job in jobs_list
    ]

    skills_by_name = _build_skills_by_name(skills_dict)
    skills_by_category = _build_skills_by_category(categories_dict, skills_dict)

    contact = other.get("contact") or {}
    title = other.get("title") or ""
    summary = other.get("summary") or ""
    certifications = other.get("certifications") or []
    other_sections = other.get("custom_sections") or other.get("other_sections") or []

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters["linkify"] = lambda s: _linkify(s) if s else ""

    template = env.get_template("resume.html")
    html = template.render(
        contact=contact,
        title=title,
        summary=summary,
        jobs=jobs_with_bullets,
        skills=skills_by_name,
        categories=categories_dict,
        skills_by_category=skills_by_category,
        certifications=certifications,
        other_sections=other_sections,
    )

    input_dir.mkdir(parents=True, exist_ok=True)
    resume_path = input_dir / "resume.html"
    resume_path.write_text(html, encoding="utf-8")

    template_src = TEMPLATES_DIR / "resume.html"
    template_dest = input_dir / "resume_template.html"
    if template_src.exists():
        import shutil
        shutil.copy2(template_src, template_dest)

    return resume_path, template_dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate resume.html from .mjs files")
    parser.add_argument(
        "-i", "--input-dir",
        type=Path,
        required=True,
        help="Directory containing jobs.mjs, skills.mjs, categories.mjs, other-sections.mjs",
    )
    args = parser.parse_args()
    try:
        resume_path, template_path = render_resume_html(args.input_dir)
        print(f"Wrote {resume_path}")
        print(f"Wrote {template_path}")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
