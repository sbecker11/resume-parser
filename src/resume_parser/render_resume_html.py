#!/usr/bin/env python3
"""
Generate resume.html from JSON files. Run separately after resume-to-flyer.

Usage:
  render-resume-html -i /path/to/output-folder

Reads jobs.json, skills.json, categories.json, other-sections.json from the input dir.
Writes resume.html and resume_template.html to the same dir.

Contract: see contracts/RENDER_RESUME_HTML-v1.0.md (used by resume-flyer to invoke this script).
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Templates live next to this package module (works when installed)
_PKG_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = _PKG_DIR / "templates"


def _load_json(path: Path) -> dict | list:
    """Load a JSON file and return the parsed value."""
    return json.loads(path.read_text(encoding="utf-8"))


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


def _strip_square_brackets(text: str) -> str:
    """Remove [ and ] from text (e.g. [Python] -> Python)."""
    if not text:
        return ""
    return str(text).replace("[", "").replace("]", "")


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


def render_resume_html(input_dir: Path, skip_square_brackets: bool = True) -> tuple[Path, Path]:
    """
    Read JSON files from input_dir, render HTML, write resume.html and resume_template.html.
    If skip_square_brackets is True (default), remove [ and ] from job descriptions, summary, and other section content.
    Returns (resume_path, template_copy_path).
    """
    from jinja2 import Environment, FileSystemLoader

    jobs_path = input_dir / "jobs.json"
    skills_path = input_dir / "skills.json"
    categories_path = input_dir / "categories.json"
    other_path = input_dir / "other-sections.json"

    for p in (jobs_path, skills_path, categories_path, other_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing {p.name} in {input_dir}")

    jobs_dict = _load_json(jobs_path)
    skills_dict = _load_json(skills_path)
    categories_dict = _load_json(categories_path)
    other = _load_json(other_path)

    jobs_list = _jobs_dict_to_list(jobs_dict)
    jobs_with_bullets = []
    for job in jobs_list:
        bullets = _description_bullets(job.get("Description") or "")
        if skip_square_brackets:
            bullets = [_strip_square_brackets(b) for b in bullets]
        jobs_with_bullets.append({**job, "description_bullets": bullets})

    skills_by_name = _build_skills_by_name(skills_dict)
    skills_by_category = _build_skills_by_category(categories_dict, skills_dict)

    contact = other.get("contact") or {}
    title = other.get("title") or ""
    summary = other.get("summary") or ""
    if skip_square_brackets:
        summary = _strip_square_brackets(summary)
    certifications = other.get("certifications") or []
    websites = other.get("websites") or []
    other_sections = other.get("custom_sections") or other.get("other_sections") or []
    if skip_square_brackets and other_sections:
        other_sections = [
            {**sec, "content": _strip_square_brackets(sec.get("content") or "")}
            for sec in other_sections
        ]

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
        websites=websites,
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
    parser = argparse.ArgumentParser(description="Generate resume.html from JSON files")
    parser.add_argument(
        "-i", "--input-dir",
        type=Path,
        required=True,
        help="Directory containing jobs.json, skills.json, categories.json, other-sections.json",
    )
    parser.add_argument(
        "--show-brackets",
        dest="show_square_brackets",
        action="store_true",
        help="Keep square brackets in job descriptions, summary, and other section content (default: strip them, e.g. [Python] -> Python)",
    )
    args = parser.parse_args()
    try:
        resume_path, template_path = render_resume_html(args.input_dir, skip_square_brackets=not args.show_square_brackets)
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
