"""Real-world regression cases for GetInlets V3.

These fixtures are concise paraphrases of live/recent Canadian postings reviewed
in September 2026. They exist to catch common search/matching mistakes such as
physical-security false positives, province-restricted remote roles, and strong
SOC roles hidden behind less-obvious titles.
"""

import unittest

from match_v3 import evaluate
from profiles_v3 import CYBERSECURITY_BETA_PROFILE


class V3RealWorldBenchmarkTests(unittest.TestCase):
    def job(self, title, location, text, posted="2026-09-09"):
        return {
            "title": title,
            "location": location,
            "text": text,
            "posted": posted,
            "url": "https://example.com/realworld-benchmark",
        }

    def test_current_market_examples(self):
        cases = {
            # CDW Toronto: genuine SOC L2 work: SIEM/SOAR/tickets, triage,
            # investigation, response and escalation.
            "cdw_l2": self.job(
                "Cyber Security Analyst (L2)",
                "Toronto, ON",
                "Security Operations Centre role. Monitor and investigate security events from SIEM, SOAR, tickets, "
                "email and phone. Triage, respond and escalate to senior analysts and customers. EDR, incident response."
            ),

            # Deloitte: security operations + IDPS + automation. Early-career
            # experience requirement is compatible with this profile.
            "deloitte_idps": self.job(
                "IDPS Cyber Automation Analyst",
                "Toronto, ON - Remote",
                "1-2 years experience in security operations. Support intrusion detection and prevention operations, "
                "alert triage, incident investigation and response, Splunk, Python, API integrations, security automation, "
                "SOC processes and firewall technologies."
            ),

            # ProServeIT: junior managed-security role, Canada remote.
            "proserveit": self.job(
                "Junior Security Analyst",
                "Canada - Remote",
                "Managed security for customers with security monitoring, event investigation and analysis, ticket lifecycle, "
                "escalation and closure. Linux, Windows, SIEM, VPN, IDS/IPS and firewall knowledge. 2+ years SOC experience."
            ),

            # Home Hardware: operational cyber analyst in St. Jacobs.
            "home_hardware": self.job(
                "Cyber Security Analyst",
                "St. Jacobs, ON",
                "Monitor security alerts, investigate incidents, support vulnerability assessment and remediation, incident "
                "response and escalation. Windows, Linux, XDR, SIEM and networking. Onsite once per month. 2 years experience."
            ),

            # Paladin: title looks perfect but this is physical-security operations,
            # not cyber/SOC. This should never appear as a cyber recommendation.
            "paladin_physical": self.job(
                "Security Operations Analyst",
                "Toronto, ON",
                "Physical Security Operations across commercial real estate assets. Analyze guard and incident data, physical "
                "security technology, front-line readiness, site security teams, access control, SOPs and operational reporting."
            ),

            # Sunnybrook: clearly senior and architecture/risk-oriented.
            "sunnybrook_senior": self.job(
                "Senior Security Analyst - Cyber Security",
                "Toronto, ON",
                "Senior cybersecurity role responsible for IT risk assessments, security architecture frameworks, cloud and "
                "application security requirements and enterprise security design."
            ),

            # CrowdStrike-style province constrained remote role. A Toronto-based
            # profile should not see AB/BC-only remote as eligible.
            "crowdstrike_bc": self.job(
                "Analyst I, Falcon Complete (Remote, PST/MST)",
                "Canada - Remote AB; Canada - Remote BC",
                "Virtual SOC detecting and responding to incidents. EDR, malware analysis, forensic analysis, Windows and Linux."
            ),
        }

        results = {name: evaluate(job, CYBERSECURITY_BETA_PROFILE) for name, job in cases.items()}

        self.assertIn(results["cdw_l2"]["recommendation"], {"strong_apply", "apply", "maybe"})
        self.assertIn(results["deloitte_idps"]["recommendation"], {"strong_apply", "apply", "maybe"})
        self.assertIn(results["proserveit"]["recommendation"], {"strong_apply", "apply"})
        self.assertIn(results["home_hardware"]["recommendation"], {"apply", "maybe"})

        self.assertEqual(results["paladin_physical"]["recommendation"], "skip")
        self.assertEqual(results["sunnybrook_senior"]["recommendation"], "skip")
        self.assertEqual(results["crowdstrike_bc"]["recommendation"], "skip")


if __name__ == "__main__":
    unittest.main()
