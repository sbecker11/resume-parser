"""
Tests for the resume-parser pipeline: extractors and parsers (no LLM calls).
Run from repo root: python -m unittest discover -s tests
"""
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from resume_parser.extractors import extract_text
from resume_parser.parsers import (
    extract_skills_from_text,
    expand_skill_parens,
    expand_parens_in_text,
    get_llm_provider,
    jobs_to_json_format,
    enrich_skills_with_llm,
    categorize_skills_with_llm,
    build_categories_dict,
    assign_skill_ids,
    parse_jobs_with_llm,
    parse_resume_sections,
    _hex_to_rgb,
    _css_name_from_hex,
    _normalize_date,
    _normalize_end_date,
    _looks_like_education_job,
)


class TestExtractSkillsFromText(unittest.TestCase):
    """Test parsers.extract_skills_from_text (pure function, no LLM)."""

    def test_empty_string(self):
        self.assertEqual(extract_skills_from_text(""), {})

    def test_no_brackets(self):
        self.assertEqual(extract_skills_from_text("Python and Java"), {})

    def test_simple_skill(self):
        self.assertEqual(
            extract_skills_from_text("Used [Python] for scripting."),
            {"Python": {"url": "", "img": ""}},
        )

    def test_skill_with_url(self):
        self.assertEqual(
            extract_skills_from_text("See [Pandas](https://pandas.pydata.org) for docs."),
            {"Pandas": {"url": "https://pandas.pydata.org", "img": ""}},
        )

    def test_skill_with_img_and_url(self):
        self.assertEqual(
            extract_skills_from_text("Used [React]{react.svg}(https://react.dev)"),
            {"React": {"url": "https://react.dev", "img": "react.svg"}},
        )

    def test_multiple_skills_merged(self):
        text = "Worked with [AWS] and [AWS] S3. [AWS](https://aws.amazon.com) is great."
        result = extract_skills_from_text(text)
        self.assertIn("AWS", result)
        self.assertEqual(result["AWS"]["url"], "https://aws.amazon.com")

    def test_preserves_first_url(self):
        text = "[Python](https://first.com) and [Python](https://second.com)"
        result = extract_skills_from_text(text)
        self.assertEqual(result["Python"]["url"], "https://first.com")

    def test_paren_skill_expanded(self):
        text = "Used [AWS (S3, EC2, Lambda)](https://aws.amazon.com) for infra."
        result = extract_skills_from_text(text)
        self.assertIn("AWS S3", result)
        self.assertIn("AWS EC2", result)
        self.assertIn("AWS Lambda", result)
        self.assertEqual(result["AWS S3"]["url"], "https://aws.amazon.com")
        self.assertEqual(len(result), 3)


class TestExpandSkillParens(unittest.TestCase):
    """Test parsers.expand_skill_parens."""

    def test_no_parens_returns_single(self):
        self.assertEqual(expand_skill_parens("Python"), ["Python"])

    def test_parens_expanded(self):
        self.assertEqual(
            expand_skill_parens("AWS (S3, EC2, Lambda, Glue)"),
            ["AWS S3", "AWS EC2", "AWS Lambda", "AWS Glue"],
        )

    def test_empty_or_whitespace(self):
        self.assertEqual(expand_skill_parens(""), [])
        self.assertEqual(expand_skill_parens("   "), [])

    def test_single_item_in_parens(self):
        self.assertEqual(expand_skill_parens("Cloud (GCP)"), ["Cloud GCP"])

    def test_no_space_and_spaced_return_same_set(self):
        """Name(a,b,c) and Name (a, b, c) should return the same set of pairs."""
        no_space = set(expand_skill_parens("Name(a,b,c)"))
        spaced = set(expand_skill_parens("Name (a, b, c)"))
        self.assertEqual(no_space, spaced)
        self.assertEqual(no_space, {"Name a", "Name b", "Name c"})


