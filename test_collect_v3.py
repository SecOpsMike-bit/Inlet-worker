"""CLI adapter tests: no real network or production database required."""
import unittest
from unittest.mock import patch
import collect_v3


class FetchAdapterTests(unittest.TestCase):
    def test_cyderes_uses_verified_lever_feed(self):
        company = next(c for c in collect_v3.companies_from_directory() if c["name"] == "Cyderes")
        self.assertEqual(company["platform"], "lever")
        self.assertEqual(company["slug"], "cyderes")

    def test_unresolved_platform_is_error(self):
        with self.assertRaisesRegex(ValueError, "Unresolved feed platform"):
            collect_v3.fetch_company({"name": "Unknown", "slug": "unknown", "platform": "auto"})

    def test_known_platform_fetch_errors_propagate(self):
        with patch.object(collect_v3.engine, "fetch_greenhouse", side_effect=TimeoutError("network")):
            with self.assertRaises(TimeoutError):
                collect_v3.fetch_company({"name": "Known", "slug": "known", "platform": "greenhouse"})

    def test_known_platform_fetch_returns_jobs(self):
        raw = [{"title": "SOC Analyst", "url": "https://example.com/job"}]
        with patch.object(collect_v3.engine, "fetch_greenhouse", return_value=raw):
            self.assertEqual(collect_v3.fetch_company(
                {"name": "Known", "slug": "known", "platform": "greenhouse"}), raw)

    def test_workday_fetch_uses_existing_tenant(self):
        with patch.object(collect_v3, "fetch_workday_strict", return_value=[]) as fetch:
            collect_v3.fetch_company({"name": "Example", "platform": "workday",
                                      "workday": {"tenant": "abc", "pod": "wd1", "site": "External"}})
            fetch.assert_called_once_with("abc", "wd1", "External")


if __name__ == "__main__":
    unittest.main()
