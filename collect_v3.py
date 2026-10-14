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
from collector_v3 import collect_batch, save_staging_json
from directory import DIRECTORY


def companies_from_directory():
    result = []
    for c in DIRECTORY:
        item = dict(c)
        item["platform"] = "workday" if "workday" in item else item.get("platform", "auto")
        result.append(item)
    return result


def fetch_company(company):
    """Use existing platform fetchers, but never invoke their scoring or DB worker."""
    return engine.pull_company(company)


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

    # Current engine.pull_company converts fetch errors to [], making failures
    # indistinguishable from empty boards. Do not report false success.
    # Wrap platform-specific functions directly for known platform types.
    result = collect_batch(selected, fetch_company)
    result["warning"] = (
        "Legacy engine.pull_company suppresses feed exceptions; empty results "
        "can mean failure. Do not interpret empty feeds as verified zero openings."
    )
    save_staging_json(result, args.output)
    print(json.dumps({"output": args.output, "stats": result["stats"],
                      "companies": result["companies"], "warning": result["warning"]}, indent=2))
    return 0 if result["stats"]["companies_error"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