class TestExpandParensInText(unittest.TestCase):
    """Test parsers.expand_parens_in_text (in-description replacement)."""

    def test_replaces_parens_with_comma_separated(self):
        self.assertEqual(
            expand_parens_in_text("Used AWS (S3, EC2, Lambda) for infra."),
            "Used AWS S3, AWS EC2, AWS Lambda for infra.",
        )

    def test_empty_unchanged(self):
        self.assertEqual(expand_parens_in_text(""), "")
        self.assertEqual(expand_parens_in_text("   "), "   ")

    def test_no_parens_unchanged(self):
        self.assertEqual(expand_parens_in_text("Just Python and Java."), "Just Python and Java.")

    def test_no_space_after_name_expands_same_as_spaced(self):
        """Name(a,b,c) and Name (a, b, c) in text both expand to Name a, Name b, Name c."""
        no_space = expand_parens_in_text("Used Name(a,b,c) here.")
        spaced = expand_parens_in_text("Used Name (a, b, c) here.")
        self.assertEqual(no_space, "Used Name a, Name b, Name c here.")
        self.assertEqual(spaced, "Used Name a, Name b, Name c here.")
        self.assertEqual(no_space, spaced)

    def test_prefix_with_slash_expands(self):
        """CI/CD (GitHub Actions, Jenkins) expands to CI/CD GitHub Actions, CI/CD Jenkins."""
        result = expand_parens_in_text("Used CI/CD (GitHub Actions, Jenkins) for pipelines.")
        self.assertEqual(result, "Used CI/CD GitHub Actions, CI/CD Jenkins for pipelines.")
        self.assertEqual(expand_skill_parens("CI/CD (GitHub Actions, Jenkins)"), ["CI/CD GitHub Actions", "CI/CD Jenkins"])


class TestGetLlmProvider(unittest.TestCase):
    """Test parsers.get_llm_provider with patched env (no real API key)."""

    def test_returns_anthropic_when_key_set(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False):
            self.assertEqual(get_llm_provider(), "anthropic")

    def test_raises_when_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                get_llm_provider()
            self.assertIn("ANTHROPIC_API_KEY", str(ctx.exception))
            self.assertIn("LLM_PROVIDER", str(ctx.exception))

    def test_llm_provider_anthropic_requires_key(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                get_llm_provider()
            self.assertIn("ANTHROPIC_API_KEY", str(ctx.exception))

    def test_llm_provider_anthropic_with_key(self):
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-ant-test"},
            clear=True,
        ):
            self.assertEqual(get_llm_provider(), "anthropic")


class TestExtractText(unittest.TestCase):
    """Test extractors.extract_text with mocked docx/pdf (no real files)."""

    def test_unsupported_format_raises(self):
        with self.assertRaises(ValueError) as ctx:
            extract_text(Path("/fake/resume.txt"))
        self.assertIn("Unsupported", str(ctx.exception))

    @patch("resume_parser.extractors._extract_docx")
    def test_docx_calls_extract_docx(self, mock_extract):
        mock_extract.return_value = "Resume text here"
        result = extract_text(Path("/fake/resume.docx"))
        self.assertEqual(result, "Resume text here")
        mock_extract.assert_called_once()

    @patch("resume_parser.extractors._extract_pdf")
    def test_pdf_calls_extract_pdf(self, mock_extract):
        mock_extract.return_value = "PDF content here"
        result = extract_text(Path("/fake/resume.pdf"))
        self.assertEqual(result, "PDF content here")
        mock_extract.assert_called_once()


class TestExtractDocxBody(unittest.TestCase):
    """Test extractors._extract_docx body (mocked Document)."""

    @patch("docx.Document")
    def test_extract_docx_paragraphs_and_tables(self, mock_document_cls):
        mock_para = MagicMock()
        mock_para.text = "  Hello World  "
        mock_para2 = MagicMock()
        mock_para2.text = "Section two"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para, mock_para2]
        mock_row = MagicMock()
        mock_row.cells = [MagicMock(text="A"), MagicMock(text="B")]
        mock_table = MagicMock()
        mock_table.rows = [mock_row]
        mock_doc.tables = [mock_table]
        mock_document_cls.return_value = mock_doc

        from extractors import _extract_docx
        result = _extract_docx(Path("/fake/file.docx"))
        self.assertIn("Hello World", result)
        self.assertIn("Section two", result)
        self.assertIn("A | B", result)
        mock_document_cls.assert_called_once_with(Path("/fake/file.docx"))

    @patch("docx.Document")
    def test_extract_docx_skips_empty_paragraphs(self, mock_document_cls):
        mock_doc = MagicMock()
        mock_doc.paragraphs = [MagicMock(text="  "), MagicMock(text="Ok")]
        mock_doc.tables = []
        mock_document_cls.return_value = mock_doc
        from extractors import _extract_docx
        result = _extract_docx(Path("/fake/file.docx"))
        self.assertEqual(result, "Ok")


