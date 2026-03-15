"""Tests for resume_parser.skill_merge module."""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from resume_parser.skill_merge import (
    suggest_skill_merges,
    apply_skill_merge,
    run_merge_interactive,
    _slugify,
)


class TestSuggestSkillMerges(unittest.TestCase):
    def test_raises_when_no_llm_provider(self):
        with patch("resume_parser.skill_merge.get_llm_provider", side_effect=RuntimeError("no key")):
            skills = {
                "Python": {"id": "python", "url": "", "img": "", "jobIDs": [0], "categoryIDs": []},
                "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
            }
            with self.assertRaises(RuntimeError):
                suggest_skill_merges(skills)

    def test_returns_empty_when_less_than_two_skills(self):
        with patch("resume_parser.skill_merge.get_llm_provider", return_value="anthropic"):
            skills = {"Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []}}
            result = suggest_skill_merges(skills)
        self.assertEqual(result, [])

    def test_returns_list_structure_on_llm_success(self):
        llm_response = '{"suggestions": [{"sources": ["Python", "python"], "target": "Python"}]}'
        with patch("resume_parser.skill_merge.get_llm_provider", return_value="anthropic"):
            with patch("resume_parser.skill_merge._call_llm", return_value=llm_response):
                skills = {
                    "Python": {"id": "python", "url": "", "img": "", "jobIDs": [0], "categoryIDs": ["prog"]},
                    "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [1], "categoryIDs": ["prog"]},
                }
                result = suggest_skill_merges(skills)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertIn("sources", result[0])
        self.assertIn("target", result[0])
        # Target "Python" (id "python") is excluded from sources
        self.assertEqual(result[0]["sources"], ["python-1"])
        self.assertEqual(result[0]["target"], "python")

    def test_returns_empty_on_llm_failure(self):
        with patch("resume_parser.skill_merge.get_llm_provider", return_value="anthropic"):
            with patch("resume_parser.skill_merge._call_llm", side_effect=Exception("API error")):
                skills = {
                    "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                    "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                }
                result = suggest_skill_merges(skills)
        self.assertEqual(result, [])

    def test_strips_markdown_from_llm_response(self):
        llm_response = '```json\n{"suggestions": [{"sources": ["Python", "python"], "target": "Python"}]}\n```'
        with patch("resume_parser.skill_merge.get_llm_provider", return_value="anthropic"):
            with patch("resume_parser.skill_merge._call_llm", return_value=llm_response):
                skills = {
                    "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                    "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                }
                result = suggest_skill_merges(skills)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]["target"], "python")

    def test_returns_empty_when_suggestions_not_list(self):
        with patch("resume_parser.skill_merge.get_llm_provider", return_value="anthropic"):
            with patch("resume_parser.skill_merge._call_llm", return_value='{"suggestions": "invalid"}'):
                skills = {
                    "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                    "Java": {"id": "java", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                }
                result = suggest_skill_merges(skills)
        self.assertEqual(result, [])

    def test_target_id_collision_gets_suffix(self):
        """When target name is new but slugifies to existing id, use suffix."""
        # "Python" as target not in skills; slug "python" exists (from "python" skill)
        llm_response = '{"suggestions": [{"sources": ["python", "Python 2"], "target": "Python"}]}'
        with patch("resume_parser.skill_merge.get_llm_provider", return_value="anthropic"):
            with patch("resume_parser.skill_merge._call_llm", return_value=llm_response):
                skills = {
                    "python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                    "Python 2": {"id": "python-2", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                }
                result = suggest_skill_merges(skills)
        self.assertGreater(len(result), 0)
        # Target "Python" slugifies to "python" which exists; collision -> "python-1"
        self.assertEqual(result[0]["target"], "python-1")
        self.assertIn("python", result[0]["sources"])
        self.assertIn("python-2", result[0]["sources"])

    def test_skips_item_with_source_resolved_by_id(self):
        """Source can be resolved by skill id (id_to_name) when not a name."""
        llm_response = '{"suggestions": [{"sources": ["python-1", "Python"], "target": "Python"}]}'
        with patch("resume_parser.skill_merge.get_llm_provider", return_value="anthropic"):
            with patch("resume_parser.skill_merge._call_llm", return_value=llm_response):
                skills = {
                    "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                    "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                }
                result = suggest_skill_merges(skills)
        self.assertGreater(len(result), 0)
        self.assertIn("python-1", result[0]["sources"])

    def test_returns_empty_when_llm_returns_no_suggestions(self):
        with patch("resume_parser.skill_merge.get_llm_provider", return_value="anthropic"):
            with patch("resume_parser.skill_merge._call_llm", return_value='{"suggestions": []}'):
                skills = {
                    "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                    "Java": {"id": "java", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
                }
                result = suggest_skill_merges(skills)
        self.assertEqual(result, [])


class TestApplySkillMerge(unittest.TestCase):
    def test_merges_job_ids_and_category_ids(self):
        skills = {
            "Python": {"id": "python", "url": "", "img": "", "jobIDs": [0], "categoryIDs": ["prog"]},
            "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [1], "categoryIDs": ["lang"]},
        }
        jobs = [{"index": 0}, {"index": 1}]
        categories = {"prog": {"name": "Programming"}, "lang": {"name": "Language"}}
        apply_skill_merge(
            skills, jobs, categories,
            sources=["python-1"],
            target="python",
            target_name="Python",
        )
        self.assertNotIn("python", skills)
        # python-1 should be removed; Python should have merged jobIDs
        self.assertIn("Python", skills)
        self.assertEqual(set(skills["Python"]["jobIDs"]), {0, 1})
        self.assertEqual(set(skills["Python"]["categoryIDs"]), {"lang", "prog"})

    def test_removes_sources_from_skills(self):
        skills = {
            "A": {"id": "a", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
            "B": {"id": "b", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        apply_skill_merge(skills, jobs, categories, sources=["b"], target="a", target_name="A")
        self.assertIn("A", skills)
        self.assertNotIn("B", skills)

    def test_creates_new_target_when_target_not_in_skills(self):
        skills = {
            "JS": {"id": "js", "url": "", "img": "", "jobIDs": [0], "categoryIDs": []},
            "JavaScript": {"id": "javascript", "url": "https://js.org", "img": "", "jobIDs": [1], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        apply_skill_merge(
            skills, jobs, categories,
            sources=["js", "javascript"],
            target="javascript",
            target_name="JavaScript",
        )
        self.assertIn("JavaScript", skills)
        self.assertNotIn("JS", skills)
        self.assertEqual(set(skills["JavaScript"]["jobIDs"]), {0, 1})
        self.assertEqual(skills["JavaScript"]["url"], "https://js.org")

    def test_prefers_non_empty_url_from_sources(self):
        skills = {
            "Python": {"id": "python", "url": "https://python.org", "img": "", "jobIDs": [], "categoryIDs": []},
            "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        apply_skill_merge(skills, jobs, categories, sources=["python-1"], target="python", target_name="Python")
        self.assertEqual(skills["Python"]["url"], "https://python.org")

    def test_merge_adds_img_from_source(self):
        skills = {
            "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
            "python": {"id": "python-1", "url": "", "img": "python.svg", "jobIDs": [], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        apply_skill_merge(skills, jobs, categories, sources=["python-1"], target="python", target_name="Python")
        self.assertEqual(skills["Python"]["img"], "python.svg")

    def test_apply_merge_target_exists_by_id_different_key(self):
        """Target skill exists (found by id), merge from sources."""
        skills = {
            "A": {"id": "a", "url": "", "img": "", "jobIDs": [0], "categoryIDs": []},
            "B": {"id": "b", "url": "", "img": "", "jobIDs": [1], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        apply_skill_merge(skills, jobs, categories, sources=["b"], target="a", target_name="CanonicalA")
        self.assertIn("A", skills)
        self.assertNotIn("B", skills)
        self.assertEqual(set(skills["A"]["jobIDs"]), {0, 1})


class TestSlugify(unittest.TestCase):
    def test_slugify_normalizes_string(self):
        self.assertEqual(_slugify("Python 3"), "python-3")
        self.assertEqual(_slugify("C++"), "c")
        self.assertEqual(_slugify(""), "skill")
        self.assertEqual(_slugify("  foo bar  "), "foo-bar")


class TestRunMergeInteractive(unittest.TestCase):
    def test_does_nothing_when_no_suggestions(self):
        skills = {
            "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
            "Java": {"id": "java", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        with patch("resume_parser.skill_merge.suggest_skill_merges", return_value=[]):
            run_merge_interactive(skills, jobs, categories)
        self.assertEqual(len(skills), 2)

    def test_applies_merge_when_user_accepts(self):
        skills = {
            "Python": {"id": "python", "url": "", "img": "", "jobIDs": [0], "categoryIDs": []},
            "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [1], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        suggestions = [{"sources": ["python-1"], "target": "python", "target_name": "Python"}]
        with patch("resume_parser.skill_merge.suggest_skill_merges", return_value=suggestions):
            with patch("builtins.input", return_value="y"):
                run_merge_interactive(skills, jobs, categories)
        self.assertNotIn("python", skills)
        self.assertIn("Python", skills)
        self.assertEqual(set(skills["Python"]["jobIDs"]), {0, 1})

    def test_skips_merge_when_user_says_n(self):
        skills = {
            "Python": {"id": "python", "url": "", "img": "", "jobIDs": [0], "categoryIDs": []},
            "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [1], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        suggestions = [{"sources": ["python-1"], "target": "python", "target_name": "Python"}]
        with patch("resume_parser.skill_merge.suggest_skill_merges", return_value=suggestions):
            with patch("builtins.input", return_value="n"):
                run_merge_interactive(skills, jobs, categories)
        self.assertIn("Python", skills)
        self.assertIn("python", skills)

    def test_accept_all_applies_remaining_merges(self):
        skills = {
            "A": {"id": "a", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
            "B": {"id": "b", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
            "C": {"id": "c", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        suggestions = [
            {"sources": ["b"], "target": "a", "target_name": "A"},
            {"sources": ["c"], "target": "a", "target_name": "A"},
        ]
        with patch("resume_parser.skill_merge.suggest_skill_merges", return_value=suggestions):
            with patch("builtins.input", return_value="a"):  # accept all
                run_merge_interactive(skills, jobs, categories)
        self.assertIn("A", skills)
        self.assertNotIn("B", skills)
        self.assertNotIn("C", skills)

    def test_quit_stops_prompting(self):
        skills = {
            "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
            "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        suggestions = [{"sources": ["python-1"], "target": "python", "target_name": "Python"}]
        with patch("resume_parser.skill_merge.suggest_skill_merges", return_value=suggestions):
            with patch("builtins.input", return_value="q"):
                run_merge_interactive(skills, jobs, categories)
        self.assertIn("python", skills)
        self.assertIn("Python", skills)

    def test_eoferror_stops_prompting(self):
        skills = {
            "Python": {"id": "python", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
            "python": {"id": "python-1", "url": "", "img": "", "jobIDs": [], "categoryIDs": []},
        }
        jobs = []
        categories = {}
        suggestions = [{"sources": ["python-1"], "target": "python", "target_name": "Python"}]
        with patch("resume_parser.skill_merge.suggest_skill_merges", return_value=suggestions):
            with patch("builtins.input", side_effect=EOFError()):
                run_merge_interactive(skills, jobs, categories)
        self.assertIn("python", skills)
