"""Tests for resume_parser.env_loader (safe .env loading)."""
import logging
import unittest
from pathlib import Path
from unittest.mock import patch

from resume_parser.env_loader import load_dotenv_safely


class TestLoadDotenvSafely(unittest.TestCase):
    def test_loads_a_valid_env_file(self):
        with patch("resume_parser.env_loader.load_dotenv") as mock_load:
            load_dotenv_safely(Path("/fake/.env"))
        mock_load.assert_called_once_with(Path("/fake/.env"))

    def test_reports_and_swallows_unicode_decode_error(self):
        error = UnicodeDecodeError("utf-8", b"\xad", 0, 1, "invalid start byte")
        with patch("resume_parser.env_loader.load_dotenv", side_effect=error):
            with self.assertLogs("resume_parser.env_loader", level="WARNING") as ctx:
                load_dotenv_safely(Path("/fake/.env"))
        self.assertIn("git-crypt encrypted", ctx.output[0])

    def test_reports_and_swallows_value_error(self):
        with patch("resume_parser.env_loader.load_dotenv", side_effect=ValueError("bad syntax")):
            with self.assertLogs("resume_parser.env_loader", level="WARNING") as ctx:
                load_dotenv_safely(Path("/fake/.env"))
        self.assertIn("bad syntax", ctx.output[0])


if __name__ == "__main__":
    unittest.main()
