# Contracts

**Single source of truth** for schema, validator, and contract specifications. Owned and maintained by resume-parser. External consumers implement against these documents.

Root-level CLIs (`resume-to-json`, `render-resume-html`, `run-merge-on-parsed`, `validate-parsed-resume`) are provided by the installed package, not stored in this folder.

## Access via GitHub

If this repo is hosted on GitHub, consumers can open contracts directly:

- **View (rendered Markdown):**  
  `https://github.com/OWNER/resume-parser/blob/BRANCH/contracts/FILENAME.md`  
  Example: `.../blob/main/contracts/RENDER_RESUME_HTML-v1.0.md`
- **Raw file:**  
  `https://github.com/OWNER/resume-parser/raw/BRANCH/contracts/FILENAME.md`  
  Use for downloads or tooling.
- **Pin to a revision (stable link):**  
  Replace `BRANCH` with a commit SHA, e.g. `.../blob/abc1234.../contracts/RENDER_RESUME_HTML-v1.0.md`  
  The file content at that commit will not change when the branch is updated.

Replace `OWNER` with the GitHub org or username and `BRANCH` with the default branch (e.g. `main`).

## Versioned filenames

Each contract is stored with its version in the filename so all versions remain available:

- **RENDER_RESUME_HTML-v1.0.md** — Standalone HTML generator (invocation, args, behavior)
- **PARSED-RESUME-FORMAT-v1.0.md** — Parsed resume directory and JSON format
- **PARSED-RESUME-JSON-FORMAT-v1.0.md** — Parsed resume JSON/directory spec
- **parsed-resume-format-v1.0.json** — JSON Schema for parsed output (jobs, skills, categories, otherSections, meta)

The **validator** lives in the installed package (no duplicate script in this folder). Run: `validate-parsed-resume <folder>` (CLI) or `python -m resume_parser.contracts.validate_parsed_resume <folder>`. Install with `pip install resume-parser` (or from Git). See root README.

When you publish a new version, add a new file (e.g. `RENDER_RESUME_HTML-v1.1.md`) and leave existing versions in place. Update repo references (README, script docstrings, etc.) to point to the version that current code implements. Consumers can pin to a specific file (e.g. `contracts/RENDER_RESUME_HTML-v1.0.md`).

## Revision control within each contract

Each versioned file also includes:

- **Version** — Same as the version in the filename (e.g. `1.0`). Bump when you change the contract:
  - **Major** — Breaking change; consumers must update to remain compatible.
  - **Minor** — Additive or clarifying change; existing consumers remain valid.
- **Revision history** — Table at the end of the document: version, date, and short description of the change.

When you add a new versioned file (e.g. v1.1), copy from the previous version, apply changes, add a row to the revision history, and update the **Version** line at the top.
