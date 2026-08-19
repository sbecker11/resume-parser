#!/usr/bin/env python3
"""
Enforce an 80% line-coverage floor per source file (not just in aggregate),
mirroring resume-flyer's vitest `thresholds: { perFile: true, lines: 80 }`.

Usage: run after `coverage run -m pytest ...`:
    python scripts/check_coverage_per_file.py [--threshold 80] [--json coverage.json]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 80.0

# Files intentionally exempt from the per-file floor. Keep this list short and
# documented — prefer fixing/testing a file over adding it here.
EXCLUDE = {
    # (none yet)
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--json", default=None, help="Path to write/read the coverage JSON report")
    args = parser.parse_args()

    json_path = Path(args.json) if args.json else Path("coverage.json")
    # Don't use check=True: `coverage json` still applies [report] fail_under and
    # exits non-zero on a global-floor miss even though it wrote the file we need;
    # this script does its own (stricter, per-file) check below.
    subprocess.run(["coverage", "json", "-o", str(json_path)], check=False)
    if not json_path.exists():
        print(f"ERROR: {json_path} was not written by `coverage json`", file=sys.stderr)
        return 1

    data = json.loads(json_path.read_text())
    failures = []
    for filename, file_data in data.get("files", {}).items():
        rel = filename
        if rel in EXCLUDE:
            continue
        pct = file_data["summary"]["percent_covered"]
        if pct < args.threshold:
            failures.append((rel, pct))

    if failures:
        print(f"ERROR: {len(failures)} file(s) below the {args.threshold:.0f}% per-file coverage floor:")
        for rel, pct in sorted(failures, key=lambda x: x[1]):
            print(f"  {pct:5.1f}%  {rel}")
        return 1

    total = data.get("totals", {}).get("percent_covered", 0)
    print(f"OK: all files meet the {args.threshold:.0f}% per-file coverage floor (overall {total:.1f}%).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