class TestExtractPdfBody(unittest.TestCase):
    """Test extractors._extract_pdf body (mocked pdfplumber)."""

    def test_extract_pdf_pages(self):
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page one text"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page two"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_pdf
        mock_open.return_value.__exit__.return_value = None
        mock_pdfplumber = MagicMock()
        mock_pdfplumber.open = mock_open
        with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
            from extractors import _extract_pdf
            result = _extract_pdf(Path("/fake/file.pdf"))
        self.assertIn("Page one text", result)
        self.assertIn("Page two", result)

    def test_extract_pdf_skips_none_text(self):
        mock_pdf = MagicMock()
        mock_pdf.pages = [
            MagicMock(extract_text=MagicMock(return_value=None)),
            MagicMock(extract_text=MagicMock(return_value="Only this")),
        ]
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_pdf
        mock_open.return_value.__exit__.return_value = None
        mock_pdfplumber = MagicMock()
        mock_pdfplumber.open = mock_open
        with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
            from extractors import _extract_pdf
            result = _extract_pdf(Path("/fake/file.pdf"))
        self.assertEqual(result, "Only this")


class TestHexToRgb(unittest.TestCase):
    """Test parsers._hex_to_rgb."""

    def test_hex_to_rgb(self):
        self.assertEqual(_hex_to_rgb("#ff0000"), (255, 0, 0))
        self.assertEqual(_hex_to_rgb("#00FF00"), (0, 255, 0))
        self.assertEqual(_hex_to_rgb("116611"), (17, 102, 17))


class TestCssNameFromHex(unittest.TestCase):
    """Test parsers._css_name_from_hex."""

    def test_mapped_colors(self):
        self.assertEqual(_css_name_from_hex("#116611"), "darkforest")
        self.assertEqual(_css_name_from_hex("#0069AC"), "darkcyan")
        self.assertEqual(_css_name_from_hex("#ffa500"), "orange")

    def test_unmapped_returns_darkgreen(self):
        self.assertEqual(_css_name_from_hex("#abcdef"), "darkgreen")


class TestNormalizeDate(unittest.TestCase):
    """Test parsers._normalize_date and _normalize_end_date."""

    def test_normalize_date_empty_none(self):
        self.assertEqual(_normalize_date(None), "")
        self.assertEqual(_normalize_date(""), "")

    def test_normalize_date_current_date(self):
        self.assertEqual(_normalize_date("CURRENT_DATE"), "CURRENT_DATE")
        self.assertEqual(_normalize_date("  current_date  "), "CURRENT_DATE")

    def test_normalize_date_iso(self):
        self.assertEqual(_normalize_date("2024-08-01"), "2024-08-01")
        self.assertEqual(_normalize_date("2024-08-01T00:00:00"), "2024-08-01")

    def test_normalize_date_passthrough(self):
        self.assertEqual(_normalize_date("Aug 2024"), "Aug 2024")
        self.assertEqual(_normalize_date("2020"), "2020")

    def test_normalize_end_date_present_current(self):
        self.assertEqual(_normalize_end_date("PRESENT"), "CURRENT_DATE")
        self.assertEqual(_normalize_end_date("Current"), "CURRENT_DATE")
        self.assertEqual(_normalize_end_date("CURRENT"), "CURRENT_DATE")

    def test_normalize_end_date_iso(self):
        self.assertEqual(_normalize_end_date("2023-12-31"), "2023-12-31")


class TestJobsToFlyerFormat(unittest.TestCase):
    """Test parsers.jobs_to_json_format."""

    def test_empty_list(self):
        self.assertEqual(jobs_to_json_format([]), [])

    def test_single_job(self):
        jobs = [{"role": "Engineer", "employer": "Acme", "start": "2020-01-01", "end": "CURRENT_DATE", "description": "Did stuff."}]
        out = jobs_to_json_format(jobs)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["index"], 0)
        self.assertEqual(out[0]["role"], "Engineer")
        self.assertEqual(out[0]["employer"], "Acme")
        self.assertEqual(out[0]["start"], "2020-01-01")
        self.assertEqual(out[0]["end"], "CURRENT_DATE")
        self.assertEqual(out[0]["Description"], "Did stuff.")
        self.assertIn(out[0]["css name"], ("darkforest", "darkgreen"))
        self.assertEqual(out[0]["z-index"], 1)

    def test_multiple_jobs_rotation(self):
        jobs = [{"role": "A", "employer": "E1", "start": "", "end": "", "description": ""}] * 2
        out = jobs_to_json_format(jobs)
        self.assertEqual(out[0]["z-index"], 1)
        self.assertEqual(out[1]["z-index"], 2)

    def test_description_expands_parens(self):
        # Expansion is done before jobs_to_json_format (e.g. in resume_to_json)
        jobs = [{"role": "Dev", "employer": "Co", "start": "", "end": "", "description": "Used AWS (S3, EC2, Lambda) for infra."}]
        for job in jobs:
            job["description"] = expand_parens_in_text((job.get("description") or "").strip())
        out = jobs_to_json_format(jobs)
        self.assertEqual(out[0]["Description"], "Used AWS S3, AWS EC2, AWS Lambda for infra.")


