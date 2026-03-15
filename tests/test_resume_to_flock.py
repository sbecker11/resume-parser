"""Tests for resume_to_flock.py to achieve >= 80% coverage."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resume_to_flock import (
    _default_output_dir,
    _write_jobs_mjs,
    _write_skills_mjs,
    _write_categories_mjs,
    _write_other_sections_mjs,
    _write_meta_json,
    main,
)


class TestDefaultOutputDir(unittest.TestCase):
    def test_returns_cwd_when_no_candidate_exists(self):
        # When no candidate path exists, _default_output_dir returns Path.cwd()
        with patch.object(Path, "exists", return_value=False):
            result = _default_output_dir()
        self.assertEqual(result, Path.cwd())

    def test_returns_cwd_after_trying_candidates(self):
        # When cwd is the only "existing" (last fallback), we get cwd
        with tempfile.TemporaryDirectory() as d:
            with patch.object(Path, "cwd", return_value=Path(d)):
                with patch.object(Path, "exists", return_value=False):
                    result = _default_output_dir()
                self.assertEqual(result, Path(d))


class TestWriters(unittest.TestCase):
    def test_write_jobs_mjs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            jobs = {"0": {"index": 0, "role": "Engineer", "skillIDs": []}}
            path = _write_jobs_mjs(jobs, out)
            self.assertTrue(path.exists())
            self.assertIn("export const jobs = ", path.read_text())
            self.assertIn("Engineer", path.read_text())

    def test_write_skills_mjs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            # skills dict is keyed by skillID; each item has "name" (display name)
            skills_by_id = {"python": {"name": "Python", "url": "", "img": "", "categoryIDs": [], "jobIDs": []}}
            path = _write_skills_mjs(skills_by_id, out)
            self.assertTrue(path.exists())
            text = path.read_text()
            self.assertIn("export const skills = ", text)
            self.assertIn("python", text)
            self.assertIn("Python", text)

    def test_write_categories_mjs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            categories = {"lang": {"name": "Language", "skillIDs": ["python"]}}
            path = _write_categories_mjs(categories, out)
            self.assertTrue(path.exists())
            self.assertIn("export const categories = ", path.read_text())

    def test_write_other_sections_mjs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            meta = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
            path = _write_other_sections_mjs(meta, out)
            self.assertTrue(path.exists())
            self.assertIn("export const otherSections = ", path.read_text())

    def test_other_sections_resume_flock_schema(self):
        """other-sections.mjs output matches PARSED-RESUME-FORMAT: certifications {name,url,description}, websites, custom_sections."""
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            meta = {
                "contact": {"name": "Jane", "email": "j@x.com"},
                "title": "Engineer",
                "summary": "Summary.",
                "certifications": [
                    {"name": "AWS CPA", "issuer": "AWS", "date": "2023"},
                ],
                "skills": ["Python"],
                "websites": [{"label": "LinkedIn", "url": "https://linkedin.com/in/jane"}],
                "other_sections": [{"title": "Awards", "content": "Best dev 2024"}],
            }
            path = _write_other_sections_mjs(meta, out)
            text = path.read_text()
            m = re.search(r"export const otherSections = (.+);\s*$", text, re.DOTALL)
            self.assertIsNotNone(m)
            data = json.loads(m.group(1))
            self.assertEqual(data["contact"]["name"], "Jane")
            self.assertEqual(data["title"], "Engineer")
            self.assertEqual(data["summary"], "Summary.")
            self.assertEqual(len(data["certifications"]), 1)
            self.assertEqual(data["certifications"][0]["name"], "AWS CPA")
            self.assertIn("url", data["certifications"][0])
            self.assertIn("description", data["certifications"][0])
            self.assertEqual(data["certifications"][0]["description"], "AWS 2023")
            self.assertEqual(data["websites"], [{"label": "LinkedIn", "url": "https://linkedin.com/in/jane"}])
            self.assertEqual(data["custom_sections"], [{"title": "Awards", "content": "Best dev 2024"}])
            self.assertEqual(data["skills"], ["Python"])

    def test_meta_json_schema(self):
        """meta.json matches PARSED-RESUME-FORMAT: id, displayName, createdAt, fileName, jobCount, skillCount."""
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            path = _write_meta_json(
                out, resume_id="parsed-resume-1", display_name="Jane Doe 2025",
                file_name="resume.docx", job_count=11, skill_count=85,
            )
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["id"], "parsed-resume-1")
            self.assertEqual(data["displayName"], "Jane Doe 2025")
            self.assertIn("createdAt", data)
            self.assertRegex(data["createdAt"], r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
            self.assertEqual(data["fileName"], "resume.docx")
            self.assertEqual(data["jobCount"], 11)
            self.assertEqual(data["skillCount"], 85)


class TestMain(unittest.TestCase):
    def test_file_not_found_returns_1(self):
        with patch("sys.argv", ["resume_to_flock.py", "/nonexistent/resume.docx"]):
            result = main()
            self.assertEqual(result, 1)

    def test_no_llm_returns_0(self):
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"dummy")
            resume_path = f.name
        try:
            with patch("resume_to_flock.extract_text", return_value="Sample resume text here."):
                with patch("sys.argv", ["resume_to_flock.py", resume_path, "--no-llm"]):
                    with patch("builtins.print"):
                        result = main()
            self.assertEqual(result, 0)
        finally:
            Path(resume_path).unlink(missing_ok=True)

    def test_full_pipeline_writes_all_outputs(self):
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"dummy")
            resume_path = f.name
        try:
            with tempfile.TemporaryDirectory() as out_d:
                out_dir = Path(out_d)
                jobs_data = [
                    {"role": "Engineer", "employer": "Acme", "start": "2020-01-01", "end": "", "description": "Did Python."}
                ]
                resume_meta = {
                    "contact": {},
                    "title": "",
                    "summary": "",
                    "certifications": [],
                    "skills": ["Python"],
                    "other_sections": [],
                }
                skills_with_cats = {
                    "Python": {"url": "", "img": "", "jobIDs": [], "categories": ["Programming Language"]},
                }

                with patch("resume_to_flock.extract_text", return_value="Resume text"):
                    with patch("resume_to_flock.get_llm_provider", return_value="anthropic"):
                        with patch("resume_to_flock.parse_jobs_with_llm", return_value=jobs_data):
                            with patch("resume_to_flock.parse_resume_sections", return_value=resume_meta):
                                with patch("resume_to_flock.enrich_skills_with_llm", side_effect=lambda s: s):
                                    with patch("resume_to_flock.categorize_skills_with_llm", return_value=skills_with_cats):
                                        with patch("sys.argv", ["resume_to_flock.py", resume_path, "-o", str(out_dir), "--no-merge", "--render"]):
                                            with patch("builtins.print"):
                                                result = main()
                self.assertEqual(result, 0)
                # Original resume copied into output folder with original filename
                resume_copy = out_dir / Path(resume_path).name
                self.assertTrue(resume_copy.exists(), f"Expected copy {resume_copy}")
                orig_size = Path(resume_path).stat().st_size
                copy_size = resume_copy.stat().st_size
                self.assertEqual(copy_size, orig_size, f"Copy file size {copy_size} should match original {orig_size}")
                self.assertEqual(resume_copy.read_bytes(), Path(resume_path).read_bytes(), "Copy should match original")
                self.assertTrue((out_dir / "jobs.mjs").exists())
                self.assertTrue((out_dir / "skills.mjs").exists())
                self.assertTrue((out_dir / "categories.mjs").exists())
                self.assertTrue((out_dir / "other-sections.mjs").exists())
                self.assertTrue((out_dir / "resume.html").exists())
                self.assertTrue((out_dir / "resume_template.html").exists())
                self.assertTrue((out_dir / "meta.json").exists())
        finally:
            Path(resume_path).unlink(missing_ok=True)

    def test_full_pipeline_with_no_merge_skips_interactive(self):
        """With --no-merge and 2+ skills, run_merge_interactive is not called."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"dummy")
            resume_path = f.name
        try:
            with tempfile.TemporaryDirectory() as out_d:
                out_dir = Path(out_d)
                jobs_data = [
                    {"role": "Engineer", "employer": "Acme", "start": "2020-01-01", "end": "", "description": "Python and Java."},
                ]
                resume_meta = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
                skills_with_cats = {
                    "Python": {"url": "", "img": "", "jobIDs": [0], "categories": ["Programming"]},
                    "Java": {"url": "", "img": "", "jobIDs": [0], "categories": ["Programming"]},
                }
                with patch("resume_to_flock.extract_text", return_value="Resume text"):
                    with patch("resume_to_flock.get_llm_provider", return_value="anthropic"):
                        with patch("resume_to_flock.parse_jobs_with_llm", return_value=jobs_data):
                            with patch("resume_to_flock.parse_resume_sections", return_value=resume_meta):
                                with patch("resume_to_flock.enrich_skills_with_llm", side_effect=lambda s: s):
                                    with patch("resume_to_flock.categorize_skills_with_llm", return_value=skills_with_cats):
                                        merge_mock = MagicMock()
                                        with patch("resume_to_flock.run_merge_interactive", merge_mock):
                                            with patch("sys.argv", ["resume_to_flock.py", resume_path, "-o", str(out_dir), "--no-merge"]):
                                                with patch("builtins.print"):
                                                    result = main()
                self.assertEqual(result, 0)
                merge_mock.assert_not_called()
        finally:
            Path(resume_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
