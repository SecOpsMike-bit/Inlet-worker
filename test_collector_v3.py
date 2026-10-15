"""Regression tests for the isolated v3 collector. Run: python -m unittest test_collector_v3.py"""
import tempfile
import unittest
from pathlib import Path
from collector_v3 import collect_batch, save_staging_json


class CollectorV3Tests(unittest.TestCase):
    def setUp(self):
        self.companies = [{"name": "Example Security", "platform": "greenhouse"}]
        self.jobs = [
            {"title": "Senior SOC Analyst", "location": "New York, USA",
             "url": "https://jobs.example.com/1?utm_source=test", "text": "Requires 8 years"},
            {"title": "Junior SOC Analyst", "location": "Toronto",
             "url": "https://jobs.example.com/2", "text": "Entry-level"},
        ]

    def test_preserves_roles_independent_of_matching(self):
        result = collect_batch(self.companies, lambda _: self.jobs, collected_at="2026-10-14T00:00:00Z")
        self.assertEqual(result["stats"]["unique_postings"], 2)
        self.assertEqual({r["title"] for r in result["postings"]},
                         {"Senior SOC Analyst", "Junior SOC Analyst"})

    def test_deduplicates_tracking_urls(self):
        jobs = self.jobs + [{**self.jobs[0], "url": "https://jobs.example.com/1?ref=other"}]
        result = collect_batch(self.companies, lambda _: jobs)
        self.assertEqual(result["stats"]["raw_postings"], 3)
        self.assertEqual(result["stats"]["unique_postings"], 2)

    def test_failed_feed_does_not_erase_other_jobs(self):
        companies = self.companies + [{"name": "Offline Employer"}]
        def fetch(c):
            if c["name"] == "Offline Employer":
                raise TimeoutError("offline")
            return self.jobs
        result = collect_batch(companies, fetch)
        self.assertEqual(result["stats"]["companies_error"], 1)
        self.assertEqual(result["stats"]["unique_postings"], 2)

    def test_http_failure_records_status_without_exposing_url(self):
        from urllib.error import HTTPError
        def fail(_):
            raise HTTPError("https://example.com/private?token=secret", 404, "Not Found", {}, None)
        result = collect_batch(self.companies, fail)
        error = result["companies"][0]
        self.assertEqual(error["http_status"], 404)
        self.assertNotIn("secret", str(error))

    def test_403_is_access_denied_not_empty(self):
        from urllib.error import HTTPError
        def blocked(_):
            raise HTTPError("https://example.com/jobs", 403, "Forbidden", {}, None)
        result = collect_batch(self.companies, blocked)
        self.assertEqual(result["companies"][0]["failure_category"], "access_denied")
        self.assertEqual(result["stats"]["companies_error"], 1)
        self.assertEqual(result["stats"]["companies_empty"], 0)

    def test_empty_is_not_error(self):
        result = collect_batch(self.companies, lambda _: [])
        self.assertEqual(result["stats"]["companies_empty"], 1)
        self.assertEqual(result["stats"]["companies_error"], 0)

    def test_invalid_posting_is_reported(self):
        result = collect_batch(self.companies, lambda _: [{"title": "SOC Analyst", "url": ""}])
        self.assertEqual(result["stats"]["invalid_postings"], 1)

    def test_staging_output_is_explicit(self):
        result = collect_batch(self.companies, lambda _: self.jobs)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "snapshot.json"
            save_staging_json(result, target)
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
