"""Tests for resume_parser.render_resume_html (HTML generation from JSON files)."""
import json
import tempfile
import unittest
from pathlib import Path

from resume_parser.render_resume_html import render_resume_html, _load_json


class TestRenderResumeHtml(unittest.TestCase):
    """Test render_resume_html reads JSON and writes resume.html."""

    def test_renders_html_from_json_files(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            # Write minimal JSON files
            jobs = {"0": {"index": 0, "role": "Engineer", "employer": "Acme", "start": "2020-01-01", "end": "CURRENT_DATE", "Description": "Did stuff.", "skillIDs": []}}
            skills = {"python": {"name": "Python", "url": "https://python.org", "img": "", "categoryIDs": ["programming-language"], "jobIDs": [0]}}
            categories = {"programming-language": {"name": "Programming Language", "skillIDs": ["python"]}}
            other = {
                "contact": {"name": "Jane Doe", "email": "j@example.com", "phone": "", "location": "", "linkedin": "", "website": ""},
                "title": "Data Engineer",
                "summary": "Summary here.",
                "certifications": [],
                "skills": ["Python"],
                "other_sections": [],
            }
            (out_dir / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
            (out_dir / "skills.json").write_text(json.dumps(skills), encoding="utf-8")
            (out_dir / "categories.json").write_text(json.dumps(categories), encoding="utf-8")
            (out_dir / "other-sections.json").write_text(json.dumps(other), encoding="utf-8")

            resume_path, template_path = render_resume_html(out_dir)
            self.assertTrue(resume_path.exists())
            self.assertTrue(template_path.exists())
            html = resume_path.read_text(encoding="utf-8")
            self.assertIn("Jane Doe", html)
            self.assertIn("Data Engineer", html)
            self.assertIn("Acme", html)
            self.assertIn("Python", html)
            self.assertIn("Programming Language", html)

    def test_load_json_parses(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b'{"0": {"role": "Dev"}}')
            f.flush()
        try:
            data = _load_json(Path(f.name))
            self.assertEqual(data, {"0": {"role": "Dev"}})
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_missing_json_raises(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            with self.assertRaises(FileNotFoundError):
                render_resume_html(out_dir)

    def _write_json_files(self, out_dir: Path, jobs: dict, skills: dict, categories: dict, other: dict):
        (out_dir / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
        (out_dir / "skills.json").write_text(json.dumps(skills), encoding="utf-8")
        (out_dir / "categories.json").write_text(json.dumps(categories), encoding="utf-8")
        (out_dir / "other-sections.json").write_text(json.dumps(other), encoding="utf-8")

    def test_description_bullets_from_json(self):
        jobs = {"0": {"index": 0, "role": "R", "employer": "E", "start": "", "end": "", "Description": "First sentence. Second sentence. Third.", "skillIDs": []}}
        skills = {}
        categories = {}
        other = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            self._write_json_files(out_dir, jobs, skills, categories, other)
            resume_path, _ = render_resume_html(out_dir)
            html = resume_path.read_text()
            self.assertIn("First sentence", html)
            self.assertIn("Second sentence", html)

    def test_skills_without_category_in_other(self):
        jobs = {"0": {"index": 0, "role": "R", "employer": "E", "Description": "", "skillIDs": []}}
        skills = {
            "python": {"name": "Python", "url": "", "img": "", "categoryIDs": ["prog"], "jobIDs": []},
            "unknown": {"name": "UnknownSkill", "url": "", "img": "", "categoryIDs": [], "jobIDs": []},
        }
        categories = {"prog": {"name": "Programming", "skillIDs": ["python"]}}
        other = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "other_sections": []}
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            self._write_json_files(out_dir, jobs, skills, categories, other)
            resume_path, _ = render_resume_html(out_dir)
            html = resume_path.read_text()
            self.assertIn("Other", html)
            self.assertIn("UnknownSkill", html)

    def test_linkify_in_summary(self):
        jobs = {"0": {"index": 0, "role": "R", "employer": "E", "Description": "", "skillIDs": []}}
        skills = {}
        categories = {}
        other = {"contact": {}, "title": "", "summary": "See https://example.com for more.", "certifications": [], "skills": [], "other_sections": []}
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            self._write_json_files(out_dir, jobs, skills, categories, other)
            resume_path, _ = render_resume_html(out_dir)
            html = resume_path.read_text()
            self.assertIn('href="https://example.com"', html)

    def test_render_with_resume_flock_format(self):
        """render_resume_html handles PARSED-RESUME-FORMAT: custom_sections, websites, certifications {name,url,description}."""
        jobs = {"0": {"index": 0, "role": "R", "employer": "E", "Description": "", "skillIDs": []}}
        skills = {}
        categories = {}
        other = {
            "contact": {"name": "Jane Doe"},
            "title": "Engineer",
            "summary": "",
            "certifications": [
                {"name": "AWS CPA", "url": "https://aws.amazon.com/certification/", "description": "AWS 2023"},
            ],
            "websites": [{"label": "LinkedIn", "url": "https://linkedin.com/in/jane"}],
            "custom_sections": [{"title": "Awards", "content": "Best dev 2024"}],
        }
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            self._write_json_files(out_dir, jobs, skills, categories, other)
            resume_path, _ = render_resume_html(out_dir)
            html = resume_path.read_text()
            self.assertIn("Jane Doe", html)
            self.assertIn("AWS CPA", html)
            self.assertIn("Best dev 2024", html)

    def test_default_strips_square_brackets(self):
        """By default [Skill] in descriptions/summary/other is rendered as Skill."""
        jobs = {
            "0": {
                "index": 0,
                "role": "R",
                "employer": "E",
                "Description": "Used [Python] and [Django]. Built [RAG] pipeline.",
                "skillIDs": [],
            }
        }
        skills = {}
        categories = {}
        other = {
            "contact": {},
            "title": "",
            "summary": "Expert in [ML] and [NLP].",
            "certifications": [],
            "skills": [],
            "custom_sections": [{"title": "Tech", "content": "Loves [React] and [Node.js]."}],
        }
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            self._write_json_files(out_dir, jobs, skills, categories, other)
            resume_path, _ = render_resume_html(out_dir)
            html = resume_path.read_text()
            self.assertIn("Python", html)
            self.assertIn("Django", html)
            self.assertIn("RAG", html)
            self.assertIn("ML", html)
            self.assertIn("NLP", html)
            self.assertIn("React", html)
            self.assertIn("Node.js", html)
            self.assertNotIn("[Python]", html)
            self.assertNotIn("[Django]", html)
            self.assertNotIn("[ML]", html)
            self.assertNotIn("[React]", html)

    def test_show_brackets_keeps_square_brackets(self):
        """With skip_square_brackets=False (--show-brackets), [Skill] is left in output."""
        jobs = {"0": {"index": 0, "role": "R", "employer": "E", "Description": "Used [Python].", "skillIDs": []}}
        skills = {}
        categories = {}
        other = {"contact": {}, "title": "", "summary": "", "certifications": [], "skills": [], "custom_sections": []}
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            self._write_json_files(out_dir, jobs, skills, categories, other)
            resume_path, _ = render_resume_html(out_dir, skip_square_brackets=False)
            html = resume_path.read_text()
            self.assertIn("[Python]", html)
