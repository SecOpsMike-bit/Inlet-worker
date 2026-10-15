"""Run Inlet v3 collector against selected employer feeds, writing local JSON only.

Examples:
 python collect_v3.py --company Cyderes --company Arctic Wolf
 python collect_v3.py --all --output staging/collector-v3.json

This script deliberately imports neither db nor worker and cannot modify Supabase.
"""
import argparse
import json
import sys
from pathlib import Path

import engine
from workday_v3 import fetch_workday_strict
from telus_digital_v3 import fetch_telus_digital_canada
from collector_v3 import collect_batch, save_staging_json
from directory import DIRECTORY

# Verified employer-hosted ATS boards. Keep overrides isolated from production.
VERIFIED_PLATFORMS = {"cyderes": ("lever", "cyderes")}


def companies_from_directory():
    result = []
    for c in DIRECTORY:
        item = dict(c)
        item["platform"] = "workday" if "workday" in item else item.get("platform", "auto")
        verified = VERIFIED_PLATFORMS.get(str(item.get("name", "")).casefold())
        if verified:
            item["platform"], item["slug"] = verified
        result.append(item)
    return result


def fetch_company(company):
    """Fetch from a known platform without suppressing network/API errors.

    Unknown-platform discovery is deliberately rejected until its source is
    resolved: engine.discover() swallows errors and would report false empties.
    """
    if company.get("name") == "TELUS International":
        return fetch_telus_digital_canada()
    if "workday" in company:
        w = company["workday"]
        return fetch_workday_strict(w["tenant"], w["pod"], w["site"])
    platform = company.get("platform")
    slug = company.get("slug")
    fetchers = {
        "greenhouse": engine.fetch_greenhouse,
        "lever": engine.fetch_lever,
        "ashby": engine.fetch_ashby,
        "smartrecruiters": engine.fetch_smartrecruiters,
    }
    if platform not in fetchers:
        raise ValueError("Unresolved feed platform; verify employer source before collection")
    return [j for j in fetchers[platform](slug) if j]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only v3 employer-feed staging collector")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Collect from all seed employers")
    group.add_argument("--company", action="append", help="Employer name (repeatable)")
    parser.add_argument("--output", default="staging/collector-v3.json")
    args = parser.parse_args(argv)

    available = companies_from_directory()
    if args.all:
        selected = available
    else:
        requested = {name.casefold() for name in args.company}
        selected = [c for c in available if c["name"].casefold() in requested]
        missing = requested - {c["name"].casefold() for c in selected}
        if missing:
            parser.error("Unknown company: " + ", ".join(sorted(missing)))

    # Known-platform fetch errors remain visible. Unknown feeds are errors,
    # never silently interpreted as employers with zero jobs.
    result = collect_batch(selected, fetch_company)
    result["warning"] = (
        "Unresolved employer feed platforms are errors, not verified empty boards. "
        "Workday listing errors propagate; job-detail lookups remain best effort."
    )
    save_staging_json(result, args.output)
    print(json.dumps({"output": args.output, "stats": result["stats"],
                      "companies": result["companies"], "warning": result["warning"]}, indent=2))
    return 0 if result["stats"]["companies_error"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
