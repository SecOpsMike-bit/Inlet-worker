import unittest

import match_v2


class TakeTwoBenchmarkTest(unittest.TestCase):
    def test_take_two_security_operations_engineer(self):
        job = {
            "title": "Security Operations Engineer",
            "location": "Toronto, Ontario, Canada",
            "posted": "2026-09-10",
            "url": "https://example.com/taketwo",
            "text": (
                "Support and maintain a Security Orchestration, Automation, and Response (SOAR) platform. "
                "Work closely with senior and lead engineers. Assist in development, testing, and maintenance of SOAR "
                "playbooks, workflows, integrations, and security automation. Partner with security analysts and document "
                "technical workflows. 1–3 years of experience in a Security Engineering level role; previous SOC analyst "
                "or IT support experience is a strong plus. Exposure to SOAR, SIEM, EDR, threat intelligence, Python and "
                "API integrations. Security+ and CySA+ are great to have. Basic familiarity with MITRE ATT&CK."
            ),
        }
        result = match_v2.explain_cyber_match(job)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["lane"], "Security Operations Engineer")
        self.assertGreaterEqual(result["score"], 70)


if __name__ == "__main__":
    unittest.main()
