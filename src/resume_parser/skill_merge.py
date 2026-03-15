#!/usr/bin/env python3
"""
Skill merge: LLM suggests duplicate/similar skills to merge; human approves before applying.
"""

import json
import re
from typing import Any

# Import LLM helpers from parsers
from .parsers import get_llm_provider


def _slugify(s: str) -> str:
    """Stable slug for skill ID."""
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower().strip()).strip("-")
    return s or "skill"


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
    """Call LLM via parsers module."""
    from .parsers import _call_llm as _call
    return _call(system_prompt, user_prompt, max_tokens=max_tokens)


def suggest_skill_merges(skills: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Ask LLM to suggest skill merges (duplicates, case variants, aliases).
    Returns list of {"sources": [skillID, ...], "target": skillID, "target_name": str}.
    On LLM failure or when no provider, returns [].
    """
    get_llm_provider()  # raise if API key not set

    if len(skills) < 2:
        return []

    names = list(skills.keys())
    system_prompt = "Output valid JSON only, no markdown or explanation."
    user_prompt = f"""These skills were extracted from a resume. Suggest merges for duplicates, case variants, or known aliases.

Output valid JSON only:
{{ "suggestions": [ {{ "sources": ["SkillA", "SkillB"], "target": "CanonicalName" }}, ... ] }}

Rules:
- sources: array of skill names to merge (each must appear exactly in the Skills list below).
- target: the canonical name to keep (one of the source names or a standard alias, e.g. "JavaScript" not "JS").
- Merge when two or more entries are the same thing: case variants (Scikit-Learn / Scikit-learn), spacing (K-means / K-means Clustering), or common aliases (JS / JavaScript, AWS / Amazon Web Services).
- Only suggest merges where skills have the same or very similar meaning. Do NOT merge unrelated skills.
- If you see clear duplicates or aliases in the list, suggest them. Leave suggestions empty [] only if there are no such pairs.

Example (if the list contained "Scikit-Learn", "Scikit-learn", "Python"):
{{ "suggestions": [ {{ "sources": ["Scikit-Learn", "Scikit-learn"], "target": "Scikit-Learn" }} ] }}

Skills: {json.dumps(names)}
"""

    text = None
    try:
        text = _call_llm(system_prompt, user_prompt)
        if "```" in text:
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = re.sub(r"```\s*$", "", text)
        data = json.loads(text.strip())
        raw = data.get("suggestions") or []
        if not isinstance(raw, list):
            return []
    except Exception as e:
        import sys
        print(f"[skill_merge] LLM response (first 500 chars): {repr(text[:500]) if text else '(no response)'}", file=sys.stderr)
        print(f"[skill_merge] Parse error: {e}", file=sys.stderr)
        return []

    id_to_name = {d["id"]: n for n, d in skills.items() if d.get("id")}
    name_to_id = {n: d["id"] for n, d in skills.items() if d.get("id")}

    result: list[dict[str, Any]] = []
    dropped: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sources_raw = item.get("sources") or []
        target_name = (item.get("target") or "").strip()
        if not target_name or not sources_raw:
            continue
        sources_raw = [str(s).strip() for s in sources_raw if str(s).strip()]
        if not sources_raw:
            continue
        # Resolve to skill IDs; skip any not in skills
        source_ids = []
        for s in sources_raw:
            if s in name_to_id:
                source_ids.append(name_to_id[s])
            elif s in id_to_name:
                source_ids.append(s)
        if not source_ids:
            dropped.append(f"sources {sources_raw} not found in skill names")
            continue
        # Target: use existing id if name exists, else create new id
        used_ids = {d["id"] for d in skills.values()}
        if target_name in name_to_id:
            target_id = name_to_id[target_name]
        else:
            base = _slugify(target_name) or "skill"
            target_id = base
            n = 1
            while target_id in used_ids:
                target_id = f"{base}-{n}"
                n += 1
        # Dedupe source_ids, exclude target if it's in sources
        source_ids = list(dict.fromkeys(source_ids))
        if target_id in source_ids:
            source_ids = [s for s in source_ids if s != target_id]
        if not source_ids:
            continue
        result.append({
            "sources": source_ids,
            "target": target_id,
            "target_name": target_name,
        })
    if not result and dropped:
        import sys
        print(f"[skill_merge] LLM returned {len(raw)} suggestion(s) but all were dropped: {dropped[:5]}{'...' if len(dropped) > 5 else ''}", file=sys.stderr)
    return result


def apply_skill_merge(
    skills: dict[str, dict[str, Any]],
    jobs: list[dict[str, Any]],
    categories: dict[str, dict[str, Any]],
    sources: list[str],
    target: str,
    target_name: str | None = None,
) -> tuple[list[str], str]:
    """
    Merge source skills into target. Mutates skills in place.
    Jobs and categories are not mutated; they derive skillIDs from skills later.
    - sources: list of skillIDs to merge from
    - target: skillID to merge into (created if not exists)
    - target_name: display name for target if creating new
    Returns (source_display_names_removed, target_display_name) for updating job descriptions.
    """
    id_to_name = {d["id"]: n for n, d in skills.items() if d.get("id")}

    # Resolve target skill
    target_entry = None
    target_key = None
    for name, data in skills.items():
        if data.get("id") == target:
            target_entry = data
            target_key = name
            break

    if target_entry is None:
        # Create new skill
        name = target_name or target
        if name in skills:
            target_entry = skills[name]
            target_key = name
        else:
            target_entry = {
                "id": target,
                "url": "",
                "img": "",
                "jobIDs": [],
                "categoryIDs": [],
            }
            skills[name] = target_entry
            target_key = name

    # Collect all jobIDs and categoryIDs from sources
    all_job_ids: set[int] = set(target_entry.get("jobIDs") or [])
    all_category_ids: set[str] = set(target_entry.get("categoryIDs") or [])
    url = target_entry.get("url") or ""
    img = target_entry.get("img") or ""

    source_keys_to_remove: list[str] = []
    for sid in sources:
        for name, data in skills.items():
            if data.get("id") == sid and name != target_key:
                all_job_ids.update(data.get("jobIDs") or [])
                all_category_ids.update(data.get("categoryIDs") or [])
                if data.get("url") and not url:
                    url = data["url"]
                if data.get("img") and not img:
                    img = data["img"]
                source_keys_to_remove.append(name)
                break

    target_entry["jobIDs"] = sorted(all_job_ids)
    target_entry["categoryIDs"] = sorted(all_category_ids)
    if url:
        target_entry["url"] = url
    if img:
        target_entry["img"] = img

    for key in source_keys_to_remove:
        skills.pop(key, None)
    return (source_keys_to_remove, target_key)


def run_merge_accept_all(
    skills: dict[str, dict[str, Any]],
    jobs: list[dict[str, Any]],
    categories: dict[str, dict[str, Any]],
) -> list[tuple[list[str], str]]:
    """
    Suggest merges and apply all of them without prompting.
    Mutates skills in place.
    Returns list of (source_display_names, target_display_name) for each applied merge.
    """
    suggestions = suggest_skill_merges(skills)
    if not suggestions:
        return []
    id_to_name = {d["id"]: n for n, d in skills.items() if d.get("id")}
    replacements: list[tuple[list[str], str]] = []
    for sug in suggestions:
        r = _do_apply(skills, jobs, categories, sug, id_to_name)
        if r:
            replacements.append(r)
        id_to_name = {d["id"]: n for n, d in skills.items() if d.get("id")}
    return replacements


def run_merge_interactive(
    skills: dict[str, dict[str, Any]],
    jobs: list[dict[str, Any]],
    categories: dict[str, dict[str, Any]],
) -> list[tuple[list[str], str]]:
    """
    Suggest merges, prompt user for each, apply approved ones.
    Mutates skills in place.
    Returns list of (source_display_names, target_display_name) for each applied merge.
    """
    suggestions = suggest_skill_merges(skills)
    if not suggestions:
        return []

    id_to_name = {d["id"]: n for n, d in skills.items() if d.get("id")}
    replacements: list[tuple[list[str], str]] = []
    accept_all = False
    for sug in suggestions:
        if accept_all:
            r = _do_apply(skills, jobs, categories, sug, id_to_name)
            if r:
                replacements.append(r)
            continue
        source_names = [id_to_name.get(sid, sid) for sid in sug["sources"]]
        target_name = sug.get("target_name") or id_to_name.get(sug["target"], sug["target"])
        label = " + ".join(f'"{n}"' for n in source_names) + " → " + f'"{target_name}"'
        try:
            ans = input(f'Merge {label}? [y/n/a/q]: ').strip().lower()
        except EOFError:
            break
        if ans == "q":
            break
        if ans == "a":
            accept_all = True
            r = _do_apply(skills, jobs, categories, sug, id_to_name)
            if r:
                replacements.append(r)
            continue
        if ans == "y":
            r = _do_apply(skills, jobs, categories, sug, id_to_name)
            if r:
                replacements.append(r)
            id_to_name = {d["id"]: n for n, d in skills.items() if d.get("id")}
    return replacements


def _do_apply(
    skills: dict[str, dict[str, Any]],
    jobs: list[dict[str, Any]],
    categories: dict[str, dict[str, Any]],
    sug: dict,
    id_to_name: dict[str, str],
) -> tuple[list[str], str] | None:
    return apply_skill_merge(
        skills,
        jobs,
        categories,
        sug["sources"],
        sug["target"],
        target_name=sug.get("target_name"),
    )
