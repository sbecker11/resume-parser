"""Tests for resume_parser.reparse_education_only."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from resume_parser.reparse_education_only import _find_resume_file, _write_education_json, main


class TestFindResumeFile(unittest.TestCase):
    def test_returns_none_when_no_resume_file(self, ):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "notes.txt").write_text("hi")
            self.assertIsNone(_find_resume_file(folder))

    def test_finds_docx_over_other_files(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "notes.txt").write_text("hi")
            (folder / "resume.docx").write_text("doc")
            (folder / "subdir").mkdir()
            found = _find_resume_file(folder)
            self.assertEqual(found.name, "resume.docx")

    def test_finds_pdf(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "resume.pdf").write_text("doc")
            found = _find_resume_file(folder)
            self.assertEqual(found.name, "resume.pdf")


class TestWriteEducationJson(unittest.TestCase):
    def test_writes_only_legitimate_degrees(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "education.json"
            entries = [
                {
                    "role": "BS Computer Science",
                    "employer": "Some University",
                    "start": "2000",
                    "end": "2004",
                    "description": "desc",
                },
                {"role": "not a real degree at all", "employer": "Nowhere"},
            ]
            with patch(
                "resume_parser.reparse_education_only.has_legitimate_degree",
                side_effect=lambda d: "Computer Science" in d,
            ), patch(
                "resume_parser.reparse_education_only.sanitize_education_description",
                side_effect=lambda t: t,
            ), patch("resume_parser.reparse_education_only.validate_education") as mock_validate:
                _write_education_json(entries, out_path)

            data = json.loads(out_path.read_text())
            self.assertEqual(len(data), 1)
            self.assertEqual(data["0"]["degree"], "BS Computer Science")
            mock_validate.assert_called_once()

    def test_skips_entries_with_blank_role(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "education.json"
            entries = [{"role": "", "employer": "X"}]
            with patch("resume_parser.reparse_education_only.validate_education"):
                _write_education_json(entries, out_path)
            data = json.loads(out_path.read_text())
            self.assertEqual(data, {})


class TestMain(unittest.TestCase):
    def _run_with_args(self, argv):
        with patch.object(sys, "argv", ["reparse-education-only"] + argv):
            return main()

    def test_returns_error_when_root_is_not_a_directory(self):
        code = self._run_with_args(["/path/does/not/exist"])
        self.assertEqual(code, 1)

    def test_returns_error_when_no_subfolders(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_with_args([tmp])
        self.assertEqual(code, 1)

    def test_skips_folder_with_existing_education_json(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "job-1"
            folder.mkdir()
            (folder / "education.json").write_text("{}")
            code = self._run_with_args([str(root)])
        self.assertEqual(code, 0)

    def test_fails_folder_with_no_resume_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "job-1"
            folder.mkdir()
            code = self._run_with_args([str(root)])
        # failures > 0 => exit code 2
        self.assertEqual(code, 2)

    def test_success_path_writes_education_json(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "job-1"
            folder.mkdir()
            (folder / "resume.docx").write_text("doc")

            jobs = [{"role": "Engineer", "employer": "Acme"}]
            education = [{"role": "BS Computer Science", "employer": "Uni", "description": "d"}]

            with patch(
                "resume_parser.reparse_education_only.extract_text", return_value="some resume text"
            ), patch(
                "resume_parser.reparse_education_only.parse_jobs_with_llm", return_value=jobs
            ), patch(
                "resume_parser.reparse_education_only._split_jobs_and_education",
                return_value=(jobs, education),
            ), patch(
                "resume_parser.reparse_education_only.has_legitimate_degree", return_value=True
            ), patch(
                "resume_parser.reparse_education_only.sanitize_education_description",
                side_effect=lambda t: t,
            ), patch("resume_parser.reparse_education_only.validate_education"):
                code = self._run_with_args([str(root)])

            self.assertEqual(code, 0)
            self.assertTrue((folder / "education.json").exists())

    def test_no_legitimate_education_removes_existing_file_when_overwrite(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "job-1"
            folder.mkdir()
            (folder / "resume.docx").write_text("doc")
            (folder / "education.json").write_text("{}")

            with patch(
                "resume_parser.reparse_education_only.extract_text", return_value="some resume text"
            ), patch(
                "resume_parser.reparse_education_only.parse_jobs_with_llm", return_value=[]
            ), patch(
                "resume_parser.reparse_education_only._split_jobs_and_education",
                return_value=([], []),
            ):
                code = self._run_with_args([str(root), "--overwrite"])

            self.assertEqual(code, 0)
            self.assertFalse((folder / "education.json").exists())

    def test_extract_text_failure_counts_as_failure(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "job-1"
            folder.mkdir()
            (folder / "resume.docx").write_text("doc")

            with patch(
                "resume_parser.reparse_education_only.extract_text", return_value="   "
            ):
                code = self._run_with_args([str(root)])

            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
