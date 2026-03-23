#!/usr/bin/env python3
"""
resume-from-json: Load parsed resume JSON into memory, then render HTML.

Usage:
  resume-from-json -i /path/to/output-folder
  # Or from repo: python resume_from_json.py -i ...
"""

import argparse
import json
import sys
from pathlib import Path

from src.resume_parser.render_resume_html import load_resume_from_json, render_resume_model


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load parsed resume JSON into memory, then render resume.html"
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing jobs.json, skills.json, categories.json, other-sections.json",
    )
    parser.add_argument(
        "--show-brackets",
        dest="show_square_brackets",
        action="store_true",
        help="Keep square brackets in rendered text (default: strip them).",
    )
    args = parser.parse_args()

    try:
        model = load_resume_from_json(args.input_dir)
        resume_path, template_path = render_resume_model(
            model,
            output_dir=args.input_dir,
            skip_square_brackets=not args.show_square_brackets,
        )
        print(f"Wrote {resume_path}")
        print(f"Wrote {template_path}")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
