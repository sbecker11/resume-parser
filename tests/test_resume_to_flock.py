"""Tests for resume_to_flock.py to achieve >= 80% coverage."""
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
    _template_dir,
    _linkify,
    _render_resume_html,
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
            self.assertIn("const jobs = ", path.read_text())
            self.assertIn("Engineer", path.read_text())

    def test_write_skills_mjs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            # skills dict is keyed by skillID; each item has "name" (display name)
            skills_by_id = {"python": {"name": "Python", "url": "", "img": "", "categoryIDs": [], "jobIDs": []}}
            path = _write_skills_mjs(skills_by_id, out)
            self.assertTrue(path.exists())
            text = path.read_text()
            self.assertIn("const skills = ", text)
            self.assertIn("python", text)
            self.assertIn("Python", text)

    def test_write_categories_mjs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            categories = {"lang": {"name": "Language", "skillIDs": ["python"]}}
            path = _write_categories_mjs(categories, out)
            self.assertTrue(path.exists())
            self.assertIn("const categories = ", path.read_text())

    def test_write_other_sections_mjs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            meta = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
            path = _write_other_sections_mjs(meta, out)
            self.assertTrue(path.exists())
            self.assertIn("const otherSections = ", path.read_text())


class TestTemplateDir(unittest.TestCase):
    def test_returns_templates_subdir(self):
        t = _template_dir()
        self.assertEqual(t.name, "templates")
        self.assertTrue(t.is_absolute() or "templates" in str(t))


class TestLinkify(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(_linkify(""), "")

    def test_none_equivalent(self):
        self.assertEqual(_linkify(None or ""), "")

    def test_no_url_returns_escaped(self):
        result = _linkify("Hello world")
        self.assertIn("Hello world", result)
        self.assertNotIn("<a ", str(result))

    def test_wraps_single_url(self):
        result = _linkify("See https://example.com for more.")
        self.assertIn('href="https://example.com"', str(result))
        self.assertIn(">https://example.com<", str(result))

    def test_wraps_multiple_urls(self):
        result = _linkify("A https://a.com and https://b.com end")
        self.assertIn("https://a.com", str(result))
        self.assertIn("https://b.com", str(result))
        self.assertIn("<a ", str(result))


class TestRenderResumeHtmlBranches(unittest.TestCase):
    """Cover description bullets (• and . ), skills_without_category, template copy."""

    def test_description_bullets_with_dot_separator(self):
        flock_jobs = [
            {"role": "R", "employer": "E", "Description": "First sentence. Second sentence. Third."},
        ]
        skills = {}
        categories = {}
        resume_meta = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            resume_path, _ = _render_resume_html(flock_jobs, skills, resume_meta, categories, out_dir)
            html = resume_path.read_text()
            self.assertIn("First sentence", html)
            self.assertIn("Second sentence", html)

    def test_description_bullets_with_bullet_char(self):
        flock_jobs = [
            {"role": "R", "employer": "E", "Description": "Item one • Item two • Item three"},
        ]
        skills = {}
        categories = {}
        resume_meta = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            resume_path, _ = _render_resume_html(flock_jobs, skills, resume_meta, categories, out_dir)
            html = resume_path.read_text()
            self.assertIn("Item one", html)
            self.assertIn("Item two", html)

    def test_skills_without_category_appear_in_other(self):
        flock_jobs = [{"role": "R", "employer": "E", "Description": ""}]
        skills = {
            "Python": {"url": "", "img": "", "categoryIDs": ["prog"], "jobIDs": []},
            "UnknownSkill": {"url": "", "img": "", "categoryIDs": [], "jobIDs": []},
        }
        categories = {"prog": {"name": "Programming", "skillIDs": ["python"]}}
        resume_meta = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            resume_path, _ = _render_resume_html(flock_jobs, skills, resume_meta, categories, out_dir)
            html = resume_path.read_text()
            self.assertIn("Other", html)
            self.assertIn("UnknownSkill", html)

    def test_template_copy_when_source_exists(self):
        flock_jobs = [{"role": "R", "employer": "E", "Description": ""}]
        skills = {}
        categories = {}
        resume_meta = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            _, template_path = _render_resume_html(flock_jobs, skills, resume_meta, categories, out_dir)
            self.assertTrue(template_path.exists())
            self.assertEqual(template_path.name, "resume_template.html")


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
                                        with patch("sys.argv", ["resume_to_flock.py", resume_path, "-o", str(out_dir)]):
                                            with patch("builtins.print"):
                                                result = main()
                self.assertEqual(result, 0)
                self.assertTrue((out_dir / "jobs.mjs").exists())
                self.assertTrue((out_dir / "skills.mjs").exists())
                self.assertTrue((out_dir / "categories.mjs").exists())
                self.assertTrue((out_dir / "other-sections.mjs").exists())
                self.assertTrue((out_dir / "resume.html").exists())
                self.assertTrue((out_dir / "resume_template.html").exists())
        finally:
            Path(resume_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
