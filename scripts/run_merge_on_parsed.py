#!/usr/bin/env python3
"""
Run the skill-merge step on an existing parsed resume folder (JSON format).

Loads jobs.json, skills.json, categories.json from the folder, converts to the
format expected by run_merge_interactive, runs the merge (interactive prompts),
then writes back updated skills.json and categories.json, recomputes job
skillIDs, and optionally re-renders resume.html.

Usage:
  run-merge-on-parsed <path-to-parsed-folder> [--render]
  run-merge-on-parsed parsed_resumes --all [--render]
  # Or from repo: python scripts/run_merge_on_parsed.py ...

  --all         Run merge for each subfolder of the given directory.
  --accept-all  Apply all LLM-suggested merges without prompting (batch mode).
  --render  (or --render-after-merging)  Re-run render-resume-html after merging.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Project root for imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env so ANTHROPIC_API_KEY is available for skill merge LLM calls
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def _require_llm_api_key() -> None:
    """Fail fast if ANTHROPIC_API_KEY is not set or empty."""
    import os
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        print("Error: ANTHROPIC_API_KEY is not set or is empty. Set it in .env or the environment.", file=sys.stderr)
        sys.exit(1)


from skill_merge import run_merge_interactive, run_merge_accept_all


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def skills_file_to_merge_format(skills_by_id: dict) -> dict:
    """Convert id-keyed skills (file format) to name-keyed (merge format)."""
    seen_names: set[str] = set()
    skills_by_name: dict = {}

    for sid, data in skills_by_id.items():
        name = (data.get("name") or sid).strip()
        if name in seen_names:
            name = f"{name} ({sid})"
        else:
            seen_names.add(name)
        skills_by_name[name] = {
            "id": sid,
            "url": data.get("url", ""),
            "img": data.get("img", ""),
            "jobIDs": list(data.get("jobIDs", [])),
            "categoryIDs": list(data.get("categoryIDs", [])),
        }
    return skills_by_name


def skills_merge_to_file_format(skills_by_name: dict) -> dict:
    """Convert name-keyed skills (after merge) back to id-keyed file format."""
    return {
        data["id"]: {
            "name": name.split(" (")[0] if " (" in name else name,
            "url": data.get("url", ""),
            "img": data.get("img", ""),
            "categoryIDs": list(data.get("categoryIDs", [])),
            "jobIDs": list(data.get("jobIDs", [])),
        }
        for name, data in skills_by_name.items()
    }


def jobs_dict_to_list(jobs_dict: dict) -> list:
    """Convert jobs.json dict (key "0","1",...) to list ordered by index."""
    keys = sorted(jobs_dict.keys(), key=lambda x: int(x) if str(x).isdigit() else x)
    return [jobs_dict[k] for k in keys]


def run_merge_in_dir(dir_path: Path, render: bool, accept_all: bool = False) -> bool:
    """Run skill merge in one parsed folder. Returns True on success."""
    jobs_path = dir_path / "jobs.json"
    skills_path = dir_path / "skills.json"
    categories_path = dir_path / "categories.json"

    for p in (jobs_path, skills_path, categories_path):
        if not p.exists():
            print(f"Skip {dir_path.name}: missing {p.name}", file=sys.stderr)
            return False

    jobs_dict = _load_json(jobs_path)
    skills_by_id = _load_json(skills_path)
    categories = _load_json(categories_path)

    jobs_list = jobs_dict_to_list(jobs_dict)
    skills_by_name = skills_file_to_merge_format(skills_by_id)

    if len(skills_by_name) < 2:
        print(f"{dir_path.name}: only {len(skills_by_name)} skill(s), nothing to merge.")
        return True

    original_skill_count = len(skills_by_name)
    print(f"\n--- {dir_path.name} ({original_skill_count} skills) ---")
    if accept_all:
        replacements = run_merge_accept_all(skills_by_name, jobs_list, categories)
    else:
        replacements = run_merge_interactive(skills_by_name, jobs_list, categories)

    # Additional pass: replace all merged terms in job descriptions.
    # Convention: skills in job descriptions are wrapped in [SkillName] brackets.
    # We:
    #  1) replace already-bracketed occurrences: [source] -> [target]
    #  2) bracketify unbracketed occurrences: source (not inside [...]) -> [target]
    #
    # Compute transitive final mapping so chained merges are correct.
    if replacements:
        immediate_map: dict[str, str] = {}
        for source_names, target_name in replacements:
            for sn in source_names:
                immediate_map[sn] = target_name

        def _resolve_final(term: str) -> str:
            seen: set[str] = set()
            cur = term
            while cur in immediate_map and cur not in seen:
                seen.add(cur)
                cur = immediate_map[cur]
            return cur

        final_map = {src: _resolve_final(src) for src in immediate_map.keys()}
        sources_sorted = sorted(final_map.keys(), key=len, reverse=True)

        def _replace_in_desc(desc: str) -> str:
            out = desc or ""
            for src in sources_sorted:
                tgt = final_map[src]
                out = re.sub(r"\[" + re.escape(src) + r"\]", f"[{tgt}]", out)
                out = re.sub(r"(?<!\[)" + re.escape(src) + r"(?!\])", f"[{tgt}]", out)
            return out

        for job in jobs_list:
            job["Description"] = _replace_in_desc(job.get("Description") or "")

    # Recompute category skillIDs and job skillIDs from merged skills
    for cat_id, cat in categories.items():
        cat["skillIDs"] = [
            data["id"]
            for name, data in skills_by_name.items()
            if cat_id in data.get("categoryIDs", [])
        ]
    for job in jobs_list:
        idx = job.get("index")
        job["skillIDs"] = [
            data["id"]
            for name, data in skills_by_name.items()
            if idx in data.get("jobIDs", [])
        ]

    new_skill_count = len(skills_by_name)
    skills_by_id_new = skills_merge_to_file_format(skills_by_name)
    _write_json(skills_path, skills_by_id_new)
    _write_json(categories_path, categories)
    _write_json(jobs_path, {str(job["index"]): job for job in jobs_list})
    print(f"Wrote {skills_path}, {categories_path}, {jobs_path}")
    print(f"Skills: {original_skill_count} → {new_skill_count}")

    if render:
        from render_resume_html import render_resume_html
        render_resume_html(dir_path)
        print(f"Rendered {dir_path / 'resume.html'}")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run skill merge on parsed JSON resume folder(s)")
    parser.add_argument("path", type=Path, help="Path to one parsed folder or to parsed_resumes")
    parser.add_argument("--all", action="store_true", help="Run merge for each subfolder")
    parser.add_argument("--accept-all", action="store_true", help="Apply all suggested merges without prompting")
    parser.add_argument("--render", "--render-after-merging", dest="render", action="store_true", help="Re-render resume.html after merge")
    args = parser.parse_args()

    _require_llm_api_key()

    path = args.path.resolve()
    if not path.exists():
        print(f"Error: {path} does not exist", file=sys.stderr)
        return 1

    if args.all:
        if not path.is_dir():
            print("Error: --all requires a directory", file=sys.stderr)
            return 1
        dirs = sorted(d for d in path.iterdir() if d.is_dir())
        if not dirs:
            print(f"No subfolders in {path}", file=sys.stderr)
            return 1
        for d in dirs:
            run_merge_in_dir(d, args.render, args.accept_all)
    else:
        if not (path / "skills.json").exists():
            print(f"Error: {path} does not look like a parsed folder (no skills.json)", file=sys.stderr)
            return 1
        run_merge_in_dir(path, args.render, args.accept_all)

    return 0


if __name__ == "__main__":
    sys.exit(main())
