"""Tests for resume HTML render and template copy."""
import unittest
from pathlib import Path
import tempfile

# Import from resume_to_flock (add parent to path if needed)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from resume_to_flock import _render_resume_html, _template_dir


class TestRenderResumeHtml(unittest.TestCase):
    def test_renders_html_and_copies_template(self):
        flock_jobs = [
            {"role": "Engineer", "employer": "Acme", "start": "2020-01-01", "end": "CURRENT_DATE", "Description": "Did stuff."},
        ]
        skills = {"Python": {"url": "https://python.org", "img": "", "categoryIDs": ["programming-language"], "jobIDs": [0]}}
        categories = {"programming-language": {"name": "Programming Language"}}
        resume_meta = {
            "contact": {"name": "Jane Doe", "email": "j@example.com", "phone": "", "location": "", "linkedin": "", "website": ""},
            "title": "Data Engineer",
            "summary": "Summary here.",
            "certifications": [],
            "skills": [],
            "other_sections": [],
        }
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            resume_path, template_path = _render_resume_html(flock_jobs, skills, resume_meta, categories, out_dir)
            self.assertTrue(resume_path.exists())
            self.assertTrue(template_path.exists())
            html = resume_path.read_text(encoding="utf-8")
            self.assertIn("Jane Doe", html)
            self.assertIn("Data Engineer", html)
            self.assertIn("Acme", html)
            self.assertIn("Python", html)
            self.assertIn("Programming Language", html)
