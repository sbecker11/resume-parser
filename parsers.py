#!/usr/bin/env python3
"""
Parse extracted resume text into jobs and skills for flock-of-postcards.
"""

import json
import os
import re
from typing import Any


# Pattern: [text]{img}(url) where img and url are optional
# Matches: [SkillName], [SkillName](url), [SkillName]{img}(url)
SKILL_PATTERN = re.compile(r"\[([^\]]+)\](?:\{([^\}]+)\})?(?:\(([^\)]+)\))?")

# Default color palette for bizcards (hex RGB)
DEFAULT_PALETTE = [
    "#116611", "#0069AC", "#006688", "#0000ff", "#4400cd", "#8a2be2",
    "#800080", "#800000", "#ff4500", "#ffa500", "#008080", "#008b8b",
]


def parse_jobs_with_llm(raw_text: str) -> list[dict[str, Any]]:
    """
    Use Anthropic Claude to extract structured jobs from resume text.
    Returns list of job dicts with role, employer, start, end, description.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Set it in .env or environment.")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    system_prompt = """You are a resume parser. Extract work experience and education entries from the resume text.
Output valid JSON only, no markdown or explanation. Use this exact schema:
{
  "jobs": [
    {
      "role": "string (job title)",
      "employer": "string (company/organization)",
      "start": "YYYY-MM-DD (use first day of month if only month/year given)",
      "end": "YYYY-MM-DD or CURRENT_DATE for present/current roles",
      "employer_city": "string or null",
      "employer_website": "string or null",
      "description": "string with bullet points (•) for each achievement. Preserve [bracketed] skill terms exactly as written."
    }
  ]
}
Rules:
- One job per experience block
- Normalize dates: "Aug 2024" -> "2024-08-01", "Present" -> "CURRENT_DATE"
- Keep [SkillName] and [SkillName](url) markup in descriptions
- Use • as bullet delimiter
"""

    user_prompt = f"Extract all work experience and education from this resume:\n\n{raw_text}"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text
    # Strip markdown code blocks if present
    if "```" in text:
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
    data = json.loads(text.strip())
    return data.get("jobs", [])


def extract_skills_from_text(text: str) -> dict[str, dict[str, str]]:
    """
    Extract skills from text using [text]{img}(url) pattern.
    Returns dict: skill_name -> { url: "", img: "" }
    Merges duplicates, preferring non-empty url/img.
    """
    skills: dict[str, dict[str, str]] = {}
    for match in SKILL_PATTERN.finditer(text):
        name = match.group(1).strip()
        img = (match.group(2) or "").strip()
        url = (match.group(3) or "").strip()

        if not name:
            continue

        if name not in skills:
            skills[name] = {"url": "", "img": ""}

        if url and not skills[name]["url"]:
            skills[name]["url"] = url
        if img and not skills[name]["img"]:
            skills[name]["img"] = img

    return skills


def enrich_skills_with_llm(skills: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """
    Use LLM to suggest URLs for skills that don't have one.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return skills

    skills_needing_url = [name for name, data in skills.items() if not data.get("url")]
    if not skills_needing_url:
        return skills

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    prompt = f"""For each of these skills/technologies, suggest the official or canonical URL (e.g., Python -> https://python.org).
Output valid JSON only:
{{ "suggestions": [ {{ "name": "SkillName", "url": "https://..." }} ] }}

Skills: {json.dumps(skills_needing_url)}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        if "```" in text:
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = re.sub(r"```\s*$", "", text)
        data = json.loads(text.strip())
        for item in data.get("suggestions", []):
            name = item.get("name")
            url = (item.get("url") or "").strip()
            if name and url and name in skills:
                skills[name]["url"] = url
    except Exception:
        pass  # Keep original skills on failure

    return skills


def jobs_to_flock_format(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert parsed jobs to flock-of-postcards jobs.mjs format.
    Adds index, z-index, css name, css RGB, text color, Description.
    """
    result = []
    for i, job in enumerate(jobs):
        color_hex = DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]
        # Use black text for light backgrounds, white for dark
        r, g, b = _hex_to_rgb(color_hex)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        text_color = "#000000" if luminance > 0.5 else "#FFFFFF"

        flock_job = {
            "index": i,
            "role": (job.get("role") or "").strip(),
            "employer": (job.get("employer") or "").strip(),
            "start": _normalize_date(job.get("start")),
            "end": _normalize_end_date(job.get("end")),
            "z-index": (i % 3) + 1,
            "css name": _css_name_from_hex(color_hex),
            "css RGB": color_hex,
            "css color": None,
            "text color": text_color,
            "Description": (job.get("description") or "").strip(),
        }
        result.append(flock_job)
    return result


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4))


def _css_name_from_hex(hex_str: str) -> str:
    """Simple mapping for common colors; otherwise generic."""
    mapping = {
        "#116611": "darkforest",
        "#0069AC": "darkcyan",
        "#006688": "darkcyan",
        "#0000ff": "blue",
        "#4400cd": "mediumblue",
        "#8a2be2": "blueviolet",
        "#800080": "purple",
        "#800000": "maroon",
        "#ff4500": "orangered",
        "#ffa500": "orange",
        "#008080": "teal",
        "#008b8b": "darkcyan",
        "#dc143c": "crimson",
    }
    return mapping.get(hex_str.upper(), "darkgreen")


def _normalize_date(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip()
    if s.upper() == "CURRENT_DATE":
        return "CURRENT_DATE"
    # Already YYYY-MM-DD
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    return s


def _normalize_end_date(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip()
    if s.upper() in ("CURRENT_DATE", "PRESENT", "CURRENT"):
        return "CURRENT_DATE"
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    return s
