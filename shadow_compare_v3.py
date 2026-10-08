"""Shadow-compare current V2 matching against V3 without changing production data.

By default this uses the built-in company directory and pulls current jobs directly
from employer ATS feeds. That keeps the comparison independent of the production
database. A database-backed source remains available for deeper manual runs.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import db
import engine as eng
import match_v2
import match_v3
from directory import DIRECTORY
from profiles_v3 import CYBERSECURITY_BETA_PROFILE


def _company_dict(c):
    base = {"name": c.name, "tier": c.tier or 3, "id": c.id, "platform": c.platform}
    if c.platform == "workday" and c.wd_tenant:
        base["workday"] = {"tenant": c.wd_tenant, "pod": c.wd_pod, "site": c.wd_site}
    else:
        base["slug"] = c.slug
    return base


def _directory_company_dict(c, index):
    out = dict(c)
    out["id"] = -(index + 1)
    out["platform"] = "workday" if "workday" in out else "auto"
    return out


def _v2_decision(job, company):
    result = match_v2.process_v2(job, company)
    if not result:
        return "skip", None
    score = result.get("landability") or result.get("opportunity_score")
    return "keep", score


def _v3_decision(job):
    result = match_v3.evaluate(job, CYBERSECURITY_BETA_PROFILE)
    return result.get("recommendation", "skip"), result


def _companies(limit, source):
    if source == "directory":
        return [_directory_company_dict(c, i) for i, c in enumerate(DIRECTORY[:limit])], None

    db.init_db()
    session = db.Session()
    companies = (
        session.query(db.Company)
        .filter(db.Company.active == True)
        .order_by(db.Company.last_checked.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [_company_dict(c) for c in companies], session


CYBER_TITLE_PATTERN = re.compile(
    r"\b(?:soc|cyber|security|threat|incident|detection|malware|forensic|vulnerability|infosec)\b",
    re.IGNORECASE,
)


def run(limit=40, source="directory", output=None):
    companies, session = _companies(limit, source)
    try:
        rows = []
        fetched_companies = 0
        raw_jobs = 0
        v2_kept = 0
        v3_kept = 0
        v3_recommendations = []
        per_company = []
        v3_rejection_reasons = Counter()
        cyber_title_candidates = []

        for cd in companies:
            jobs = eng.pull_company(cd) or []
            company_stats = {"company": cd.get("name"), "raw_jobs": len(jobs),
                             "v2_kept": 0, "v3_kept": 0, "cyber_title_candidates": 0}
            per_company.append(company_stats)
            if not jobs:
                continue
            fetched_companies += 1

            for job in jobs:
                raw_jobs += 1
                v2_decision, v2_score = _v2_decision(job, cd)
                v3_decision, v3 = _v3_decision(job)
                v3_keep = v3_decision in {"strong_apply", "apply", "maybe"}
                disagree = (v2_decision == "keep") != v3_keep
                v3_reason = v3.get("reason") or v3.get("explanation", {}).get("title_reason")
                if not v3_keep:
                    v3_rejection_reasons[v3_reason or "below_threshold"] += 1
                if CYBER_TITLE_PATTERN.search(job.get("title") or ""):
                    company_stats["cyber_title_candidates"] += 1
                    cyber_title_candidates.append({
                        "company": cd.get("name"),
                        "title": job.get("title"),
                        "location": job.get("location"),
                        "url": job.get("url"),
                        "v2": v2_decision,
                        "v3": v3_decision,
                        "v3_score": v3.get("overall_score"),
                        "v3_reason": v3_reason,
                        "warnings": v3.get("warnings", []),
                    })
                if v2_decision == "keep":
                    v2_kept += 1
                    company_stats["v2_kept"] += 1
                if v3_keep:
                    v3_kept += 1
                    company_stats["v3_kept"] += 1
                    v3_recommendations.append({
                        "company": cd.get("name"),
                        "title": job.get("title"),
                        "location": job.get("location"),
                        "url": job.get("url"),
                        "recommendation": v3_decision,
                        "score": v3.get("overall_score"),
                        "warnings": v3.get("warnings", []),
                    })

                if disagree:
                    rows.append({
                        "company": cd.get("name"),
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

        report = {
            "source": source,
            "companies_requested": limit,
            "companies_available": len(companies),
            "companies_with_jobs": fetched_companies,
            "raw_jobs_evaluated": raw_jobs,
            "v2_kept": v2_kept,
            "v3_kept": v3_kept,
            "per_company": per_company,
            "v3_rejection_reasons": dict(v3_rejection_reasons.most_common()),
            "cyber_title_candidates_count": len(cyber_title_candidates),
            "cyber_title_candidates": cyber_title_candidates,
            "v3_recommendations": sorted(
                v3_recommendations,
                key=lambda row: row["score"] or 0,
                reverse=True,
            )[:30],
            "disagreements": len(rows),
            "rows": rows,
        }
        if output:
            Path(output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        summary = {key: report[key] for key in (
            "source", "companies_available", "companies_with_jobs",
            "raw_jobs_evaluated", "v2_kept", "v3_kept",
            "cyber_title_candidates_count", "disagreements",
            "per_company", "v3_rejection_reasons",
        )}
        summary["cyber_title_candidates_preview"] = cyber_title_candidates[:35]
        summary["v3_recommendations"] = report["v3_recommendations"]
        print(json.dumps(summary, indent=2, default=str))
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare V2 and V3 matching on live raw jobs")
    parser.add_argument("--companies", type=int, default=40)
    parser.add_argument("--source", choices=("directory", "db"), default="directory")
    parser.add_argument("--output", help="Optional path for full JSON diagnostic report")
    args = parser.parse_args()
    run(limit=args.companies, source=args.source, output=args.output)
