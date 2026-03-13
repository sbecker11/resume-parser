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

# Match "Prefix (item1, item2, ...)" for expanding into "Prefix item1", "Prefix item2", ...
_PAREN_SKILL_PATTERN = re.compile(r"^(.+?)\s*\(([^)]+)\)\s*$")
# In text: "Name (a,b,c)" as substring — replace with "Name a, Name b, Name c".
# Name = token(s) immediately before " ("; allow / and - (e.g. CI/CD, AWS)
_PAREN_SKILL_AT_START = re.compile(r"^([^\s(]+(?:\s+[^\s(]+)*)\s*\(([^)]+)\)", re.MULTILINE)
_PAREN_SKILL_AFTER_SPACE = re.compile(r"(\s+)([^\s(]+(?:\s+[^\s(]+)*)\s*\(([^)]+)\)")


def expand_skill_parens(name: str) -> list[str]:
    """
    If name is "Prefix (a, b, c)", return ["Prefix a", "Prefix b", "Prefix c"].
    Otherwise return [name].
    """
    name = (name or "").strip()
    if not name:
        return []
    m = _PAREN_SKILL_PATTERN.match(name)
    if not m:
        return [name]
    prefix = m.group(1).strip()
    if not prefix:
        return [name]
    items = [x.strip() for x in m.group(2).split(",") if x.strip()]
    if not items:
        return [name]
    return [f"{prefix} {item}" for item in items]


def expand_parens_in_text(text: str) -> str:
    """
    In the original input string, replace each "Name (a,b,c)" with "Name a, Name b, Name c".
    """
    if not text or not text.strip():
        return text

    def repl_start(m: re.Match) -> str:
        prefix = m.group(1).strip()
        items = [x.strip() for x in m.group(2).split(",") if x.strip()]
        if not prefix or not items:
            return m.group(0)
        return ", ".join(f"{prefix} {item}" for item in items)

    def repl_after(m: re.Match) -> str:
        space = m.group(1)
        prefix = m.group(2).strip()
        items = [x.strip() for x in m.group(3).split(",") if x.strip()]
        if not prefix or not items:
            return m.group(0)
        return space + ", ".join(f"{prefix} {item}" for item in items)

    # After-space first so "Used AWS (S3,...)" → "Used AWS S3, ..." (prefix "AWS"); then start-of-string
    text = _PAREN_SKILL_AFTER_SPACE.sub(repl_after, text)
    text = _PAREN_SKILL_AT_START.sub(repl_start, text)
    return text


# Default color palette for bizcards (hex RGB)
DEFAULT_PALETTE = [
    "#116611", "#0069AC", "#006688", "#0000ff", "#4400cd", "#8a2be2",
    "#800080", "#800000", "#ff4500", "#ffa500", "#008080", "#008b8b",
]


def get_llm_provider() -> str:
    """Return LLM provider name ('anthropic') if ANTHROPIC_API_KEY is set, else raise.
    Optional: set LLM_PROVIDER=anthropic to force Anthropic (still requires ANTHROPIC_API_KEY).
    """
    forced = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if forced == "anthropic":
        key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        if key:
            return "anthropic"
        raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY not set.")
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return "anthropic"
    raise RuntimeError(
        "No LLM API key set. Set ANTHROPIC_API_KEY (LLM_PROVIDER=anthropic) in .env or environment."
    )


def _llm_provider() -> tuple[str, object]:
    """Return (LLM provider name, client). Uses LLM_PROVIDER / ANTHROPIC_API_KEY; Anthropic only."""
    provider = get_llm_provider()
    if provider == "anthropic":
        from anthropic import Anthropic
        return ("anthropic", Anthropic(api_key=(os.environ.get("ANTHROPIC_API_KEY") or "").strip()))
    raise RuntimeError("Unsupported LLM provider")


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> str:
    """Call LLM (provider from get_llm_provider / LLM_PROVIDER) and return response text. Anthropic only."""
    provider, client = _llm_provider()
    if provider == "anthropic":
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text
    raise RuntimeError("Unsupported LLM provider")


