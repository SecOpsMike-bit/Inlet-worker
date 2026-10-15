"""Strict Workday listing behavior regression tests."""
import unittest
from unittest.mock import patch
import workday_v3


class WorkdayV3Tests(unittest.TestCase):
    def test_listing_failure_propagates(self):
        with patch.object(workday_v3.engine, "_post_json", side_effect=TimeoutError("timeout")):
            with self.assertRaises(TimeoutError):
                workday_v3.fetch_workday_strict("tenant", "wd1", "External")

    def test_empty_feed_is_successful(self):
        with patch.object(workday_v3.engine, "_post_json", return_value={"jobPostings": []}):
            self.assertEqual(workday_v3.fetch_workday_strict("tenant", "wd1", "External"), [])

    def test_malformed_response_fails(self):
        with patch.object(workday_v3.engine, "_post_json", return_value={"error": "invalid"}):
            with self.assertRaisesRegex(ValueError, "jobPostings"):
                workday_v3.fetch_workday_strict("tenant", "wd1", "External")

    def test_repeated_search_results_are_deduplicated(self):
        response = {"jobPostings": [{
            "title": "SOC Analyst", "externalPath": "/job/123",
            "locationsText": "Toronto", "postedOn": "Posted Today",
        }]}
        with patch.object(workday_v3.engine, "_post_json", return_value=response), \
             patch.object(workday_v3.engine, "_workday_detail", return_value="SOC monitoring"):
            jobs = workday_v3.fetch_workday_strict("tenant", "wd1", "External")
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["title"], "SOC Analyst")


if __name__ == "__main__":
    unittest.main()
