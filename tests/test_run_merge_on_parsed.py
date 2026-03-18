"""Tests for resume_parser.run_merge_on_parsed (skill merge on parsed folder)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from resume_parser.run_merge_on_parsed import (
    skills_file_to_merge_format,
    skills_merge_to_file_format,
    jobs_dict_to_list,
    run_merge_in_dir,
    reconcile_job_descriptions_in_dir,
    main,
)


class TestSkillsFileToMergeFormat(unittest.TestCase):
    def test_converts_id_keyed_to_name_keyed(self):
        skills_by_id = {
            "python": {"name": "Python", "url": "https://python.org", "img": "", "categoryIDs": [], "jobIDs": [0]},
            "java": {"name": "Java", "url": "", "img": "", "categoryIDs": [], "jobIDs": []},
        }
        result = skills_file_to_merge_format(skills_by_id)
        self.assertIn("Python", result)
        self.assertIn("Java", result)
        self.assertEqual(result["Python"]["id"], "python")
        self.assertEqual(result["Python"]["url"], "https://python.org")
        self.assertEqual(result["Python"]["jobIDs"], [0])
        self.assertEqual(result["Java"]["jobIDs"], [])

    def test_duplicate_names_get_suffix(self):
        skills_by_id = {
            "py": {"name": "Python", "url": "", "img": "", "categoryIDs": [], "jobIDs": []},
            "py3": {"name": "Python", "url": "", "img": "", "categoryIDs": [], "jobIDs": []},
        }
        result = skills_file_to_merge_format(skills_by_id)
        names = list(result.keys())
        self.assertEqual(len(names), 2)
        self.assertIn("Python", names)
        self.assertIn("Python (py3)", names)

    def test_empty_skills(self):
        self.assertEqual(skills_file_to_merge_format({}), {})


class TestSkillsMergeToFileFormat(unittest.TestCase):
    def test_converts_name_keyed_back_to_id_keyed(self):
        skills_by_name = {
            "Python": {"id": "python", "url": "", "img": "", "categoryIDs": [], "jobIDs": [0]},
            "Java": {"id": "java", "url": "", "img": "", "categoryIDs": [], "jobIDs": []},
        }
        result = skills_merge_to_file_format(skills_by_name)
        self.assertIn("python", result)
        self.assertIn("java", result)
        self.assertEqual(result["python"]["name"], "Python")
        self.assertEqual(result["python"]["jobIDs"], [0])

    def test_strips_duplicate_suffix_from_name(self):
        skills_by_name = {
            "Python (py3)": {"id": "py3", "url": "", "img": "", "categoryIDs": [], "jobIDs": []},
        }
        result = skills_merge_to_file_format(skills_by_name)
        self.assertEqual(result["py3"]["name"], "Python")


class TestJobsDictToList(unittest.TestCase):
    def test_orders_by_numeric_key(self):
        jobs_dict = {"1": {"index": 1, "role": "B"}, "0": {"index": 0, "role": "A"}}
        result = jobs_dict_to_list(jobs_dict)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["role"], "A")
        self.assertEqual(result[1]["role"], "B")

    def test_empty_dict(self):
        self.assertEqual(jobs_dict_to_list({}), [])


class TestRunMergeInDir(unittest.TestCase):
    def _write_parsed_folder(self, folder: Path, job_index: int = 0) -> None:
        jobs = {str(job_index): {"index": job_index, "role": "Engineer", "employer": "Acme", "start": "", "end": "", "Description": "Used Python and Java.", "skillIDs": ["python", "java"]}}
        skills = {
            "python": {"name": "Python", "url": "", "img": "", "categoryIDs": ["lang"], "jobIDs": [job_index]},
            "java": {"name": "Java", "url": "", "img": "", "categoryIDs": ["lang"], "jobIDs": [job_index]},
        }
        categories = {"lang": {"name": "Language", "skillIDs": ["python", "java"]}}
        (folder / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
        (folder / "skills.json").write_text(json.dumps(skills), encoding="utf-8")
        (folder / "categories.json").write_text(json.dumps(categories), encoding="utf-8")

    def test_run_merge_in_dir_success_without_render(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self._write_parsed_folder(folder)

            with patch("resume_parser.run_merge_on_parsed.run_merge_interactive", return_value=[]) as mock_merge:
                result = run_merge_in_dir(folder, render=False, accept_all=False)
            self.assertTrue(result)
            mock_merge.assert_called_once()
            # Files should be written (merge returned no replacements but still writes back)
            self.assertTrue((folder / "skills.json").exists())
            self.assertTrue((folder / "categories.json").exists())
            self.assertTrue((folder / "jobs.json").exists())

    def test_run_merge_in_dir_with_render_calls_render_resume_html(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self._write_parsed_folder(folder)
            (folder / "other-sections.json").write_text(json.dumps({"contact": {}, "title": "", "summary": "", "certifications": [], "websites": [], "custom_sections": []}), encoding="utf-8")

            with patch("resume_parser.run_merge_on_parsed.run_merge_interactive", return_value=[]):
                with patch("resume_parser.render_resume_html.render_resume_html", return_value=(folder / "resume.html", folder / "resume_template.html")) as mock_render:
                    result = run_merge_in_dir(folder, render=True, accept_all=False)
            self.assertTrue(result)
            mock_render.assert_called_once_with(folder)

    def test_run_merge_in_dir_missing_file_returns_false(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text("{}", encoding="utf-8")
            # missing skills.json and categories.json

            result = run_merge_in_dir(folder, render=False, accept_all=False)
            self.assertFalse(result)

    def test_run_merge_in_dir_single_skill_returns_true_without_merge(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            jobs = {"0": {"index": 0, "role": "R", "employer": "E", "start": "", "end": "", "Description": "", "skillIDs": ["py"]}}
            skills = {"py": {"name": "Python", "url": "", "img": "", "categoryIDs": [], "jobIDs": [0]}}
            categories = {}
            (folder / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
            (folder / "skills.json").write_text(json.dumps(skills), encoding="utf-8")
            (folder / "categories.json").write_text(json.dumps(categories), encoding="utf-8")

            with patch("resume_parser.run_merge_on_parsed.run_merge_interactive") as mock_merge:
                result = run_merge_in_dir(folder, render=False, accept_all=False)
            self.assertTrue(result)
            mock_merge.assert_not_called()

    def test_replaces_merged_terms_in_job_descriptions(self):
        """
        After a merge, job descriptions must swap source terms with the merged term
        using the bracket convention: source -> [final merged term].
        """
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            jobs = {
                "0": {
                    "index": 0,
                    "role": "R",
                    "employer": "E",
                    "start": "",
                    "end": "",
                    "Description": "Used [K-means] and also K-means in the workflow.",
                    "skillIDs": ["k-means", "other"],
                }
            }
            skills = {
                "k-means": {"name": "K-means", "url": "", "img": "", "categoryIDs": [], "jobIDs": [0]},
                "other": {"name": "Other", "url": "", "img": "", "categoryIDs": [], "jobIDs": [0]},
            }
            categories = {}

            (folder / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
            (folder / "skills.json").write_text(json.dumps(skills), encoding="utf-8")
            (folder / "categories.json").write_text(json.dumps(categories), encoding="utf-8")

            with patch(
                "resume_parser.run_merge_on_parsed.run_merge_interactive",
                return_value=[(["K-means"], "K-means clustering")],
            ):
                result = run_merge_in_dir(folder, render=False, accept_all=False)

            self.assertTrue(result)
            updated = json.loads((folder / "jobs.json").read_text(encoding="utf-8"))
            desc = updated["0"]["Description"]
            self.assertIn("[K-means clustering]", desc)
            self.assertNotIn("[K-means]", desc)
            self.assertNotIn(" K-means ", desc)

    def test_reconcile_only_infers_replacements_from_skills(self):
        """
        Pre-existing merged folder:
        - skills.json contains only the final merged term
        - jobs.json may still mention the older source term
        reconcile_job_descriptions_in_dir should replace '[source]' and unbracketed 'source'.
        """
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            jobs = {
                "0": {
                    "index": 0,
                    "role": "R",
                    "employer": "E",
                    "start": "",
                    "end": "",
                    "Description": "Used [K-means] and also K-means in the workflow.",
                    "skillIDs": ["k-means-clustering"],
                }
            }
            skills = {
                "k-means-clustering": {
                    "name": "K-means clustering",
                    "url": "",
                    "img": "",
                    "categoryIDs": [],
                    "jobIDs": [0],
                }
            }
            (folder / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
            (folder / "skills.json").write_text(json.dumps(skills), encoding="utf-8")
            (folder / "categories.json").write_text(json.dumps({}), encoding="utf-8")

            ok = reconcile_job_descriptions_in_dir(folder, render=False)
            self.assertTrue(ok)
            updated = json.loads((folder / "jobs.json").read_text(encoding="utf-8"))
            desc = updated["0"]["Description"]
            self.assertIn("[K-means clustering]", desc)
            self.assertNotIn("[K-means]", desc)
            self.assertNotIn(" K-means ", desc)


class TestMain(unittest.TestCase):
    def test_main_nonexistent_path_returns_1(self):
        with patch("resume_parser.run_merge_on_parsed._require_llm_api_key"):
            with patch.object(sys, "argv", ["run-merge-on-parsed", "/nonexistent/path"]):
                with patch("sys.stderr"):
                    result = main()
        self.assertEqual(result, 1)

    def test_main_valid_single_folder_returns_0(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "jobs.json").write_text(json.dumps({"0": {"index": 0, "role": "R", "employer": "E", "start": "", "end": "", "Description": "", "skillIDs": []}}), encoding="utf-8")
            (folder / "skills.json").write_text(json.dumps({"a": {"name": "A", "url": "", "img": "", "categoryIDs": [], "jobIDs": [0]}, "b": {"name": "B", "url": "", "img": "", "categoryIDs": [], "jobIDs": []}}), encoding="utf-8")
            (folder / "categories.json").write_text(json.dumps({}), encoding="utf-8")

            with patch("resume_parser.run_merge_on_parsed._require_llm_api_key"):
                with patch("resume_parser.run_merge_on_parsed.run_merge_in_dir", return_value=True):
                    with patch.object(sys, "argv", ["run-merge-on-parsed", str(folder)]):
                        result = main()
        self.assertEqual(result, 0)

    def test_main_all_with_no_subdirs_returns_1(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            with patch("resume_parser.run_merge_on_parsed._require_llm_api_key"):
                with patch.object(sys, "argv", ["run-merge-on-parsed", str(path), "--all"]):
                    with patch("sys.stderr"):
                        result = main()
        self.assertEqual(result, 1)

    def test_main_not_parsed_folder_returns_1(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            # No skills.json
            with patch("resume_parser.run_merge_on_parsed._require_llm_api_key"):
                with patch.object(sys, "argv", ["run-merge-on-parsed", str(path)]):
                    with patch("sys.stderr"):
                        result = main()
        self.assertEqual(result, 1)
