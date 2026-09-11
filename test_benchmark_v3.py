"""Regression benchmark for GetInlets V3 profile-driven matching.

These cases represent manually reviewed roles and deliberate edge cases. V3 should
make the same broad Apply / Maybe / Skip decision a careful human reviewer would.
"""

import unittest

from match_v3 import evaluate
from profiles_v3 import CYBERSECURITY_BETA_PROFILE


class V3CyberMatchBenchmarkTests(unittest.TestCase):
    def job(self, title, location, text, posted="2026-09-09"):
        return {
            "title": title,
            "location": location,
            "text": text,
            "posted": posted,
            "url": "https://example.com/v3-benchmark",
        }

    def test_known_good_roles(self):
        cases = {
            "finastra": self.job(
                "Cyber Security Operations Center Analyst",
                "Mississauga - Avebury",
                "Monitor, investigate and respond to security alerts and incidents. Threat analysis and alert triage, "
                "incident response, containment, incident escalation, tracking and post-incident documentation. "
                "Hands-on SIEM including Microsoft Sentinel and Splunk. Windows and Linux, XDR, EDR, phishing, "
                "malware, threat intelligence and remediation guidance."
            ),
            "cdw": self.job(
                "Security Specialist",
                "Mississauga, ON, Canada",
                "Managed Detection and Response using Microsoft Sentinel and Microsoft Defender. Monitor, triage, "
                "investigate, remediate and resolve cyber incidents; escalation, root cause analysis, client support, "
                "SLA and ticket reviews. Improve analytics and reduce false positives, create SOC SOPs and use cases. "
                "1 year of security experience in a client-focused environment or SOC."
            ),
            "proserveit": self.job(
                "Junior Security Analyst",
                "Canada - Remote",
                "Managed security for customers: security monitoring, alert triage, event investigation and analysis, "
                "service desk ticket lifecycle, incident escalation and closure. Linux, Windows Server, TCP/IP, SIEM, "
                "VPN, routers, IDS/IPS, firewall configuration and client-facing remediation. 2+ years of SOC experience."
            ),
            "home_hardware": self.job(
                "Cyber Security Analyst",
                "St. Jacobs, ON",
                "Monitor security alerts and investigate incidents. Document findings and recommendations, support "
                "vulnerability assessments, security testing and remediation, incident response and escalation. "
                "Two years of cybersecurity, IT support, networking or systems administration. Windows, Linux, XDR, "
                "SIEM, TCP/IP, routing and switching. Onsite once per month."
            ),
        }

        results = {name: evaluate(job, CYBERSECURITY_BETA_PROFILE) for name, job in cases.items()}

        self.assertIn(results["finastra"]["recommendation"], {"strong_apply", "apply"})
        self.assertIn(results["cdw"]["recommendation"], {"strong_apply", "apply", "maybe"})
        self.assertIn(results["proserveit"]["recommendation"], {"strong_apply", "apply"})
        self.assertIn(results["home_hardware"]["recommendation"], {"apply", "maybe"})

        self.assertNotEqual(results["finastra"]["eligibility_status"], "fail")
        self.assertNotEqual(results["proserveit"]["eligibility_status"], "fail")
        self.assertGreater(results["finastra"]["overall_score"], results["home_hardware"]["overall_score"])

    def test_location_rejections(self):
        crowdstrike_bc = self.job(
            "SOC Analyst I",
            "Canada - Remote AB; Canada - Remote BC",
            "Virtual SOC detecting and responding to incidents. Windows, Linux, malware analysis, SIEM, EDR, "
            "incident response and Python. Remote role restricted to Alberta and British Columbia."
        )
        result = evaluate(crowdstrike_bc, CYBERSECURITY_BETA_PROFILE)
        self.assertEqual(result["recommendation"], "skip")
        self.assertEqual(result["eligibility_status"], "fail")
        self.assertEqual(result["location_score"], 0)

    def test_senior_and_off_lane_rejections(self):
        cases = [
            self.job(
                "Senior Security Operations Analyst",
                "Toronto, ON",
                "SIEM, Splunk, Sentinel and incident response. 3 years of security experience."
            ),
            self.job(
                "Security Architect",
                "Toronto, ON",
                "Architecture, cloud controls and security design."
            ),
            self.job(
                "Application Security Analyst",
                "Toronto, ON",
                "Secure SDLC, SAST, DAST and application security testing."
            ),
            self.job(
                "GRC Analyst",
                "Toronto, ON",
                "Governance, risk, compliance, audits and policy work."
            ),
        ]

        for job in cases:
            result = evaluate(job, CYBERSECURITY_BETA_PROFILE)
            self.assertEqual(result["recommendation"], "skip", result)

    def test_experience_rules(self):
        three_year = self.job(
            "Security Operations Analyst",
            "Toronto, ON",
            "3+ years of security experience. SIEM, Sentinel, alert triage, incident response, Windows and Linux."
        )
        four_year = self.job(
            "Security Operations Analyst",
            "Toronto, ON",
            "4+ years of security experience. SIEM, Sentinel, Splunk, alert triage, incident response, Windows and Linux."
        )
        five_year = self.job(
            "Security Operations Analyst",
            "Toronto, ON",
            "5+ years of security experience. SIEM, Sentinel, Splunk, alert triage and incident response."
        )

        r3 = evaluate(three_year, CYBERSECURITY_BETA_PROFILE)
        r4 = evaluate(four_year, CYBERSECURITY_BETA_PROFILE)
        r5 = evaluate(five_year, CYBERSECURITY_BETA_PROFILE)

        self.assertNotEqual(r3["eligibility_status"], "fail")
        self.assertIn("requires_3_years", r3["warnings"])
        self.assertNotEqual(r4["eligibility_status"], "fail")
        self.assertIn("requires_4_years", r4["warnings"])
        self.assertEqual(r5["eligibility_status"], "fail")
        self.assertEqual(r5["recommendation"], "skip")

    def test_nearby_ontario_hybrid_frequency(self):
        monthly = self.job(
            "Cyber Security Analyst",
            "St. Jacobs, ON",
            "SIEM, alert triage and incident response. Onsite once per month. 2 years of cybersecurity experience."
        )
        three_days = self.job(
            "Cyber Security Analyst",
            "St. Jacobs, ON",
            "SIEM, alert triage and incident response. Onsite three days per week. 2 years of cybersecurity experience."
        )

        monthly_result = evaluate(monthly, CYBERSECURITY_BETA_PROFILE)
        three_day_result = evaluate(three_days, CYBERSECURITY_BETA_PROFILE)

        self.assertGreater(monthly_result["location_score"], three_day_result["location_score"])
        self.assertIn("onsite_monthly", monthly_result["warnings"])
        self.assertIn("hybrid_3_days_week", three_day_result["warnings"])

    def test_conditional_threat_title_needs_better_future_lane_guard(self):
        """Documents a known V3 gap: broad conditional titles need content-lane gating.

        This is intentionally marked as an expected failure until V3 adds SOC-evidence
        requirements for conditional titles like Threat Analyst.
        """
        job = self.job(
            "Threat Analyst",
            "Toronto, ON",
            "3+ years with social engineering education, simulated phishing campaigns, suspicious email reporting, "
            "covert social engineering operations and OSINT research."
        )
        result = evaluate(job, CYBERSECURITY_BETA_PROFILE)

        # Desired V3 behavior: skip because this is not operational SOC / MDR work.
        self.assertEqual(result["recommendation"], "skip")


if __name__ == "__main__":
    unittest.main()