def parse_jobs_with_llm(raw_text: str) -> list[dict[str, Any]]:
    """
    Use LLM (LLM_PROVIDER=anthropic, ANTHROPIC_API_KEY) to extract structured jobs from resume text.
    Returns list of job dicts with role, employer, start, end, description.
    """
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
      "description": "string with bullet points (•) for each achievement."
    }
  ]
}
Rules:
- One job per experience block
- Normalize dates: "Aug 2024" -> "2024-08-01", "Present" -> "CURRENT_DATE"
- Use • as bullet delimiter
- IMPORTANT: Wrap every technology, framework, tool, and skill in [SkillName] brackets. Examples:
  "Python and Pandas" -> "[Python] and [Pandas]"
  "AWS SageMaker" -> "[AWS SageMaker]" or "[AWS] [SageMaker]"
  "React 19/Node.js" -> "[React] [Node.js]"
  "LangChain and ChromaDB" -> "[LangChain] and [ChromaDB]"
  Include programming languages, frameworks, cloud services, databases, tools, and methodologies.
"""

    user_prompt = f"Extract all work experience and education from this resume:\n\n{raw_text}"
    text = _call_llm(system_prompt, user_prompt)

    # Strip markdown code blocks if present
    if "```" in text:
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
    data = json.loads(text.strip())
    return data.get("jobs", [])


def parse_resume_sections(raw_text: str) -> dict[str, Any]:
    """
    Use LLM to extract contact, summary, certifications, skills section, and other sections
    (everything except work/education jobs). Returns a dict suitable for JSON.
    """
    system_prompt = """You are a resume parser. Extract everything that is NOT work experience or education.
