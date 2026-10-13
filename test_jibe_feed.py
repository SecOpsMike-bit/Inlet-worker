"""Unit tests for the employer-hosted public Kinaxis iCIMS/Jibe feed."""

import unittest
from unittest.mock import patch
import urllib.error

import engine
import jibe_feed


def record(slug, title, city="Toronto", country="Canada", **overrides):
    data = {"slug": slug, "title": title, "city": city,
            "state": "Ontario", "country": country,
            "posted_date": "2026-10-13T21:38:00+0000",
            "description": "<p>SIEM and incident response.</p>",
            "searchable": True, "internal": False}
    data.update(overrides)
    return {"data": data}


class KinaxisJibeTests(unittest.TestCase):
    def test_public_jibe_pages_normalize_and_deduplicate(self):
        pages = {
            1: {"jobs": [
                record("35553", "SOC Analyst"),
                record("35554", "Senior Security Architect", city="", country="United States"),
                record("35555", "Internal", internal=True),
            ], "totalCount": 5},
            2: {"jobs": [
                record("35553", "SOC Analyst"),
                record("35556", "Incident Response Analyst", city="Ottawa"),
            ], "totalCount": 5},
            3: {"jobs": [], "totalCount": 5},
        }
        with patch.object(jibe_feed, "_fetch_page", side_effect=lambda n: pages[n]):
            jobs = jibe_feed.fetch_jibe_kinaxis()
        self.assertEqual(len(jobs), 3)
        self.assertEqual(jobs[0]["location"], "Toronto, Ontario, Canada")
        self.assertEqual(jobs[0]["posted"], "2026-10-13T21:38:00+0000")
        self.assertEqual(jobs[0]["url"], "https://join.kinaxis.com/jobs/35553?lang=en-us")
        self.assertEqual(jobs[0]["text"], "SIEM and incident response.")
        self.assertEqual(jobs[1]["location"], "Ontario, United States")
        self.assertEqual(jobs[2]["location"], "Ottawa, Ontario, Canada")

    def test_cap_and_no_network_for_invalid_response(self):
        with patch.object(jibe_feed, "_fetch_page", return_value={
            "jobs": [record("35553", "SOC Analyst"), record("35554", "Security Analyst")],
            "totalCount": 100,
        }) as fetch:
            jobs = jibe_feed.fetch_jibe_kinaxis(cap=1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(fetch.call_count, 1)
        with patch.object(jibe_feed, "_fetch_page", return_value={"error": "invalid"}):
            with self.assertRaises(ValueError):
                jibe_feed.fetch_jibe_kinaxis()

    def test_failed_kinaxis_feed_not_reported_as_no_vacancies(self):
        with patch.object(engine, "fetch_jibe_kinaxis", side_effect=urllib.error.HTTPError(
            jibe_feed.JOBS_API.format(page=1), 503, "Unavailable", {}, None
        )):
            jobs, diag = engine.pull_company_diagnostic(
                {"name": "Kinaxis", "platform": "jibe"}
            )
        self.assertEqual(jobs, [])
        self.assertEqual(diag["status"], "fetch_error")
        self.assertEqual(diag["http_status"], 503)


if __name__ == "__main__":
    unittest.main()
