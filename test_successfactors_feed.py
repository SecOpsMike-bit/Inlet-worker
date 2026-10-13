"""Offline regression tests for the public SuccessFactors job adapter."""
import unittest

from successfactors_feed import (
    fetch_successfactors, parse_job_detail, parse_listing,
)


BOARD = "https://jobs.descartes.com/go/View-All-Jobs/2574817/"
JOB = "https://jobs.descartes.com/job/Waterloo-Customer-Success-Manager-ON-N2V-1C6/603095517/"


class SuccessFactorsFeedTests(unittest.TestCase):
    def test_listing_extracts_official_distinct_job_links(self):
        page = """
        <a href="/job/Waterloo-Customer-Success-Manager-ON-N2V-1C6/603095517/">
            Customer <span>Success</span> Manager
        </a>
        <a href="/job/Waterloo-Customer-Success-Manager-ON-N2V-1C6/603095517/">
            Customer Success Manager
        </a>
        <a href="https://attacker.example/job/False-Job/9999/">False job</a>
        <a href="/go/View-All-Jobs/2574817/">All jobs</a>
        """
        self.assertEqual(
            parse_listing(page, BOARD), [("Customer Success Manager", JOB)]
        )

    def test_detail_requires_real_location_not_description_guess(self):
        detail = """
        <html><h1>Title: Customer Success Manager</h1>
        <div>Location:</div><div>Waterloo, ON, CA, N2V 1C6</div>
        <p>Security operations and support. Assist customers and document
        incidents, maintain runbooks and help with escalations.</p></html>
        """
        loc, text = parse_job_detail(detail)
        self.assertEqual(loc, "Waterloo, ON, CA, N2V 1C6")
        self.assertIn("Security operations and support", text)

    def test_fetch_returns_normalized_jobs(self):
        listing = '<a href="' + JOB + '">Customer Success Manager</a>'
        detail = """
        <h1>Title: Customer Success Manager</h1>
        <div>Location:</div><div>Waterloo, ON, CA, N2V 1C6</div>
        <p>Customer account operations, technical support and client
        communication, incident escalation, service improvement and
        stakeholder reporting for the logistics technology platform.</p>
        """
        pages = {BOARD: listing, JOB: detail}
        jobs = fetch_successfactors(BOARD, get_page=lambda url: pages[url])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["location"], "Waterloo, ON, CA, N2V 1C6")
        self.assertEqual(jobs[0]["url"], JOB)
        self.assertEqual(jobs[0]["posted"], "")

    def test_feed_errors_are_not_reported_as_zero_openings(self):
        with self.assertRaises(ValueError):
            fetch_successfactors(BOARD, get_page=lambda _: "<p>Broken board</p>")


if __name__ == "__main__":
    unittest.main()
