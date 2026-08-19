# Test coverage

## What the gate enforces

Every source file in `src/resume_parser/` must hit **at least 80% line
coverage individually**, not just in aggregate. This is enforced two ways:

- **`.coveragerc`** sets `fail_under = 80` under `[report]` — an aggregate
  floor across the whole `src/resume_parser/` tree. This alone would let one
  very well-tested file mask another that's badly under-tested, since only
  the overall percentage is checked.
- **`scripts/check_coverage_per_file.py`** closes that gap: it reads
  `coverage json`'s per-file breakdown and fails if *any* file is below the
  threshold (80% by default), mirroring the sibling `resume-flyer` project's
  vitest `coverage.thresholds.perFile: true` semantics for the same reason —
  coverage.py's own `fail_under` is aggregate-only, so a dedicated script is
  the only way to get equivalent per-file rigor in Python.

## Running it locally

```bash
# from the repo root, with the venv activated
coverage run --source=src/resume_parser -m pytest tests/ -q

# per-file gate (fails with a list of any file under 80%)
python scripts/check_coverage_per_file.py

# optional: full aggregate report with missing line numbers
coverage report -m --include="src/*"
```

`--source=src/resume_parser` matters: without it, `coverage` only tracks
files that were actually imported during the test run, which can hide a
file that's never imported anywhere (and therefore sitting at an invisible
0%). With `--source`, every file under `src/resume_parser/` is measured,
imported or not.

`check_coverage_per_file.py` writes `coverage.json` (via `coverage json -o`)
as a side effect — that file is gitignored, no need to clean it up manually.

## How CI enforces it

`.github/workflows/ci.yml`, job `test`, runs three steps in order:

1. **"Run tests with coverage"** — `coverage run --source=src/resume_parser -m pytest tests/ -q`
2. **"Enforce 80% coverage (per file)"** — `python scripts/check_coverage_per_file.py`, which fails the build (non-zero exit) and prints every offending file + its percentage if any file is under 80%.
3. **"Coverage summary"** (`if: always()`) — `coverage report -m --include="src/*"`, so the full per-file breakdown with missing line numbers is always visible in the CI log, even when step 2 fails.

CI does not need `.env` decrypted (see `docs/SECRETS.md`) — tests patch
`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` via `unittest.mock`, and
`env_loader.load_dotenv_safely()` degrades gracefully (logs a warning,
doesn't raise) if `.env` on disk is still the git-crypt-encrypted blob.

## Excluding a file that can't reasonably reach 80%

`check_coverage_per_file.py` has an `EXCLUDE` set at the top of the script
for exactly this case:

```python
EXCLUDE = {
    # (none yet)
}
```

To exclude a file, add its path as it appears in `coverage json`'s `files`
key (repo-relative, e.g. `"src/resume_parser/some_module.py"`) with a
one-line comment explaining why — same pattern resume-flyer uses in
`vitest.config.js`'s `coverage.exclude` array. Note this only bypasses the
*per-file* script check; the file's lines still count toward `.coveragerc`'s
aggregate `fail_under = 80`, so an excluded file still needs to not drag the
overall project average down too far. Prefer writing tests (including
smoke-testing thin CLI wrappers with mocks, as `test_resume_from_json.py`
and `test_reparse_education_only.py` do) over adding to this list.
