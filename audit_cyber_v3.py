"""Report candidate cyber inventory without filtering or modifying staged raw jobs."""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path

CYBER_TERMS = re.compile(
    r"cyber|information security|it security|security (?:operations|analyst|engineer|specialist|architect|incident|monitoring)"
    r"|\\bsoc\\b|threat (?:analyst|detection|hunter|intelligence)|incident (?:response|responder)"
    r"|detection (?:engineer|analyst)|\\bdfir\\b|\\bmdr\\b|\\bsiem\\b", re.I
)
NON_CYBER = re.compile(
    r"financial security|security advisor|estate planning|physical security|security guard"
    r"|loss prevention|social security", re.I
)


def is_cyber_title(title):
    return bool(CYBER_TERMS.search(title or "")) and not bool(NON_CYBER.search(title or ""))


CANADA_TERMS = re.compile(r"canada|ontario|toronto|mississauga|waterloo|kitchener|ottawa|vancouver|montreal|calgary|edmonton|\bON\b|\bBC\b|\bAB\b", re.I)
REMOTE_TERMS = re.compile(r"remote", re.I)
SENIOR_TERMS = re.compile(r"\bsenior\b|\bsr\.?\b|\blead\b|\bprincipal\b|\bstaff\b|\bdirector\b|\bmanager\b|\bhead\b|\bvp\b", re.I)


def summarize(postings):
    by_company = Counter(x.get("source_company", "") for x in postings)
    title_cyber = [x for x in postings if is_cyber_title(x.get("title", ""))]
    canada_explicit = [x for x in title_cyber if CANADA_TERMS.search(x.get("location", ""))]
    remote_unspecified = [x for x in title_cyber if REMOTE_TERMS.search(x.get("location", "")) and not CANADA_TERMS.search(x.get("location", ""))]
    review = [x for x in canada_explicit if not SENIOR_TERMS.search(x.get("title", ""))]
    return {
        "raw_total": len(postings),
        "by_company": dict(by_company),
        "cyber_title_signal": len(title_cyber),
        "cyber_explicit_canada_location": len(canada_explicit),
        "cyber_remote_unspecified_country": len(remote_unspecified),
        "cyber_canada_non_senior_title_review": len(review),
        "review_roles": [{"company": x.get("source_company"), "title": x.get("title"),
                          "location": x.get("location"), "url": x.get("source_url")} for x in review],
        "disclaimer": "Heuristic audit only; Canadian eligibility, current vacancy and entry-level requirements need human/source verification. Raw jobs are not removed.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot")
    parser.add_argument("--output", default="staging/cyber-summary.json")
    args = parser.parse_args()
    data = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    summary = summarize(data["postings"])
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
