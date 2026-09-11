"""Shadow-compare current V2 matching against V3 without changing production data.

This script pulls a sample of currently configured companies, evaluates each raw job
with both V2 and V3, and prints disagreement summaries. It does not write roles,
jobs, matches, or applications to the database.
"""

import argparse
import json

import db
import engine as eng
import match_v2
import match_v3
from profiles_v3 import CYBERSECURITY_BETA_PROFILE


def _company_dict(c):
    base = {"name": c.name, "tier": c.tier or 3, "id": c.id, "platform": c.platform}
    if c.platform == "workday" and c.wd_tenant:
        base["workday"] = {"tenant": c.wd_tenant, "pod": c.wd_pod, "site": c.wd_site}
    else:
        base["slug"] = c.slug
    return base


def _v2_decision(job, company):
    result = match_v2.process_v2(job, company)
    if not result:
        return "skip", None
    score = result.get("landability") or result.get("opportunity_score")
    return "keep", score


def _v3_decision(job):
    result = match_v3.evaluate(job, CYBERSECURITY_BETA_PROFILE)
    return result.get("recommendation", "skip"), result


def run(limit=40):
    db.init_db()
    session = db.Session()
    try:
        companies = (
            session.query(db.Company)
            .filter(db.Company.active == True)
            .order_by(db.Company.last_checked.desc().nullslast())
            .limit(limit)
            .all()
        )

        rows = []
        fetched_companies = 0
        raw_jobs = 0

        for company in companies:
            cd = _company_dict(company)
            jobs = eng.pull_company(cd) or []
            if not jobs:
                continue
            fetched_companies += 1

            for job in jobs:
                raw_jobs += 1
                v2_decision, v2_score = _v2_decision(job, cd)
                v3_decision, v3 = _v3_decision(job)
                v3_keep = v3_decision in {"strong_apply", "apply", "maybe"}
                disagree = (v2_decision == "keep") != v3_keep

                if disagree:
                    rows.append({
                        "company": company.name,
                        "title": job.get("title"),
                        "location": job.get("location"),
                        "url": job.get("url"),
                        "v2": v2_decision,
                        "v2_score": v2_score,
                        "v3": v3_decision,
                        "v3_score": v3.get("overall_score"),
                        "v3_reason": v3.get("reason") or v3.get("explanation", {}).get("title_reason"),
                        "warnings": v3.get("warnings", []),
                        "required_years": v3.get("explanation", {}).get("required_years"),
                    })

        print(json.dumps({
            "companies_requested": limit,
            "companies_with_jobs": fetched_companies,
            "raw_jobs_evaluated": raw_jobs,
            "disagreements": len(rows),
            "rows": rows,
        }, indent=2, default=str))
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare V2 and V3 matching on live raw jobs")
    parser.add_argument("--companies", type=int, default=40)
    args = parser.parse_args()
    run(limit=args.companies)
