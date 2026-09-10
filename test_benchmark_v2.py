"""Regression benchmarks based on roles manually reviewed during the job search.

The point is not to reproduce every word of an employer posting. These fixtures keep
the requirements that mattered to the manual fit decision so future scoring changes
do not drift back toward generic 'cybersecurity' matching.
"""

import unittest

import match_v2


class MichaelMatchBenchmarkTests(unittest.TestCase):
    def job(self, title, location, text, posted="2026-09-09"):
        return {
            "title": title,
            "location": location,
            "text": text,
            "posted": posted,
            "url": "https://example.com/benchmark",
        }

    def test_known_good_and_bad_roles(self):
        cases = {
            "finastra": self.job(
                "Cyber Security Operations Center Analyst",
                "Mississauga - Avebury",
                "Monitor, investigate and respond to security alerts and incidents. Threat analysis and triage, "
                "incident response, containment, escalation, tracking and post-incident documentation. Hands-on "
                "SIEM including Microsoft Sentinel and Splunk. TCP/IP, DNS, HTTP, SMTP, cloud and on-premises, "
                "threat intelligence, operational playbooks and remediation requirements."
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
                "Managed security for customers: security monitoring, event investigation and analysis, service desk "
                "ticket lifecycle, escalation and closure. Linux, Windows Server, TCP/IP, SIEM, VPN, routers, IDS/IPS, "
                "firewall configuration and Security+. 2+ years of SOC experience."
            ),
            "home_hardware": self.job(
                "Cyber Security Analyst",
                "St. Jacobs, ON",
                "Monitor security alerts and investigate incidents. Document findings and recommendations, support "
                "vulnerability assessments, security testing and remediation, incident response and escalation. "
                "Two years of cybersecurity, IT support, networking or systems administration. Windows, Linux, XDR, "
                "SIEM, TCP/IP, routing, switching; Bash or Python is an asset."
            ),
            "crowdstrike_bc": self.job(
                "Analyst I, Falcon Complete (Remote, PST/MST)",
                "Canada - Remote AB; Canada - Remote BC",
                "Virtual SOC detecting and responding to incidents. Windows, Mac and Linux incident handling, malware "
                "analysis, forensic analysis, network logs, remediation and Python. Remote PST/MST."
            ),
            "acero": self.job(
                "Threat Analyst",
                "Toronto, ON",
                "3+ years with social engineering education, simulated phishing campaigns, suspicious email reporting, "
                "covert social engineering operations and OSINT research."
            ),
        }

        results = {name: match_v2.explain_cyber_match(job) for name, job in cases.items()}

        for name in ("finastra", "cdw", "proserveit", "home_hardware"):
            self.assertTrue(results[name]["accepted"], f"{name}: {results[name]}")

        self.assertGreaterEqual(results["finastra"]["score"], 90)
        self.assertGreaterEqual(results["cdw"]["score"], 80)
        self.assertGreaterEqual(results["proserveit"]["score"], 70)
        self.assertGreaterEqual(results["home_hardware"]["score"], 70)

        # Stronger explicit SOC tooling should rank above broad-tooling analyst roles.
        self.assertGreater(results["finastra"]["score"], results["home_hardware"]["score"])

        self.assertFalse(results["crowdstrike_bc"]["accepted"])
        self.assertEqual(results["crowdstrike_bc"]["reason"], "location_incompatible")

        self.assertFalse(results["acero"]["accepted"])
        self.assertIn(results["acero"]["reason"], {"off_target_lane", "weak_profile_match"})


if __name__ == "__main__":
    unittest.main()
