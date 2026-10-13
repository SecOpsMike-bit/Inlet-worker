"""Separate recency scoring tests from job-fit benchmark fixtures."""
import datetime as dt
import unittest

import match_v2
import match_v3


class RecencyScoringTests(unittest.TestCase):
    def test_v3_recent_and_old_postings_have_different_scores(self):
        recent = (dt.date.today() - dt.timedelta(days=2)).isoformat()
        old = (dt.date.today() - dt.timedelta(days=65)).isoformat()
        recent_score, recent_age = match_v3._opportunity_score(recent)
        old_score, old_age = match_v3._opportunity_score(old)
        self.assertEqual(recent_age, 2)
        self.assertEqual(old_age, 65)
        self.assertGreater(recent_score, old_score)

    def test_v2_age_rejects_old_role_unless_exceptional(self):
        job = {
            "title": "Junior Security Analyst",
            "location": "Canada - Remote",
            "text": "Monitor SIEM and EDR alerts, triage security incidents, "
                    "investigate malware, and escalate incidents. 1 year SOC experience.",
            "posted": (dt.date.today() - dt.timedelta(days=90)).isoformat(),
            "url": "https://example.com/old",
        }
        result = match_v2.explain_cyber_match(job)
        self.assertFalse(result["accepted"])
        self.assertIn(result["reason"], {"older_not_exceptional", "too_old", "stale"})


if __name__ == "__main__":
    unittest.main()
