"""Cyber audit classification must not conflate financial security with cyber."""
import unittest
from audit_cyber_v3 import is_cyber_title, summarize


class CyberAuditTests(unittest.TestCase):
    def test_financial_security_is_not_cyber(self):
        self.assertFalse(is_cyber_title("Estate Planning Associate (Financial Security Advisor)"))

    def test_physical_security_is_not_cyber(self):
        self.assertFalse(is_cyber_title("Physical Security Guard"))

    def test_soc_and_cyber_roles_are_cyber(self):
        for title in ("SOC Analyst I", "Cybersecurity Analyst", "Security Operations Engineer",
                      "Incident Response Analyst", "Threat Detection Analyst"):
            with self.subTest(title=title):
                self.assertTrue(is_cyber_title(title))

    def test_report_keeps_raw_job(self):
        posting = {"source_company": "RBC", "title": "Estate Planning Associate (Financial Security Advisor)",
                   "location": "Montréal, Quebec, Canada"}
        result = summarize([posting])
        self.assertEqual(result["raw_total"], 1)
        self.assertEqual(result["cyber_title_signal"], 0)


if __name__ == "__main__":
    unittest.main()
