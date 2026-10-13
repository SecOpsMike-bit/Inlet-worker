"""Offline tests for eSentire's documented anonymous Dayforce JobFeeds API."""
import unittest

from dayforce_feed import fetch_dayforce, parse_jobfeeds


class DayforceJobFeedsTests(unittest.TestCase):
    def setUp(self):
        self.sample = {
            "Title": "Support Center Analyst I",
            "Description": "<p>Monitor SIEM alerts, triage tickets &amp; "
                           "escalate security incidents.</p>",
            "City": "Waterloo", "State": "ON", "Country": "CA",
            "DatePosted": "2026-10-12T00:00:00",
            "JobDetailsUrl":
                "https://jobs.dayforcehcm.com/en-US/esentire/CANDIDATEPORTAL/jobs/5800",
            "ApplyUrl":
                "https://jobs.dayforcehcm.com/en-US/esentire/CANDIDATEPORTAL/jobs/5800/apply",
            "ReferenceNumber": 5800,
        }

    def test_normalizes_canadian_location_description_and_link(self):
        result = parse_jobfeeds([self.sample], "esentire")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["location"], "Waterloo, ON, Canada")
        self.assertEqual(result[0]["posted"], "2026-10-12")
        self.assertIn("tickets & escalate", result[0]["text"])
        self.assertEqual(result[0]["url"], self.sample["JobDetailsUrl"])

    def test_missing_location_is_explicitly_unverified(self):
        row = dict(self.sample, City="", State="", Country="")
        result = parse_jobfeeds([row], "esentire")
        self.assertEqual(result[0]["location"], "Location unverified")

    def test_rejects_external_apply_link_and_uses_official_fallback(self):
        row = dict(self.sample, JobDetailsUrl="https://malicious.example/job/1",
                   ApplyUrl="https://malicious.example/apply")
        result = parse_jobfeeds([row], "esentire")
        self.assertEqual(
            result[0]["url"],
            "https://jobs.dayforcehcm.com/en-US/esentire/CANDIDATEPORTAL/jobs/5800"
        )

    def test_deduplicates_and_limits_results(self):
        second = dict(self.sample, Title="Security Specialist",
                      ReferenceNumber=5807,
                      JobDetailsUrl="https://jobs.dayforcehcm.com/en-US/esentire/CANDIDATEPORTAL/jobs/5807")
        result = parse_jobfeeds([self.sample, self.sample, second], "esentire", cap=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["title"], "Security Specialist")

    def test_rejects_unexpected_feed_shape(self):
        with self.assertRaises(ValueError):
            parse_jobfeeds({"jobPostings": []}, "esentire")

    def test_fetch_uses_anonymous_documented_get_feed(self):
        urls = []
        def get_json(url):
            urls.append(url)
            return [self.sample]
        result = fetch_dayforce("esentire", get_json=get_json)
        self.assertEqual(urls, [
            "https://www.dayforcehcm.com/api/esentire/V1/JobFeeds"
        ])
        self.assertEqual(result[0]["title"], "Support Center Analyst I")

    def test_namespace_validation_prevents_untrusted_hosts(self):
        with self.assertRaises(ValueError):
            fetch_dayforce("esentire/../../foo", get_json=lambda _: [])


if __name__ == "__main__":
    unittest.main()
