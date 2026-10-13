"""Unit tests for employer-feed diagnostics and targeted ATS discovery."""
import urllib.error
import unittest
from unittest.mock import patch

import engine
from shadow_compare_v3 import _directory_company_dict, _v2_decision


class FeedDiagnosticsTests(unittest.TestCase):
    def test_shadow_v2_does_not_count_unrelated_operations_jobs(self):
        job = {"title": "Operations Coordinator", "location": "Toronto, ON",
               "text": "Manage vendor relationships, warehouse operations and supply chain.",
               "posted": "2026-10-12", "url": "https://example.com/ops"}
        decision, score, reason = _v2_decision(job, {"name": "Example", "tier": 2})
        self.assertEqual(decision, "skip")
        self.assertEqual(reason, "off_target_lane")

    def test_shadow_v2_accepts_real_soc_role(self):
        import datetime as dt
        job = {"title": "Junior Security Analyst", "location": "Toronto, ON",
               "text": "Monitor SIEM and EDR security alerts, investigate malware, "
                       "triage incidents, and support incident response. 1 year SOC experience.",
               "posted": dt.date.today().isoformat(), "url": "https://example.com/soc"}
        decision, score, reason = _v2_decision(job, {"name": "Example", "tier": 2})
        self.assertEqual(decision, "keep")
        self.assertGreaterEqual(score, 55)

    def test_explicit_unsupported_provider_is_not_no_vacancies(self):
        jobs, diag = engine.pull_company_diagnostic(
            {"name": "Test Employer", "platform": "dayforce", "slug": "test"}
        )
        self.assertEqual(jobs, [])
        self.assertEqual(diag["status"], "unsupported_platform")

    def test_successfactors_missing_url_is_not_no_vacancies(self):
        jobs, diag = engine.pull_company_diagnostic(
            {"name": "Test Employer", "platform": "successfactors", "slug": "test"}
        )
        self.assertEqual(jobs, [])
        self.assertEqual(diag["status"], "missing_board_url")

    def test_successfactors_feed_reports_actual_results(self):
        sample = [{"title": "Security Analyst", "location": "Toronto, ON",
                   "url": "https://jobs.descartes.com/job/Toronto-Test/12345/",
                   "text": "SOC SIEM EDR incident response", "posted": ""}]
        with patch.object(engine, "fetch_successfactors", return_value=sample):
            jobs, diag = engine.pull_company_diagnostic({
                "name": "Descartes", "platform": "successfactors",
                "board_url": "https://jobs.descartes.com/go/View-All-Jobs/2574817/"
            })
        self.assertEqual(jobs, sample)
        self.assertEqual(diag["status"], "ok")

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
