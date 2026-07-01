"""
discovery.py  -  automatic company discovery for Inlet (Greenhouse).

Finding companies is the machine's job, not yours. This:
  1. Harvests Greenhouse board slugs from Common Crawl (the public web crawl).
  2. Validates each slug against Greenhouse's public API.
  3. Keeps the ones hiring in Canada / remote.
  4. Writes them into the `companies` table, which the worker reads.

Run occasionally to grow the directory:
    python discovery.py                 # harvest + validate + add, default caps
    python discovery.py --max 1000      # look at up to 1000 slugs
    python discovery.py --seed          # just load the built-in starter list, no crawl
"""

import argparse
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import db
import engine as eng
from directory import DIRECTORY

UA = {"User-Agent": "inlet-discovery/1.0"}
CC_COLLINFO = "https://index.commoncrawl.org/collinfo.json"
GH_PATTERNS = ["boards.greenhouse.io/*", "job-boards.greenhouse.io/*"]
# slugs that are not real company boards
SKIP_SLUGS = {"embed", "jobs", "v1", "boards", "internal", "assets", "static"}


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def latest_cc_index():
    """Return the CDX API url of the most recent Common Crawl index."""
    data = json.loads(_get(CC_COLLINFO))
    return data[0]["cdx-api"]           # newest first


def harvest_greenhouse_slugs(max_slugs=500):
    """Pull Greenhouse board slugs out of the latest Common Crawl index."""
    cdx = latest_cc_index()
    slugs = set()
    for pattern in GH_PATTERNS:
        q = urllib.parse.urlencode({"url": pattern, "output": "json", "fl": "url", "limit": max_slugs * 4})
        try:
            body = _get(f"{cdx}?{q}", timeout=60)
        except Exception as e:
            print(f"  cdx query failed for {pattern}: {e}")
            continue
        for line in body.splitlines():
            try:
                u = json.loads(line).get("url", "")
            except json.JSONDecodeError:
                continue
            m = re.search(r"greenhouse\.io/([A-Za-z0-9_-]+)", u)
            if m:
                slug = m.group(1).lower()
                if slug not in SKIP_SLUGS and len(slug) > 1:
                    slugs.add(slug)
            if len(slugs) >= max_slugs:
                break
        if len(slugs) >= max_slugs:
            break
    return sorted(slugs)


def validate_greenhouse(slug):
    """Return (ok, total_jobs, canada_jobs) for a Greenhouse slug."""
    try:
        jobs = [j for j in eng.fetch_greenhouse(slug) if j]
    except Exception:
        return (False, 0, 0)
    if not jobs:
        return (False, 0, 0)
    canada = sum(1 for j in jobs if eng.location_ok(j["location"]))
    return (True, len(jobs), canada)


def _company_key(c):
    if c.slug:
        return ("slug", c.platform, c.slug)
    return ("wd", c.wd_tenant, c.wd_pod, c.wd_site)


def _existing_keys(s):
    keys = set()
    for c in s.query(db.Company).all():
        keys.add(_company_key(c))
    return keys


def add_greenhouse_companies(slugs, min_canada=1):
    """Validate slugs in parallel and upsert the good ones."""
    s = db.Session()
    try:
        have = _existing_keys(s)
    finally:
        s.close()

    good = []
    checked = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(validate_greenhouse, slug): slug for slug in slugs}
        for fut in as_completed(futures):
            slug = futures[fut]
            checked += 1
            ok, total, canada = fut.result()
            if ok and canada >= min_canada:
                key = ("slug", "greenhouse", slug)
                if key not in have:
                    good.append((slug, canada))

    s = db.Session()
    try:
        for slug, canada in good:
            s.add(db.Company(name=slug, tier=3, platform="greenhouse", slug=slug,
                             active=True, source="greenhouse-cc", roles_found=canada,
                             last_checked=dt.datetime.utcnow()))
        s.commit()
    finally:
        s.close()
    return checked, len(good)


def seed_from_directory():
    """One-time load of the built-in starter companies into the table."""
    s = db.Session()
    try:
        have = _existing_keys(s)
        added = 0
        for c in DIRECTORY:
            if "workday" in c:
                w = c["workday"]
                key = ("wd", w["tenant"], w["pod"], w["site"])
                if key in have:
                    continue
                s.add(db.Company(name=c["name"], tier=c["tier"], platform="workday",
                                 wd_tenant=w["tenant"], wd_pod=w["pod"], wd_site=w["site"],
                                 active=True, source="seed"))
                added += 1
            else:
                key = ("slug", "greenhouse", c["slug"])   # platform auto-detected at fetch
                if ("slug", "greenhouse", c["slug"]) in have or ("slug", "lever", c["slug"]) in have:
                    continue
                s.add(db.Company(name=c["name"], tier=c["tier"], platform="auto",
                                 slug=c["slug"], active=True, source="seed"))
                added += 1
        s.commit()
        return added
    finally:
        s.close()


def run(max_slugs=500, seed_only=False):
    db.init_db()
    seeded = seed_from_directory()
    if seeded:
        print(f"seeded {seeded} starter companies")
    if seed_only:
        return
    print(f"harvesting up to {max_slugs} Greenhouse slugs from Common Crawl...")
    slugs = harvest_greenhouse_slugs(max_slugs)
    print(f"  found {len(slugs)} candidate slugs, validating...")
    checked, added = add_greenhouse_companies(slugs)
    print(f"validated {checked}, added {added} new companies hiring in Canada/remote")
    s = db.Session()
    try:
        total = s.query(db.Company).filter(db.Company.active == True).count()
    finally:
        s.close()
    print(f"directory now holds {total} active companies")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Discover companies for Inlet")
    ap.add_argument("--max", type=int, default=500, help="max slugs to harvest")
    ap.add_argument("--seed", action="store_true", help="only load the starter list")
    args = ap.parse_args()
    run(max_slugs=args.max, seed_only=args.seed)
