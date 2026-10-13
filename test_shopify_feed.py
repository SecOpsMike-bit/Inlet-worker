"""Fixture tests for Shopify's first-party careers listing (no network)."""

import unittest
from unittest.mock import patch
import urllib.error

import engine
import shopify_feed


LISTING = """<html><body><main>
<a href="/careers/security-operations-analyst_62efacf8-e3b3-4265-be67-92f1e6f379ed">
<h4>Security Operations Analyst</h4><div><span>Remote - Canada</span></div></a>
<a href="/careers/security-operations-analyst_62efacf8-e3b3-4265-be67-92f1e6f379ed">
<h4>Security Operations Analyst</h4><div><span>Remote - Canada</span></div></a>
<a href="/careers/sales-associate_3634cf4f-a27d-4200-b09c-635dce73f68f">
<h4>Sales Associate</h4><div><span>Remote - Americas</span></div></a>
<a href="/careers/extraordinary">Skip the line</a>
</main></body></html>"""
DETAIL = """<html><head><script>malicious = 'IGNORE';</script></head>
<body><main><h1>Security Operations Analyst</h1>
<p>Investigate SIEM alerts, triage EDR incidents, and escalate malware.</p>
<script>hidden = 'DO NOT MATCH';</script></main></body></html>"""


class ShopifyFeedTests(unittest.TestCase):
    def test_parses_only_verified_job_links_and_deduplicates(self):
        def fake_fetch(url):
            return LISTING if url == shopify_feed.CAREERS_URL else DETAIL
        with patch.object(shopify_feed, "_fetch_html", side_effect=fake_fetch):
            jobs = shopify_feed.fetch_shopify()
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["title"], "Security Operations Analyst")
        self.assertEqual(jobs[0]["location"], "Remote - Canada")
        self.assertEqual(jobs[0]["url"], "https://www.shopify.com/careers/security-operations-analyst_62efacf8-e3b3-4265-be67-92f1e6f379ed")
        self.assertIn("SIEM alerts", jobs[0]["text"])
        self.assertNotIn("DO NOT MATCH", jobs[0]["text"])
        self.assertEqual(jobs[1]["title"], "Sales Associate")
        self.assertEqual(jobs[1]["text"], "")

    def test_bounded_detail_fetch(self):
        with patch.object(shopify_feed, "_fetch_html", return_value=LISTING) as fetch:
            jobs = shopify_feed.fetch_shopify(detail_cap=0)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(fetch.call_count, 1)

    def test_shopify_diagnostic_is_not_auto_discovery(self):
        sample = [{"title": "Security Analyst", "location": "Canada",
                   "url": "https://www.shopify.com/careers/security-analyst_12345678-1234-1234-1234-123456789abc",
                   "text": "SIEM", "posted": ""}]
        with patch.object(engine, "fetch_shopify", return_value=sample):
            jobs, diag = engine.pull_company_diagnostic(
                {"name": "Shopify", "platform": "shopify", "slug": "shopify"}
            )
        self.assertEqual(diag["status"], "ok")
        self.assertEqual(diag["platform"], "shopify")
        self.assertEqual(jobs, sample)

    def test_shopify_http_error_is_not_no_openings(self):
        with patch.object(engine, "fetch_shopify", side_effect=urllib.error.HTTPError(
            shopify_feed.CAREERS_URL, 503, "Unavailable", {}, None
        )):
            jobs, diag = engine.pull_company_diagnostic(
                {"name": "Shopify", "platform": "shopify", "slug": "shopify"}
            )
        self.assertEqual(jobs, [])
        self.assertEqual(diag["status"], "fetch_error")
        self.assertEqual(diag["http_status"], 503)


if __name__ == "__main__":
    unittest.main()