class TestParseJobsWithLlm(unittest.TestCase):
    """Test parsers.parse_jobs_with_llm with mocked _call_llm."""

    @patch("resume_parser.parsers._call_llm")
    def test_returns_jobs_from_json(self, mock_call_llm):
        mock_call_llm.return_value = '{"jobs": [{"role": "Dev", "employer": "Co", "start": "2022-01-01", "end": "CURRENT_DATE", "description": "Work"}]}'
        result = parse_jobs_with_llm("resume text")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "Dev")
        self.assertEqual(result[0]["employer"], "Co")

    @patch("resume_parser.parsers._call_llm")
    def test_strips_markdown_code_blocks(self, mock_call_llm):
        mock_call_llm.return_value = '```json\n{"jobs": [{"role": "R", "employer": "E", "start": "", "end": "", "description": ""}]}\n```'
        result = parse_jobs_with_llm("x")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "R")

    @patch("resume_parser.parsers._call_llm")
    def test_empty_jobs_key_returns_empty_list(self, mock_call_llm):
        mock_call_llm.return_value = "{}"
        result = parse_jobs_with_llm("x")
        self.assertEqual(result, [])

    @patch("resume_parser.parsers._call_llm")
    def test_tolerates_trailing_comma_in_llm_json(self, mock_call_llm):
        mock_call_llm.return_value = '{"jobs": [{"role": "R", "employer": "E", "start": "", "end": "", "description": ""},]}'
        result = parse_jobs_with_llm("x")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "R")

    @patch("resume_parser.parsers._call_llm")
    def test_extracts_json_object_from_wrapped_text(self, mock_call_llm):
        mock_call_llm.return_value = 'Here is the JSON:\n{"jobs": [{"role": "R", "employer": "E", "start": "", "end": "", "description": ""}]}\nHope that helps.'
        result = parse_jobs_with_llm("x")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "R")

    @patch("resume_parser.parsers._call_llm")
    def test_adds_education_from_text_when_llm_misses_it(self, mock_call_llm):
        mock_call_llm.return_value = '{"jobs": [{"role": "Engineer", "employer": "Acme", "start": "2022-01-01", "end": "CURRENT_DATE", "description": "Work"}]}'
        raw_text = (
            "EXPERIENCE\n"
            "Engineer at Acme\n\n"
            "EDUCATION\n"
            "University of Example\n"
            "B.S. Computer Science\n"
            "2016 - 2020\n"
        )
        result = parse_jobs_with_llm(raw_text)
        self.assertTrue(any("University of Example" in (j.get("employer") or "") for j in result))
        edu = [j for j in result if "University of Example" in (j.get("employer") or "")]
        self.assertEqual(edu[0]["role"], "B.S. Computer Science")
        self.assertEqual(edu[0]["start"], "2016-01-01")
        self.assertEqual(edu[0]["end"], "2020-12-31")

    @patch("resume_parser.parsers._call_llm")
    def test_does_not_duplicate_when_llm_already_has_education(self, mock_call_llm):
        mock_call_llm.return_value = (
            '{"jobs": ['
            '{"role": "Engineer", "employer": "Acme", "start": "2022-01-01", "end": "CURRENT_DATE", "description": "Work"},'
            '{"role": "B.S. Computer Science", "employer": "University of Example", "start": "2016-01-01", "end": "2020-12-31", "description": ""}'
            ']}'
        )
        raw_text = (
            "EDUCATION\n"
            "University of Example\n"
            "B.S. Computer Science\n"
            "2016 - 2020\n"
        )
        result = parse_jobs_with_llm(raw_text)
        edu = [j for j in result if "University of Example" in (j.get("employer") or "")]
        self.assertEqual(len(edu), 1)

    @patch("resume_parser.parsers._call_llm")
    def test_education_fallback_without_legitimate_degree_treated_as_job(self, mock_call_llm):
        mock_call_llm.return_value = '{"jobs": [{"role": "Engineer", "employer": "Acme", "start": "2022-01-01", "end": "CURRENT_DATE", "description": "Work"}]}'
        raw_text = (
            "EXPERIENCE\n"
            "Engineer at Acme\n\n"
            "EDUCATION\n"
            "University of Example\n"
            "Resident Assistant\n"
            "2016 - 2020\n"
        )
        result = parse_jobs_with_llm(raw_text)

        # The fallback should produce a job-like entry, not an education entry.
        self.assertTrue(
            any(
                j.get("employer") == "University of Example"
                and j.get("role") == "Resident Assistant"
                for j in result
            )
        )
        self.assertFalse(any(j.get("role") == "Education" for j in result))


