"""Unit tests for employer-feed diagnostics and targeted ATS discovery."""
import urllib.error
import unittest
from unittest.mock import patch

import engine
from shadow_compare_v3 import _directory_company_dict


class FeedDiagnosticsTests(unittest.TestCase):
    def test_explicit_unsupported_provider_is_not_no_vacancies(self):
        for provider in ("dayforce", "successfactors"):
            with self.subTest(provider=provider):
                jobs, diag = engine.pull_company_diagnostic(
                    {"name": "Test Employer", "platform": provider, "slug": "test"}
                )
                self.assertEqual(jobs, [])
                self.assertEqual(diag["status"], "unsupported_platform")

    def test_directory_preserves_known_platform(self):
        company = _directory_company_dict(
            {"name": "eSentire", "tier": 1, "slug": "esentire", "platform": "dayforce"}, 0
        )
        self.assertEqual(company["platform"], "dayforce")

    def test_auto_discovery_reports_failed_attempts(self):
        def bad_fetch(_slug):
            raise urllib.error.HTTPError("https://example.com", 404, "not found", {}, None)

        with patch.object(engine, "_AUTO", [("greenhouse", bad_fetch)]):
            jobs, diag = engine.pull_company_diagnostic(
                {"name": "Example", "slug": "badslug", "platform": "auto"}
            )
        self.assertEqual(jobs, [])
        self.assertEqual(diag["status"], "unresolved_feed")
        self.assertEqual(diag["attempts"][0]["http_status"], 404)

    def test_auto_discovery_success_reports_platform(self):
        job = {"title": "SOC Analyst", "location": "Toronto", "url": "https://example.com/j"}
        with patch.object(engine, "_AUTO", [("lever", lambda slug: [job])]):
            jobs, diag = engine.pull_company_diagnostic(
                {"name": "Example", "slug": "example", "platform": "auto"}
            )
        self.assertEqual(jobs, [job])
        self.assertEqual(diag["status"], "ok")
        self.assertEqual(diag["platform"], "lever")

    def test_workday_zero_results_are_not_reported_as_no_openings(self):
        with patch.object(engine, "fetch_workday", return_value=[]):
            jobs, diag = engine.pull_company_diagnostic({
                "name": "Example", "workday": {"tenant": "example", "pod": "wd5", "site": "External"}
            })
        self.assertEqual(jobs, [])
        self.assertEqual(diag["status"], "empty_or_feed_error")

    def test_workday_prioritizes_soc_queries(self):
        self.assertEqual(engine.WORKDAY_TERMS[0], "soc analyst")
        self.assertLess(engine.WORKDAY_TERMS.index("incident response"),
                        engine.WORKDAY_TERMS.index("security"))


if __name__ == "__main__":
    unittest.main()
