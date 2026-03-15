"""Tests for schemas/validate_parsed_resume.py (folder and schema validation)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Load validate_parsed_resume from schemas/ so schema path resolves
_schemas_dir = Path(__file__).resolve().parent.parent / "schemas"
sys.path.insert(0, str(_schemas_dir))

import jsonschema
import validate_parsed_resume as vpr


def _minimal_jobs_dict():
    return {"0": {"index": 0, "role": "Engineer", "employer": "Acme", "start": None, "end": None, "Description": None, "skillIDs": []}}


def _minimal_jobs_list():
    return [{"index": 0, "role": "Engineer", "employer": "Acme", "start": None, "end": None, "Description": None, "skillIDs": []}]


def _minimal_skills():
    return {"python": {"name": "Python", "url": None, "img": None, "categoryIDs": [], "jobIDs": []}}


def _minimal_categories():
    return {"lang": {"name": "Language", "skillIDs": []}}


def _minimal_other_sections():
    return {"summary": "", "title": "", "contact": {}, "certifications": [], "websites": [], "custom_sections": []}


def _minimal_meta():
    return {"id": "resume-1", "displayName": "Resume 1", "createdAt": "2025-03-08T12:00:00.000Z", "jobCount": 1, "skillCount": 1}


class TestValidateJobs(unittest.TestCase):
    def test_valid_jobs_dict(self):
        vpr.validate_jobs(_minimal_jobs_dict())

    def test_valid_jobs_list(self):
        vpr.validate_jobs(_minimal_jobs_list())

    def test_invalid_jobs_raises(self):
        with self.assertRaises(jsonschema.ValidationError):
            vpr.validate_jobs("not an object or array")


class TestValidateSkills(unittest.TestCase):
    def test_valid_skills(self):
        vpr.validate_skills(_minimal_skills())

    def test_valid_empty_skills(self):
        vpr.validate_skills({})

    def test_invalid_skills_raises(self):
        with self.assertRaises(jsonschema.ValidationError):
            vpr.validate_skills([{"name": "X"}])  # must be object


class TestValidateCategories(unittest.TestCase):
    def test_valid_categories(self):
        vpr.validate_categories(_minimal_categories())

    def test_valid_empty_categories(self):
        vpr.validate_categories({})

    def test_invalid_categories_raises(self):
        with self.assertRaises(jsonschema.ValidationError):
            vpr.validate_categories([])  # must be object


class TestValidateOtherSections(unittest.TestCase):
    def test_valid_other_sections(self):
        vpr.validate_other_sections(_minimal_other_sections())

    def test_invalid_other_sections_raises(self):
        with self.assertRaises(jsonschema.ValidationError):
            vpr.validate_other_sections({"certifications": [{}]})  # certificationItem requires "name"


class TestValidateMeta(unittest.TestCase):
    def test_valid_meta(self):
        vpr.validate_meta(_minimal_meta())

    def test_invalid_meta_raises(self):
        with self.assertRaises(jsonschema.ValidationError):
            vpr.validate_meta({"id": "x"})  # missing required displayName, createdAt, jobCount, skillCount


class TestValidateFolder(unittest.TestCase):
    def test_validate_folder_returns_list_of_validated_files(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text(json.dumps(_minimal_jobs_dict()), encoding="utf-8")
            (folder / "skills.json").write_text(json.dumps(_minimal_skills()), encoding="utf-8")
            (folder / "categories.json").write_text(json.dumps(_minimal_categories()), encoding="utf-8")
            (folder / "other-sections.json").write_text(json.dumps(_minimal_other_sections()), encoding="utf-8")
            (folder / "meta.json").write_text(json.dumps(_minimal_meta()), encoding="utf-8")

            result = vpr.validate_folder(folder)
            self.assertIn("jobs.json", result)
            self.assertIn("skills.json", result)
            self.assertIn("categories.json", result)
            self.assertIn("other-sections.json", result)
            self.assertIn("meta.json", result)
            self.assertEqual(len(result), 5)

    def test_validate_folder_only_validates_existing_files(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text(json.dumps(_minimal_jobs_dict()), encoding="utf-8")

            result = vpr.validate_folder(folder)
            self.assertEqual(result, ["jobs.json"])

    def test_validate_folder_invalid_json_raises(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text("not json", encoding="utf-8")

            with self.assertRaises(json.JSONDecodeError):
                vpr.validate_folder(folder)

    def test_validate_folder_invalid_data_raises(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text('"invalid"', encoding="utf-8")

            with self.assertRaises(jsonschema.ValidationError):
                vpr.validate_folder(folder)


class TestMain(unittest.TestCase):
    def test_main_no_args_returns_1(self):
        with patch.object(sys, "argv", ["validate_parsed_resume.py"]):
            with patch("sys.stderr"):
                result = vpr.main()
        self.assertEqual(result, 1)

    def test_main_valid_folder_returns_0(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text(json.dumps(_minimal_jobs_dict()), encoding="utf-8")
            (folder / "skills.json").write_text(json.dumps(_minimal_skills()), encoding="utf-8")
            (folder / "categories.json").write_text(json.dumps(_minimal_categories()), encoding="utf-8")
            (folder / "other-sections.json").write_text(json.dumps(_minimal_other_sections()), encoding="utf-8")
            (folder / "meta.json").write_text(json.dumps(_minimal_meta()), encoding="utf-8")

            with patch.object(sys, "argv", ["validate_parsed_resume.py", str(folder)]):
                result = vpr.main()
            self.assertEqual(result, 0)

    def test_main_invalid_folder_returns_1(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text("not json", encoding="utf-8")

            with patch.object(sys, "argv", ["validate_parsed_resume.py", str(folder)]):
                with patch("sys.stderr"):
                    result = vpr.main()
            self.assertEqual(result, 1)

    def test_main_schema_violation_returns_1(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text('"not object or array"', encoding="utf-8")

            with patch.object(sys, "argv", ["validate_parsed_resume.py", str(folder)]):
                with patch("sys.stderr"):
                    result = vpr.main()
            self.assertEqual(result, 1)