class TestEducationDetectionRules(unittest.TestCase):
    def test_requires_legitimate_degree_not_university_role(self):
        self.assertFalse(
            _looks_like_education_job(
                {"role": "Resident Assistant", "employer": "University of Example"}
            )
        )
        self.assertFalse(
            _looks_like_education_job(
                {"role": "Research Assistant", "employer": "University of Example"}
            )
        )
        self.assertTrue(
            _looks_like_education_job(
                {"role": "M.S. Data Science", "employer": "University of Example"}
            )
        )


class TestParseResumeSections(unittest.TestCase):
    """Test parsers.parse_resume_sections with mocked _call_llm."""

    @patch("resume_parser.parsers._call_llm")
    def test_returns_normalized_dict(self, mock_call_llm):
        mock_call_llm.return_value = '''{
          "contact": { "name": "Jane", "email": "j@example.com", "phone": "", "location": "", "linkedin": "", "website": "" },
          "title": "Data Engineer",
          "summary": "Data engineer.",
          "certifications": [ { "name": "AWS CPA", "issuer": "AWS", "date": "2023" } ],
          "skills": [ "Python", "SQL" ],
          "other_sections": [ { "title": "Publications", "content": "Paper 1." } ]
        }'''
        result = parse_resume_sections("resume text")
        self.assertEqual(result["contact"]["name"], "Jane")
        self.assertEqual(result["contact"]["email"], "j@example.com")
        self.assertEqual(result["title"], "Data Engineer")
        self.assertEqual(result["summary"], "Data engineer.")
        self.assertEqual(len(result["certifications"]), 1)
        self.assertEqual(result["certifications"][0]["name"], "AWS CPA")
        self.assertEqual(result["skills"], ["Python", "SQL"])
        self.assertEqual(len(result["other_sections"]), 1)
        self.assertEqual(result["other_sections"][0]["title"], "Publications")

    @patch("resume_parser.parsers._call_llm")
    def test_strips_markdown_and_normalizes_missing_keys(self, mock_call_llm):
        mock_call_llm.return_value = '```json\n{"contact": {}, "summary": "Hi"}\n```'
        result = parse_resume_sections("x")
        self.assertEqual(result["summary"], "Hi")
        self.assertEqual(result["title"], "")
        self.assertEqual(result["certifications"], [])
        self.assertEqual(result["skills"], [])
        self.assertEqual(result["other_sections"], [])


class TestEnrichSkillsWithLlm(unittest.TestCase):
    """Test parsers.enrich_skills_with_llm with mocked LLM."""

    def test_returns_unchanged_when_no_provider(self):
        with patch("resume_parser.parsers._llm_provider") as mock_provider:
            mock_provider.side_effect = RuntimeError("no key")
            skills = {"Python": {"url": "", "img": ""}}
            result = enrich_skills_with_llm(skills)
            self.assertEqual(result, skills)

    def test_returns_unchanged_when_no_skills_need_url(self):
        with patch("resume_parser.parsers._llm_provider"), patch("resume_parser.parsers._call_llm") as mock_call:
            skills = {"Python": {"url": "https://python.org", "img": ""}}
            result = enrich_skills_with_llm(skills)
            mock_call.assert_not_called()
            self.assertEqual(result, skills)

    @patch("resume_parser.parsers._call_llm")
    def test_updates_url_from_suggestions(self, mock_call_llm):
        with patch("resume_parser.parsers._llm_provider"):
            mock_call_llm.return_value = '{"suggestions": [{"name": "Python", "url": "https://python.org"}]}'
            skills = {"Python": {"url": "", "img": ""}}
            result = enrich_skills_with_llm(skills)
            self.assertEqual(result["Python"]["url"], "https://python.org")

    @patch("resume_parser.parsers._call_llm")
    def test_keeps_skills_on_llm_failure(self, mock_call_llm):
        with patch("resume_parser.parsers._llm_provider"):
            mock_call_llm.side_effect = Exception("API error")
            skills = {"X": {"url": "", "img": ""}}
            result = enrich_skills_with_llm(skills)
            self.assertEqual(result["X"]["url"], "")


