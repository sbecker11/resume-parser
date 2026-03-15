# Parsed Resume Object — File/Directory Format

A **parsed resume** is a directory under `parsed_resumes/<id>/` containing the original resume file (optional), parser output files, and metadata. The app loads jobs/skills from these directories via `GET /api/resumes/:id/data`.

## Resume-parser output format (current)

The resume-parser writes a **flattened** output folder (no subfolders). All files sit in the output directory. The output folder also contains a **copy of the original resume file** (DOCX or PDF) under its **original filename**.

**Data model (consistent across the three dicts):**

- **Skills** dictionary uses **skillID** as primary key. Each skill item has: display name (`name`), optional list of `categoryIDs`, optional list of `jobIDs`. May also include `url`, `img`.
- **Jobs** dictionary uses **jobID** as primary key. Each job item has: display name (role, employer, etc.), optional list of `skillIDs`.
- **Categories** dictionary uses **categoryID** as primary key. Each category item has: display name (`name`), optional list of `skillIDs`.

Files written: `jobs.mjs`, `skills.mjs`, `categories.mjs`, `other-sections.mjs`, `resume.html`, `resume_template.html`, plus the original `resume.docx` (or PDF) under its original filename.

## Directory layout (flat)

All parser files at folder root. No subfolders.

```
parsed_resumes/
  <id>/
    jobs.mjs               # required — parser output (export const jobs = {...}; keyed by jobID)
    skills.mjs             # optional — parser output (export const skills = {...}; keyed by skillID); if missing, skills = {}
    categories.mjs         # optional — parser output (export const categories = {...}; keyed by categoryID)
    other-sections.mjs     # optional — export const otherSections = { ... }
    meta.json              # optional for load; required for list UI
    resume.docx            # optional — original uploaded document (parser copies here under original filename)
    resume.pdf             # optional — original uploaded document (one of resume.*)
```

- **`<id>`**: Opaque identifier. Use lowercase alphanumeric and hyphens (e.g. `parsed-resume-1`). Must not be `default` (reserved for static content).
- **Jobs**: `jobs.mjs` at folder root. Parser format: dict keyed by jobID; each job has display fields and optional `skillIDs` array. Parsed by `parseMjsExport(content, 'jobs')`.
- **Skills**: Optional. `skills.mjs` at folder root. Parser format: dict keyed by skillID; each skill has `name`, optional `categoryIDs`, optional `jobIDs`. If missing, the server returns `skills: {}`.
- **Categories**: Optional. `categories.mjs` at folder root. Parser format: dict keyed by categoryID; each category has `name`, optional `skillIDs`.
- **other-sections.mjs**: Optional. See "other-sections.mjs schema" below.
- **Original doc**: Parser writes a copy of the input resume (DOCX/PDF) into the output folder under its original filename.

## meta.json schema

```json
{
  "id": "<same as directory name>",
  "displayName": "Human-readable label",
  "createdAt": "ISO 8601 date string",
  "fileName": "resume.docx",
  "jobCount": 11,
  "skillCount": 85
}
```

| Field         | Type   | Required | Description |
|---------------|--------|----------|-------------|
| `id`          | string | yes      | Same as parent directory name. |
| `displayName` | string | yes      | Label for UI (e.g. "Default resume", "Shawn Becker 2025"). |
| `createdAt`   | string | yes      | ISO 8601 (e.g. `2025-03-07T12:00:00.000Z`). |
| `fileName`    | string | no       | Original file name if uploaded (e.g. `resume.docx`). Omit if no file. |
| `jobCount`    | number | yes      | Number of jobs: length of `jobs` array if array, or `Object.keys(jobs).length` if dict keyed by jobID. |
| `skillCount`  | number | yes      | Number of keys in `skills` object in `skills.mjs`. |

## Validation rules

- Jobs file must parse to an array or object. If object, keys are jobIDs; each job has display fields (role, employer, start, end, Description, etc.) and optional `skillIDs`. Legacy format: array with at least `index`, `role`, `employer`, `start`, `end`, `Description`.
- If present, skills file must parse to an object keyed by skillID; each skill has display name (`name`) and optionally `url`, `img`, `categoryIDs`, `jobIDs`.
- If present, categories file is an object keyed by categoryID; each category has `name` and optional `skillIDs`.
- Server returns 404 only if the resume folder or jobs file is missing for a given `id`. `meta.json`, `skills`, and `categories` are optional.

