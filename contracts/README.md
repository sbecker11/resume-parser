# Contracts

Specifications owned and maintained by resume-parser. External consumers (e.g. resume-flock) implement against these documents.

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

When you publish a new version, add a new file (e.g. `RENDER_RESUME_HTML-v1.1.md`) and leave existing versions in place. Update repo references (README, script docstrings, etc.) to point to the version that current code implements. Consumers can pin to a specific file (e.g. `contracts/RENDER_RESUME_HTML-v1.0.md`).

## Revision control within each contract

Each versioned file also includes:

- **Version** — Same as the version in the filename (e.g. `1.0`). Bump when you change the contract:
  - **Major** — Breaking change; consumers must update to remain compatible.
  - **Minor** — Additive or clarifying change; existing consumers remain valid.
- **Revision history** — Table at the end of the document: version, date, and short description of the change.

When you add a new versioned file (e.g. v1.1), copy from the previous version, apply changes, add a row to the revision history, and update the **Version** line at the top.