class TestCategorizeSkillsWithLlm(unittest.TestCase):
    """Test parsers.categorize_skills_with_llm with mocked LLM."""

    def test_adds_empty_categories_when_no_provider(self):
        with patch("resume_parser.parsers._llm_provider") as mock_provider:
            mock_provider.side_effect = RuntimeError("no key")
            skills = {"Python": {"url": "", "img": ""}}
            result = categorize_skills_with_llm(skills)
            self.assertEqual(result["Python"]["categories"], [])

    @patch("resume_parser.parsers._call_llm")
    def test_assigns_categories_from_llm(self, mock_call_llm):
        with patch("resume_parser.parsers._llm_provider"):
            mock_call_llm.return_value = '{"categories": {"Python": ["Programming Language"], "React": ["Framework", "Frontend"]}}'
            skills = {"Python": {"url": "", "img": ""}, "React": {"url": "", "img": ""}}
            result = categorize_skills_with_llm(skills)
            self.assertEqual(result["Python"]["categories"], ["Programming Language"])
            self.assertEqual(result["React"]["categories"], ["Framework", "Frontend"])

    @patch("resume_parser.parsers._call_llm")
    def test_uses_empty_list_on_llm_failure(self, mock_call_llm):
        with patch("resume_parser.parsers._llm_provider"):
            mock_call_llm.side_effect = Exception("API error")
            skills = {"X": {"url": "", "img": ""}}
            result = categorize_skills_with_llm(skills)
            self.assertEqual(result["X"]["categories"], [])


class TestBuildCategoriesDict(unittest.TestCase):
    """Test parsers.build_categories_dict."""

    def test_builds_ids_and_adds_categoryIDs_to_skills(self):
        skills = {
            "Python": {"url": "", "img": "", "categories": ["Programming Language"]},
            "React": {"url": "", "img": "", "categories": ["Framework", "Frontend"]},
            "SQL": {"url": "", "img": "", "categories": ["Programming Language"]},
        }
        categories = build_categories_dict(skills)
        self.assertIn("programming-language", categories)
        self.assertEqual(categories["programming-language"]["name"], "Programming Language")
        self.assertIn("framework", categories)
        self.assertIn("frontend", categories)
        self.assertEqual(skills["Python"]["categoryIDs"], ["programming-language"])
        self.assertEqual(set(skills["React"]["categoryIDs"]), {"framework", "frontend"})
        self.assertEqual(skills["SQL"]["categoryIDs"], ["programming-language"])

    def test_skill_with_no_categories_gets_empty_categoryIDs(self):
        skills = {"X": {"url": "", "img": "", "categories": []}}
        categories = build_categories_dict(skills)
        self.assertEqual(skills["X"]["categoryIDs"], [])
        self.assertEqual(categories, {})


class TestAssignSkillIds(unittest.TestCase):
    """Test parsers.assign_skill_ids."""

    def test_adds_unique_slug_id_to_each_skill(self):
        skills = {
            "Python": {"url": "", "img": "", "jobIDs": [0], "categoryIDs": []},
            "React": {"url": "", "img": "", "jobIDs": [], "categoryIDs": []},
        }
        assign_skill_ids(skills)
        self.assertEqual(skills["Python"]["id"], "python")
        self.assertEqual(skills["React"]["id"], "react")

    def test_collision_gets_suffix(self):
        skills = {
            "react": {"url": "", "img": "", "jobIDs": []},
            "React": {"url": "", "img": "", "jobIDs": []},
        }
        assign_skill_ids(skills)
        ids = [skills["react"]["id"], skills["React"]["id"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("react", ids)
        self.assertTrue(any(s.startswith("react-") for s in ids))


if __name__ == "__main__":
    unittest.main()
