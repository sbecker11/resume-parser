# Skill Merge & HTML Render Refactor: Implementation & Testing Plan

## Overview

1. Add skill merging (LLM suggests, human approves) before writing .mjs
2. Make .mjs writes lightweight serialization only
3. Extract HTML generation into a separate script that reads .mjs files

---

## Phase 1: Refactor HTML generation to read .mjs ✅

### 1.1 Create `render_resume_html.py` ✅

- **Input:** `-i` / `--input-dir` (folder containing jobs.mjs, skills.mjs, categories.mjs, other-sections.mjs)
- **Output:** Writes `resume.html` and `resume_template.html` to that folder
- **Logic:**
  - Load .mjs files (parse as JS or convert to JSON: strip `const X = ` prefix and `;` suffix, then `json.loads`)
  - Build `skills_by_category` from categories + skills
  - Build `description_bullets` per job from `Description`
  - Apply linkify filter
  - Render Jinja2 template, write HTML
  - Copy template to `resume_template.html`
- **Dependencies:** Jinja2, markupsafe; no resume parsing

### 1.2 Remove HTML render from `resume_to_flock.py` ✅

- Removed `_render_resume_html`, `_linkify`, `_template_dir`; HTML generation moved to `render_resume_html.py`
- Added optional `--render` flag to call render script after .mjs writes

### 1.3 Update CLI / docs ✅

- README: documented `python render_resume_html.py -i outputs-2` and `--render`
- Optionally: `resume_to_flock.py` can invoke `render_resume_html.py` after writing if desired

---

## Phase 2: Skill merge (LLM suggest + human approve) ✅

### 2.1 Add `suggest_skill_merges(skills: dict) -> list[dict]` in skill_merge.py ✅

- **Input:** skills dict (name-keyed in-memory format)
- **LLM prompt:** Given skill names, output JSON: `{"suggestions": [{"sources": ["python", "Python"], "target": "Python"}, ...]}`
- **Rules:** Only suggest merges where sources have similar meaning (duplicates, case variants, known aliases). Do not merge unrelated skills.
- **Output:** List of `{"sources": [skillIDs], "target": skillID}` (resolve names to IDs)
- **Error handling:** On LLM failure, return []

### 2.2 Add `apply_skill_merge` in skill_merge.py ✅

- **Input:** in-memory skills (name-keyed), flock_jobs, categories, source skill IDs/names, target skill ID/name
- **Logic:**
  - Resolve sources and target to skillIDs (target may be new)
  - Merge jobIDs, categoryIDs, url, img from sources into target
  - Remove source skills from skills dict
  - Update each job's skillIDs: replace sources with target, dedupe
  - Update each category's skillIDs: replace sources with target, dedupe
- **Output:** Mutates skills, jobs, categories; returns None

### 2.3 Add interactive approval loop in `resume_to_flock.py` ✅

- After `assign_skill_ids`, before building `skills_by_id`; `run_merge_interactive` in skill_merge.py:
  - Call `suggest_skill_merges(skills)`
  - For each suggestion (or batch):
    - Print: `Merge "X" + "Y" → "Z"? [y/n/a/q]: `
    - `y` = apply this merge, `n` = skip, `a` = accept all remaining, `q` = quit (no more merges)
  - Apply approved merges with `apply_skill_merge`
  - Re-run `assign_skill_ids` after merges? Or handle ID stability: target keeps its id, sources removed. No re-assign needed if we only remove sources.
- **Flag:** `--no-merge` to skip merge step (for non-interactive use)

### 2.4 Merge module layout ✅

- Implemented in `skill_merge.py` with `suggest_skill_merges`, `apply_skill_merge`, `run_merge_interactive`

---

## Phase 3: Ensure .mjs writes are lightweight

### 3.1 Current state

- Writes are already simple: `json.dumps` + write to file
- No change needed if merge happens in-memory before the write step

### 3.2 Pipeline order in main()

1. Extract, parse jobs, parse sections
2. Build flock_jobs, skills (name-keyed), categories
3. assign_skill_ids(skills)
4. **Skill merge** (suggest → approve → apply)
5. Build jobs_by_id, skills_by_id (id-keyed for output)
6. Add skillIDs to categories
7. **Write .mjs** (jobs, skills, categories, other-sections)
8. Copy original resume
9. **(Optional)** Run render_resume_html.py or document as separate step

---

## Testing Plan

### Unit tests

| Test | Module | Description |
|------|--------|-------------|
| `suggest_skill_merges` returns list, handles empty | parsers/skill_merge | Mock LLM; assert structure |
| `suggest_skill_merges` on LLM failure returns [] | skill_merge | Mock LLM exception |
| `apply_skill_merge` merges jobIDs, categoryIDs | skill_merge | Given skills, jobs, categories; apply merge; assert jobs and categories updated |
| `apply_skill_merge` removes sources from skills | skill_merge | Assert source keys gone, target has merged data |
| `apply_skill_merge` with new target creates skill | skill_merge | Target not in skills; assert new skill added |
| Render script loads .mjs and writes HTML | render_resume_html | Temp dir with sample .mjs; run script; assert resume.html exists, contains expected content |
| Render script linkify works | render_resume_html | other-sections or job desc with URL; assert `<a href` in output |

### Integration tests

| Test | Description |
|------|-------------|
| Full pipeline with `--no-merge` | Parse resume → write .mjs; no prompts; assert all files exist |
| Full pipeline with merge (mock stdin) | Patch input() to return "n" for all; assert no merges applied, .mjs written |
| Render after pipeline | Run pipeline with --no-merge, then render script; assert resume.html matches data |

### Manual tests

- Run pipeline with real resume; at merge prompt, approve one merge; verify skills.mjs, jobs.mjs, categories.mjs reflect merge
- Run render_resume_html.py on existing output dir; verify HTML regenerates correctly
- Run pipeline with `--no-merge` in CI / non-interactive context

---

## File structure (after implementation)

```
resume-parser/
├── resume_to_flock.py      # Parse + merge + write .mjs (no HTML)
├── render_resume_html.py   # Read .mjs → write resume.html (new)
├── skill_merge.py          # suggest_skill_merges, apply_skill_merge (new)
├── parsers.py
├── extractors.py
├── templates/
│   └── resume.html
├── tests/
│   ├── test_skill_merge.py
│   ├── test_render_resume_html.py
│   └── ...
└── docs/
    └── IMPLEMENTATION_PLAN.md
```

---

## Implementation order

1. **Phase 1** – Extract HTML render to `render_resume_html.py`; remove from main pipeline; test.
2. **Phase 2** – Add `skill_merge.py`; integrate merge step in `resume_to_flock.py`; add `--no-merge`.
3. **Phase 3** – Confirm .mjs writes stay lightweight (no code change if order is correct).
4. **Tests** – Add unit and integration tests as each phase is completed.
