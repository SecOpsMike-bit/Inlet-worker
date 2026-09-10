import unittest

import match_v2


class MatchV2Tests(unittest.TestCase):
    def job(self, title, text, location="Toronto, ON", posted="2026-09-10"):
        return {"title": title, "text": text, "location": location,
                "posted": posted, "url": "https://example.com/job"}

    def test_strong_soc_role_is_accepted(self):
        j = self.job(
            "Junior Security Analyst",
            "Monitor security alerts in Microsoft Sentinel and Splunk, investigate phishing and malware, "
            "handle incident response and escalation, manage tickets, support Windows and Linux, and use MITRE ATT&CK. "
            "1 year of SOC experience required."
        )
        r = match_v2.explain_cyber_match(j)
        self.assertTrue(r["accepted"])
        self.assertGreaterEqual(r["score"], 80)

    def test_mdr_security_specialist_is_accepted(self):
        j = self.job(
            "Security Specialist",
            "Managed Detection and Response service using Microsoft Sentinel and Defender. Monitor, triage, investigate, "
            "remediate and resolve cyber incidents. Manage tickets and SLAs, reduce false positives, and provide client support. "
            "1 year of security experience in a SOC required.",
            location="Mississauga, ON"
        )
        r = match_v2.explain_cyber_match(j)
        self.assertTrue(r["accepted"])
        self.assertGreaterEqual(r["score"], 80)

    def test_junior_security_operations_engineer_is_accepted(self):
        j = self.job(
            "Security Operations Engineer",
            "1-3 years of experience in a Security Engineering level role. Previous SOC analyst experience is a strong plus. "
            "Work closely with senior engineers and assist in development, testing and maintenance of SOAR playbooks, "
            "security automation workflows and API integrations. Exposure to SIEM, EDR and threat intelligence platforms. "
            "Foundational Python scripting, technical documentation, MITRE ATT&CK and Security+ or CySA+ are great to have."
        )
        r = match_v2.explain_cyber_match(j)
        self.assertTrue(r["accepted"])
        self.assertEqual(r["lane"], "Security Operations Engineer")
        self.assertGreaterEqual(r["score"], 70)

    def test_advanced_security_engineer_is_rejected(self):
        j = self.job(
            "Security Operations Engineer",
            "Requires 6 years of security engineering experience. Design enterprise-scale SOAR architecture, own platform "
            "engineering strategy, lead complex integrations and mentor engineering teams."
        )
        r = match_v2.explain_cyber_match(j)
        self.assertFalse(r["accepted"])

    def test_senior_role_is_rejected(self):
        j = self.job(
            "Senior SOC Analyst",
            "Microsoft Sentinel, Splunk, incident response and threat hunting. 3 years of SOC experience required."
        )
        r = match_v2.explain_cyber_match(j)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "senior_level")

    def test_five_year_requirement_is_rejected(self):
        j = self.job(
            "Security Operations Analyst",
            "Requires at least 5 years of cybersecurity experience. Monitor SIEM alerts and respond to incidents."
        )
        r = match_v2.explain_cyber_match(j)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "requires_5_plus_years")

    def test_off_lane_appsec_role_is_rejected(self):
        j = self.job(
            "Application Security Analyst",
            "SAST, DAST, secure SDLC, code review and penetration testing."
        )
        r = match_v2.explain_cyber_match(j)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "off_target_lane")

    def test_remote_bc_only_is_rejected(self):
        j = self.job(
            "SOC Analyst I",
            "Remote role. Monitor EDR and SIEM, investigate alerts and respond to incidents.",
            location="Canada - Remote BC"
        )
        r = match_v2.explain_cyber_match(j)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "location_incompatible")

    def test_canada_wide_remote_is_accepted(self):
        j = self.job(
            "SOC Analyst I",
            "Fully remote anywhere in Canada. Monitor Microsoft Sentinel and CrowdStrike, triage alerts, investigate malware, "
            "and escalate incidents. 1 year of SOC experience required.",
            location="Canada - Remote"
        )
        r = match_v2.explain_cyber_match(j)
        self.assertTrue(r["accepted"])
        self.assertGreaterEqual(r["location_fit"], 85)

    def test_broad_threat_analyst_without_soc_evidence_is_rejected(self):
        j = self.job(
            "Threat Analyst",
            "Conduct social engineering education, process reviews, simulated phishing campaigns and OSINT research."
        )
        r = match_v2.explain_cyber_match(j)
        self.assertFalse(r["accepted"])
        self.assertEqual(r["reason"], "off_target_lane")


if __name__ == "__main__":
    unittest.main()
