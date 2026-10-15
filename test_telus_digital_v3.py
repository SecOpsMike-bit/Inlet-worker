import unittest
from telus_digital_v3 import parse_canada_jobs

PAGE = """<html><body><h1>Job Search Results</h1>
Showing 1-2 of 2 result(s)
<h4><a href="/jobs/17271982-bilingual-customer-service-representative-canada">Bilingual Customer Service Representative (Canada)</a></h4>
<p>Canada</p>
<h4><a href="https://careers.telusdigital.com/jobs/17272007-e-commerce-customer-service-representative">E-Commerce Customer Service Representative</a></h4>
<p>Montreal, QC, Canada</p></body></html>"""

class TelusDigitalV3Tests(unittest.TestCase):
    def test_parses_both_official_jobs(self):
        jobs = parse_canada_jobs(PAGE)
        self.assertEqual(len(jobs), 2)
        self.assertTrue(all(x["url"].startswith("https://careers.telusdigital.com/jobs/") for x in jobs))
    def test_rejects_incomplete_page(self):
        with self.assertRaisesRegex(ValueError, "paginated"):
            parse_canada_jobs(PAGE.replace("1-2 of 2", "1-2 of 30"))
    def test_rejects_missing_links(self):
        with self.assertRaisesRegex(ValueError, "mismatch"):
            parse_canada_jobs(PAGE.replace('href="/jobs/17271982-', 'href="/not-a-job/17271982-'))
    def test_rejects_unrecognized_markup(self):
        with self.assertRaises(ValueError):
            parse_canada_jobs("<html>Forbidden</html>")
    def test_rejects_external_links(self):
        with self.assertRaisesRegex(ValueError, "mismatch"):
            parse_canada_jobs(PAGE.replace("https://careers.telusdigital.com/jobs/17272007", "https://other.example/jobs/17272007"))

if __name__ == "__main__":
    unittest.main()
