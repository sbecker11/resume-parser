"""Tests for resume_parser.resume_from_json (thin CLI wrapper)."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from resume_parser.resume_from_json import main


class TestResumeFromJsonMain(unittest.TestCase):
    def _run_with_args(self, argv):
        with patch.object(sys, "argv", ["resume-from-json"] + argv):
            return main()

    def test_success_writes_resume_and_template(self):
        with patch(
            "resume_parser.resume_from_json.load_resume_from_json", return_value={"role": "x"}
        ) as mock_load, patch(
            "resume_parser.resume_from_json.render_resume_model",
            return_value=(Path("/tmp/resume.html"), Path("/tmp/template.html")),
        ) as mock_render:
            code = self._run_with_args(["-i", "/tmp/some-folder"])

        self.assertEqual(code, 0)
        mock_load.assert_called_once_with(Path("/tmp/some-folder"))
        mock_render.assert_called_once()
        _, kwargs = mock_render.call_args
        self.assertEqual(kwargs["output_dir"], Path("/tmp/some-folder"))
        self.assertTrue(kwargs["skip_square_brackets"])

    def test_show_brackets_flag_disables_stripping(self):
        with patch("resume_parser.resume_from_json.load_resume_from_json", return_value={}), patch(
            "resume_parser.resume_from_json.render_resume_model",
            return_value=(Path("/tmp/resume.html"), Path("/tmp/template.html")),
        ) as mock_render:
            code = self._run_with_args(["-i", "/tmp/some-folder", "--show-brackets"])

        self.assertEqual(code, 0)
        _, kwargs = mock_render.call_args
        self.assertFalse(kwargs["skip_square_brackets"])

    def test_missing_input_dir_returns_error_code(self):
        with patch(
            "resume_parser.resume_from_json.load_resume_from_json",
            side_effect=FileNotFoundError("no such folder"),
        ):
            code = self._run_with_args(["-i", "/tmp/does-not-exist"])
        self.assertEqual(code, 1)

    def test_invalid_json_returns_error_code(self):
        with patch(
            "resume_parser.resume_from_json.load_resume_from_json",
            side_effect=json.JSONDecodeError("bad", "doc", 0),
        ):
            code = self._run_with_args(["-i", "/tmp/some-folder"])
        self.assertEqual(code, 1)

    def test_value_error_returns_error_code(self):
        with patch(
            "resume_parser.resume_from_json.load_resume_from_json",
            side_effect=ValueError("bad model"),
        ):
            code = self._run_with_args(["-i", "/tmp/some-folder"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