Output valid JSON only, no markdown or explanation. Use this exact schema:
{
  "contact": {
    "name": "string or empty",
    "email": "string or empty",
    "phone": "string or empty",
    "location": "string or empty",
    "linkedin": "string or empty",
    "website": "string or empty"
  },
  "title": "string (professional title / headline, e.g. Data Engineer, Full Stack Developer; empty if absent)",
  "summary": "string (professional summary / objective; empty if absent)",
  "certifications": [ { "name": "string", "issuer": "string or empty", "date": "string or empty" } ],
  "skills": [ "string" ],
  "other_sections": [ { "title": "string (section heading)", "content": "string" } ]
}
Rules:
- contact: fill only the fields present in the resume; use "" for missing.
- title: the resume headline or professional title (often under the name).
- summary: the main summary/objective paragraph.
- certifications: list each certification with name; add issuer and date if present.
- skills: the explicit skills list (e.g. "Skills" section); do not duplicate technologies from job descriptions.
- other_sections: any other sections (e.g. Publications, Patents, Volunteer, Awards, Languages). Use title for the section heading and content for the body text.
- If a section is absent, use empty string or empty array as appropriate.
"""

    user_prompt = f"Extract contact, summary, certifications, skills, and other sections from this resume (exclude work experience and education):\n\n{raw_text}"
    text = _call_llm(system_prompt, user_prompt, max_tokens=4096)

    if "```" in text:
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
    data = json.loads(text.strip())

    # Normalize to expected keys
    return {
        "contact": data.get("contact") or {},
        "title": data.get("title") or "",
        "summary": data.get("summary") or "",
        "certifications": data.get("certifications") or [],
        "skills": data.get("skills") or [],
        "other_sections": data.get("other_sections") or [],
    }


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

        for n in expand_skill_parens(name):
            if not n:
                continue
            if n not in skills:
                skills[n] = {"url": "", "img": ""}
            if url and not skills[n]["url"]:
                skills[n]["url"] = url
            if img and not skills[n]["img"]:
                skills[n]["img"] = img

    return skills


def enrich_skills_with_llm(skills: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """
    Use LLM (LLM_PROVIDER / ANTHROPIC_API_KEY) to suggest URLs for skills that don't have one.
    """
    try:
        _llm_provider()
    except RuntimeError:
        return skills

    skills_needing_url = [name for name, data in skills.items() if not data.get("url")]
    if not skills_needing_url:
        return skills

    system_prompt = "Output valid JSON only, no markdown or explanation."
    user_prompt = f"""For each of these skills/technologies, suggest the official or canonical URL (e.g., Python -> https://python.org).
Output valid JSON only:
{{ "suggestions": [ {{ "name": "SkillName", "url": "https://..." }} ] }}

Skills: {json.dumps(skills_needing_url)}
"""

    try:
        text = _call_llm(system_prompt, user_prompt, max_tokens=4096)
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


def categorize_skills_with_llm(skills: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Use LLM to assign each skill a list of categories (e.g. Programming Language, Framework, Cloud).
    Adds "categories": [...] to each skill; uses [] if LLM unavailable or on failure.
    """
    for data in skills.values():
        data.setdefault("categories", [])

    try:
        _llm_provider()
    except RuntimeError:
        return skills

    if not skills:
        return skills

    names = list(skills.keys())
    system_prompt = "Output valid JSON only, no markdown or explanation."
    user_prompt = f"""Assign each of these skills/technologies to one or more categories. Use short, consistent category names (e.g. "Programming Language", "Framework", "Cloud", "Database", "Tool", "Library", "Methodology", "Data Science", "DevOps", "Frontend", "Backend").
Output valid JSON only:
{{ "categories": {{ "SkillName": ["Category1", "Category2"], ... }} }}

Each key must be exactly one of the skill names below. Use an empty array [] if a skill doesn't fit any category.
Skills: {json.dumps(names)}
"""

    try:
        text = _call_llm(system_prompt, user_prompt, max_tokens=4096)
        if "```" in text:
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = re.sub(r"```\s*$", "", text)
        data = json.loads(text.strip())
        cat_map = data.get("categories") or data
        if not isinstance(cat_map, dict):
            return skills
        for name in skills:
            raw = cat_map.get(name)
            if isinstance(raw, list):
                skills[name]["categories"] = [str(c).strip() for c in raw if str(c).strip()]
            else:
                skills[name]["categories"] = []
    except Exception:
        for data in skills.values():
            data["categories"] = data.get("categories") or []

    return skills


def _slugify(s: str) -> str:
    """Stable slug for category ID: lowercase, alphanumeric and single hyphens."""
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().strip()).strip("-")
    return s or "other"


def build_categories_dict(skills: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    """
    Build a categories dict with unique categoryIDs from skills' category names.
    Mutates each skill: adds "categoryIDs": [id, ...] and removes "categories" (names live only in categories dict).
    Returns categories = { categoryID: { "name": "Display Name" } }.
    """
    name_to_id: dict[str, str] = {}
    categories: dict[str, dict[str, str]] = {}
    for data in skills.values():
        for name in (data.get("categories") or []):
            name = str(name).strip()
            if not name:
                continue
            cid = name_to_id.get(name)
            if cid is None:
                cid = _slugify(name)
                if cid in categories:
                    base, n = cid, 1
                    while cid in categories:
                        cid = f"{base}-{n}"
                        n += 1
                name_to_id[name] = cid
                categories[cid] = {"name": name}
    for data in skills.values():
        names = data.get("categories") or []
        data["categoryIDs"] = [name_to_id[n] for n in names if n in name_to_id]
        data.pop("categories", None)
    return categories


def assign_skill_ids(skills: dict[str, dict[str, Any]]) -> None:
    """
    Assign a unique "id" (slug) to each skill in place.
    Enables jobs to reference skills via skillIDs; IDs are URL-safe and stable.
    """
    used: set[str] = set()
    for name, data in skills.items():
        base = _slugify(name) or "skill"
        sid = base
        n = 1
        while sid in used:
            sid = f"{base}-{n}"
            n += 1
        used.add(sid)
        data["id"] = sid
    return


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
        "#0069ac": "darkcyan",
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
    return mapping.get(hex_str.lower(), "darkgreen")


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