## other-sections.mjs schema

The parser should write `other-sections.mjs` with `export const otherSections = { ... }`. The object may include:

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | Professional summary |
| `title` | string | Job title or headline |
| `contact` | object | `{ name?, email?, phone?, location?, linkedin?, website? }` |
| `certifications` | array | Each: `{ name, url?, description? }` |
| `websites` | array | Each: `{ label, url, description? }` |
| `custom_sections` | array | User-defined sections, e.g. Education, Awards. Each: `{ title, subtitle?, description? }` or `{ title, content? }` |

### Websites: one entry per line

For a resume section containing labeled links (e.g. `Label: URL` lines) such as:

```
Certifications: https://www.linkedin.com/in/shawnbecker/details/certifications/
Publications: https://independent.academia.edu/shawnbecker
Patents: https://patents.justia.com/inventor/shawn-c-becker
LinkedIn: https://www.linkedin.com/in/shawnbecker
GitHub: https://github.com/sbecker11
Portfolio: https://sbecker11.github.io/flock-of-postcards
```

the parser should emit **each line as its own entry** in the `websites` array:

```js
export const otherSections = {
  websites: [
    { label: "Certifications", url: "https://www.linkedin.com/in/shawnbecker/details/certifications/" },
    { label: "Publications", url: "https://independent.academia.edu/shawnbecker" },
    { label: "Patents", url: "https://patents.justia.com/inventor/shawn-c-becker" },
    { label: "LinkedIn", url: "https://www.linkedin.com/in/shawnbecker" },
    { label: "GitHub", url: "https://github.com/sbecker11" },
    { label: "Portfolio", url: "https://sbecker11.github.io/flock-of-postcards" }
  ]
  // ... other fields
};
```

Each item has `label` (the text before the colon) and `url`. Optional `description` may be used for extra text. The resume-details-editor displays one row per website entry.

## Using a parsed resume from another directory

The app reads only from **resume-flock’s** `parsed_resumes/` directory (project root). To use a folder you created elsewhere (e.g. `~/workspace-resume/parsed-resumes/parsed-resume-1/`):

1. **Copy or symlink** that folder into resume-flock’s `parsed_resumes/` under the same id:
   - From repo root:  
     `cp -r ~/workspace-resume/parsed-resumes/parsed-resume-1 ./parsed_resumes/parsed-resume-1`  
   - or:  
     `ln -s ~/workspace-resume/parsed-resumes/parsed-resume-1 ./parsed_resumes/parsed-resume-1`
2. Your layout is supported: **jobs at root** (`jobs.mjs`) and **no skills file** (server uses `skills: {}`). Original doc name (e.g. `data-engineer.docx`) is fine.
3. In the app, set `currentResumeId` to `parsed-resume-1` and call the reinitializer (or use a future “Load resume” UI).

## Relationship to “default” resume

- **Default resume**: Jobs/skills come from `static_content/jobs/jobs.mjs` and `static_content/skills/skills.mjs` (API path `/api/resumes/default/data`). No directory under `parsed_resumes/` is required.
- **Parsed resume**: Jobs/skills come from `parsed_resumes/<id>/jobs.mjs` and `parsed_resumes/<id>/skills.mjs` (API path `/api/resumes/:id/data`). App state `currentResumeId` holds `id` or `null` for default.

## Reinitializing the app with a parsed resume

After setting `currentResumeId` in app state and persisting, call the single reinit path so Timeline, CardsController, and the resume list rebuild from the new jobs:

```js
import { reinitializeResumeSystem } from '@/modules/resume/resumeReinitializer.mjs'

// e.g. after user selects a resume or after parse
await reinitializeResumeSystem(resumeId)  // resumeId string or null for default
```

See `modules/resume/resumeReinitializer.mjs` for registration of Timeline, CardsController, and resume-list callbacks.

---

## Latest work (implementation status)

### currentResumeId behavior

- **`currentResumeId: null`** — Loads the **default resume** from `static_content/jobs/jobs.mjs` and `static_content/skills/skills.mjs` (API: `/api/resumes/default/data`).
- **`currentResumeId: "<id>"`** — Loads the **parsed resume** from `parsed_resumes/<id>/` (API: `/api/resumes/:id/data`).

