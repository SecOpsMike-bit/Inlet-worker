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

    def test_falcon_complete_titles_without_security_keyword(self):
        """Role-family names need SOC evidence, and location still overrides fit."""
        description = (
            "Virtual SOC analyst for managed detection and response customers. "
            "Security monitoring, SIEM, EDR, incident response, alert triage, "
            "malware investigation, Windows and Linux, client-facing remediation."
        )
        eligible = self.job(
            "Analyst I, Falcon Complete (Remote)",
            "Canada - Remote ON",
            description,
            posted="2026-10-07",
        )
        restricted = self.job(
            "Analyst I, Falcon Complete (Remote, PST/MST)",
            "Canada - Remote AB; Canada - Remote BC",
            description,
            posted="2026-10-07",
        )
        senior = self.job(
            "Sr. Analyst, Falcon Complete (Remote)",
            "Canada - Remote ON",
            description,
            posted="2026-10-07",
        )
        eligible_result = evaluate(eligible, CYBERSECURITY_BETA_PROFILE)
        restricted_result = evaluate(restricted, CYBERSECURITY_BETA_PROFILE)
        senior_result = evaluate(senior, CYBERSECURITY_BETA_PROFILE)
        self.assertIn(eligible_result["recommendation"], {"strong_apply", "apply", "maybe"})
        self.assertEqual(restricted_result["recommendation"], "skip")
        self.assertEqual(restricted_result["eligibility_status"], "fail")
        self.assertEqual(senior_result["recommendation"], "skip")

    def test_foreign_remote_is_not_canada_eligible(self):
        """ATS 'Remote' jobs outside Canada must never reach Apply/Maybe."""
        description = (
            "Managed detection and response virtual SOC: SIEM, EDR, "
            "security monitoring, alert triage, incident response, Windows, "
            "Linux, malware investigation, client-facing remediation."
        )
        foreign_locations = [
            "USA - Remote",
            "United Kingdom - Remote",
            "United States",
            "Remote - US",
            "India - Remote",
            "Remote, Denmark",
        ]
        for location in foreign_locations:
            with self.subTest(location=location):
                result = evaluate(
                    self.job("Analyst I, Falcon Complete (Remote)", location, description,
                             posted="2026-10-07"),
                    CYBERSECURITY_BETA_PROFILE,
                )
                self.assertEqual(result["recommendation"], "skip")
                self.assertEqual(result["eligibility_status"], "fail")
                self.assertIn("foreign_country_restricted", result["warnings"])
                self.assertEqual(result["reason"], "foreign_country_restricted")

        canadian = evaluate(
            self.job("Analyst I, Falcon Complete (Remote)", "Canada - Remote ON",
                     description, posted="2026-10-07"),
            CYBERSECURITY_BETA_PROFILE,
        )
        self.assertIn(canadian["recommendation"], {"strong_apply", "apply", "maybe"})

    def test_skillbridge_is_not_regular_entry_level_opening(self):
        description = (
            "Virtual SOC managed detection and response, SIEM, EDR, "
            "security monitoring, alert triage, incident response, malware."
        )
        result = evaluate(
            self.job("Analyst, Falcon Complete - SkillBridge",
                     "Canada - Remote ON", description, posted="2026-10-07"),
            CYBERSECURITY_BETA_PROFILE,
        )
        self.assertEqual(result["recommendation"], "skip")
        self.assertIn("us_skillbridge_program", result["warnings"])

    def test_live_shadow_candidates_from_october_2026(self):
        """Regression cases from the 2026-10-08 ATS shadow comparison.

        The CDW description is a concise paraphrase of its published posting.
        The other examples preserve the exact title/location eligibility signals
        that caused the earlier false-positive recommendations.
        """
        cdw = self.job(
            "Security Specialist",
            "Mississauga / Forsythe - ON 44",
            "Second-level cybersecurity incident response in a managed detection "
            "and response SOC, primarily Microsoft Sentinel and Defender. "
            "Monitor, triage, investigate, remediate and escalate incidents; "
            "perform root cause analysis, improve SIEM analytics, reduce false "
            "positives and provide client support. Requires 1 year of security "
            "experience and at least two intermediate-level security certifications.",
            posted="2026-10-01",
        )
        us = self.job(
            "Analyst I, Falcon Complete (Hybrid, San Antonio)",
            "USA - Remote",
            "Managed detection and response, EDR, SIEM, alert triage, "
            "security monitoring, incident response.",
            posted="2026-10-07",
        )
        uk = self.job(
            "Analyst I, Falcon Complete (Remote, GBR)",
            "United Kingdom - Remote",
            "Managed detection and response, EDR, SIEM, alert triage, "
            "security monitoring, incident response.",
            posted="2026-10-07",
        )
        skillbridge = self.job(
            "Analyst, Falcon Complete - SkillBridge",
            "USA - St. Louis, MO",
            "Managed detection and response, EDR, SIEM, alert triage, "
            "security monitoring, incident response.",
            posted="2026-10-07",
        )
        cdw_result = evaluate(cdw, CYBERSECURITY_BETA_PROFILE)
        self.assertIn(cdw_result["recommendation"], {"apply", "maybe", "strong_apply"})
        for case in (us, uk, skillbridge):
            with self.subTest(title=case["title"]):
                result = evaluate(case, CYBERSECURITY_BETA_PROFILE)
                self.assertEqual(result["recommendation"], "skip")
                self.assertEqual(result["eligibility_status"], "fail")

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

            # The HLB/Dice: aggregator says "Remote" and the title looks plausible,
            # but the description requires an existing CDC badge and Atlanta-metro
            # presence. Hard eligibility must outrank skill overlap.
            "hlb_cdc": {
                "title": "Security Analyst",
                "location": "Remote",
                "employment_type": "Contract W2",
                "text": "MUST BE CDC BADGED and ATL METRO BASED. 5+ years cybersecurity operations. "
                        "Security monitoring, incident response, vulnerability management, NIST SP 800-53, STIG and POA&M.",
                "posted": "2026-10-05",
                "url": "https://www.dice.com/job-detail/0b03b580-7701-4444-a96f-5383555707bd",
            },

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

        self.assertEqual(results["hlb_cdc"]["recommendation"], "skip")
        self.assertEqual(results["hlb_cdc"]["eligibility_status"], "fail")
        self.assertIn("requires_cdc_badge", results["hlb_cdc"]["warnings"])
        self.assertIn("requires_atlanta_metro", results["hlb_cdc"]["warnings"])
        self.assertIn("us_w2_only", results["hlb_cdc"]["warnings"])

        self.assertEqual(results["paladin_physical"]["recommendation"], "skip")
        self.assertEqual(results["sunnybrook_senior"]["recommendation"], "skip")
        self.assertEqual(results["crowdstrike_bc"]["recommendation"], "skip")


if __name__ == "__main__":
    unittest.main()
