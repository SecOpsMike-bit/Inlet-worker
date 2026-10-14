"""Fixture tests for public, external-only ADP Workforce Now job feeds."""

import urllib.error
import urllib.parse
import unittest

from adp_feed import fetch_adp, _tenant, EXTERNAL_CAREER_CENTRE


BOARD = (
    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/"
    "recruitment.html?cid=5d5085c5-5799-40cd-ae96-c7e0621cd1bc"
)


def row(item_id, title, external_id=None):
    fields = [{"nameCode": {"codeValue": "ExternalJobID"},
               "stringValue": external_id}] if external_id else []
    return {
        "itemID": item_id,
        "requisitionTitle": title,
        "requisitionLocations": [
            {"nameCode": {"shortName": " Toronto, ON, CA"}},
            {"nameCode": {"shortName": " Montréal, QC, CA"}},
            {"nameCode": {"shortName": " Toronto, ON, CA"}},
        ],
        "postDate": "2026-10-12T00:00:00",
        "customFieldGroup": {"stringFields": fields},
    }


class AdpFeedTests(unittest.TestCase):
    def test_public_external_board_only(self):
        cid, ccid = _tenant(BOARD)
        self.assertEqual(cid, "5d5085c5-5799-40cd-ae96-c7e0621cd1bc")
        self.assertEqual(ccid, EXTERNAL_CAREER_CENTRE)
        with self.assertRaises(ValueError):
            _tenant(BOARD.replace("workforcenow.adp.com", "workforcenow.adp.com.evil.org"))
        with self.assertRaises(ValueError):
            _tenant(BOARD + "&ccId=19000101_000002")

    def test_normalizes_verified_jobs_with_real_descriptions(self):
        calls = []
        def get_json(url):
            calls.append(url)
            if "/job-requisitions/" in url:
                return {"requisitionDescription": "<p>Monitor SIEM and EDR alerts.</p>"}
            return {"jobRequisitions": [
                row("9201277043066_1", "SOC Analyst", "584190"),
                row("9201277043066_1", "SOC Analyst", "584190"),
                row("9201285852815_1", "Account Executive", "585200"),
            ], "meta": {"totalNumber": 3}}
        jobs = fetch_adp(BOARD, get_json=get_json)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["title"], "SOC Analyst")
        self.assertEqual(jobs[0]["location"], "Toronto, ON, CA / Montréal, QC, CA")
        self.assertEqual(jobs[0]["posted"], "2026-10-12")
        self.assertEqual(jobs[0]["text"], "Monitor SIEM and EDR alerts.")
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(jobs[0]["url"]).query)
        self.assertEqual(query["jobId"], ["584190"])
        self.assertEqual(query["jwId"], ["9201277043066_1"])
        self.assertEqual(query["ccId"], [EXTERNAL_CAREER_CENTRE])
        self.assertEqual(len(calls), 3)
        self.assertIn("%24skip=1", calls[0])

    def test_one_based_pagination_and_cap(self):
        calls = []
        def get_json(url):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            calls.append(query["$skip"][0])
            if query["$skip"] == ["1"]:
                return {"jobRequisitions": [
                    row(f"92000000000{i:02d}_1", f"Analyst {i}")
                    for i in range(20)
                ], "meta": {"totalNumber": 21}}
            return {"jobRequisitions": [
                row("9200000000021_1", "Security Analyst")
            ], "meta": {"totalNumber": 21}}
        jobs = fetch_adp(BOARD, get_json=get_json, detail_cap=0)
        self.assertEqual(len(jobs), 21)
        self.assertEqual(calls, ["1", "21"])

    def test_unrecognized_shape_and_access_denied(self):
        with self.assertRaises(ValueError):
            fetch_adp(BOARD, get_json=lambda _: {"meta": {"totalNumber": 2}})
        def forbidden(_):
            raise urllib.error.HTTPError(BOARD, 403, "Forbidden", {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            fetch_adp(BOARD, get_json=forbidden)

    def test_detail_failure_keeps_posting_without_invented_description(self):
        def get_json(url):
            if "/job-requisitions/" in url:
                raise urllib.error.HTTPError(url, 503, "unavailable", {}, None)
            return {"jobRequisitions": [row("9201277043066_1", "SOC Analyst")],
                    "meta": {"totalNumber": 1}}
        jobs = fetch_adp(BOARD, get_json=get_json)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["text"], "")


if __name__ == "__main__":
    unittest.main()