Set and persist in `app_state.json` under `user-settings.currentResumeId`; the app reads it on load and fetches the corresponding jobs/skills.

### Using a parsed resume (steps that work)

1. **Parser output** (e.g. from `resume_to_flock.py` in workspace-resume/resume-parser): writes a **flattened** output folder (no subfolders) with `jobs.mjs`, `skills.mjs`, `categories.mjs`, and a **copy of the original resume** (DOCX/PDF) under its original filename (e.g. `~/workspace-resume/parsed-resumes/parsed-resume-1/`).
2. **Symlink into resume-flock** (from resume-flock repo root):  
   `ln -s ~/workspace-resume/parsed-resumes/parsed-resume-1 ./parsed_resumes/parsed-resume-1`
3. **Set default resume in app state**: In `app_state.json`, set `user-settings.currentResumeId` to `"parsed-resume-1"` (or `null` for static default).
4. **Start app**: `npm run dev`. Jobs load from the API; Timeline, CardsController, and resume list reinitialize from the loaded jobs.

### Server behavior

- **Flat layout only**: `jobs.mjs`, `skills.mjs`, `categories.mjs`, `other-sections.mjs` at folder root. Missing skills file → `skills: {}`.
- **Reinit path**: Single path in `resumeReinitializer.mjs`: load jobs by id → Timeline reinit → CardsController reinit → resume list reinit.

### CardsController / jobs race fix

CardsController now initializes when **either** (1) `scene-plane-ready` fires **or** (2) jobs become available (watcher on jobs dependency). That avoids the case where the scene is ready before `loadJobs()` completes (e.g. parsed resume from API), which previously left biz-card-divs and skill-card-divs at zero.

---

## Invoking the parser (next objective)

To run the parse-resume pipeline from resume-flock given a `resume.docx` path:

- **Parser**: `resume_to_flock.py` (in a separate repo, e.g. `RESUME_PARSER_PATH` or `~/workspace-resume/resume-parser`).
- **Invocation**: `python resume_to_flock.py <path-to-resume.docx> -o <output-dir>`.
- **Output dir**: Typically `parsed_resumes/<id>/` (or an external path like `~/workspace-resume/parsed-resumes/parsed-resume-1`). The parser writes a flattened folder: `jobs.mjs`, `skills.mjs`, `categories.mjs`, and a copy of the input resume file (original filename).

**Script:** `scripts/run-parse-resume.mjs` (npm script `parse-resume`) invokes the parser subprocess.

```bash
# Local folder: input docx inside the output dir (from repo root)
npm run parse-resume -- --docx ./parsed_resumes/parsed-resume-0/data-engineer-0.docx --out ./parsed_resumes/parsed-resume-0

# Output to resume-flock’s parsed_resumes/<id> (then symlink or use as currentResumeId)
npm run parse-resume -- --docx /path/to/your/resume.docx --id parsed-resume-2

# Output to another repo (e.g. workspace-resume)
npm run parse-resume -- --docx /path/to/your/resume.docx --out ~/workspace-resume/parsed-resumes/parsed-resume-1
```

Set `RESUME_PARSER_PATH` if the parser repo is not at `../workspace-resume/resume-parser` relative to resume-flock. The script uses the parser’s `venv/bin/python` when present.

---

## External HTML renderer

The app can invoke an external script that reads resume data from the resume folder and produces HTML. Use the **Render** button to run it and view the result in a new tab.

**Configuration:** Set `RESUME_HTML_RENDERER_SCRIPT` to the path of your Node script (e.g. `./scripts/render-resume-html.mjs` or an absolute path).

**Invocation:** The server runs `node <scriptPath> <resumeFolderPath>`. The script receives the parsed resume folder path (e.g. `parsed_resumes/parsed-resume-1` resolved to an absolute path) as its first argument.

**Output:** The script must write the HTML to `<resumeFolderPath>/rendered.html`. The app then serves that file at `GET /api/resumes/:id/rendered`.

If `RESUME_HTML_RENDERER_SCRIPT` is not set, the Render button returns 501 with an explanatory message.
