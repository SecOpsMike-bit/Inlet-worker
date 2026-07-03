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


# ============================================================ WORKDAY

WD_RE = re.compile(r"https?://([a-z0-9][a-z0-9-]*)\.(wd\d+)\.myworkdayjobs\.com/([^?\s\"'<>]*)", re.I)
LOCALE_RE = re.compile(r"^[a-z]{2}-[A-Za-z]{2}$")
WD_SKIP = {"wday", "job", "jobs", "en", "assets", "search", "search-results", ""}


def parse_workday(url):
    """Extract (tenant, pod, site) from a Workday career URL, or None."""
    m = WD_RE.search(url)
    if not m:
        return None
    tenant, pod = m.group(1).lower(), m.group(2).lower()
    segs = [s for s in m.group(3).split("/") if s]
    if not segs or segs[0].lower() == "wday":
        return None
    idx = 1 if LOCALE_RE.match(segs[0]) else 0     # skip a locale segment like en-US / fr-CA
    if len(segs) <= idx:
        return None
    site = segs[idx]
    if site.lower() in WD_SKIP or len(site) < 2:
        return None
    return (tenant, pod, site)


def harvest_workday_sites(max_sites=200):
    """Pull unique Workday (tenant, pod, site) career sites from Common Crawl."""
    cdx = latest_cc_index()
    q = urllib.parse.urlencode({"url": "myworkdayjobs.com", "matchType": "domain",
                                "output": "json", "fl": "url", "limit": max_sites * 40})
    sites = set()
    try:
        body = _get(f"{cdx}?{q}", timeout=90)
    except Exception as e:
        print(f"  cdx workday query failed: {e}")
        return []
    for line in body.splitlines():
        try:
            u = json.loads(line).get("url", "")
        except json.JSONDecodeError:
            continue
        parsed = parse_workday(u)
        if parsed:
            sites.add(parsed)
        if len(sites) >= max_sites:
            break
    return sorted(sites)


def validate_workday(tenant, pod, site):
    """Lightweight check: does this Workday site return jobs, any in Canada?"""
    cxs = f"https://{tenant}.{pod}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    try:
        d = eng._post_json(f"{cxs}/jobs", {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""})
    except Exception:
        return (False, 0, 0)
    posts = d.get("jobPostings", [])
    if not posts:
        return (False, 0, 0)
    canada = sum(1 for p in posts if eng.location_ok(p.get("locationsText", "")))
    if canada == 0:                                  # second look, filtered to Canada
        try:
            d2 = eng._post_json(f"{cxs}/jobs", {"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": "Canada"})
            canada = sum(1 for p in d2.get("jobPostings", []) if eng.location_ok(p.get("locationsText", "")))
        except Exception:
            pass
    return (True, len(posts), canada)


def add_workday_companies(sites, min_canada=1):
    """Validate Workday sites in parallel and upsert the Canadian-hiring ones."""
    s = db.Session()
    try:
        have = _existing_keys(s)
    finally:
        s.close()

    good, checked = [], 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(validate_workday, t, p, si): (t, p, si) for (t, p, si) in sites}
        for fut in as_completed(futures):
            t, p, si = futures[fut]
            checked += 1
            ok, total, canada = fut.result()
            if ok and canada >= min_canada and ("wd", t, p, si) not in have:
                good.append((t, p, si, canada))

    s = db.Session()
    try:
        for t, p, si, canada in good:
            s.add(db.Company(name=t, tier=3, platform="workday", wd_tenant=t, wd_pod=p,
                             wd_site=si, active=True, source="workday-cc", roles_found=canada,
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


def run(max_slugs=500, seed_only=False, platform="both"):
    db.init_db()
    seeded = seed_from_directory()
    if seeded:
        print(f"seeded {seeded} starter companies")
    if seed_only:
        return

    if platform in ("both", "greenhouse"):
        print(f"[greenhouse] harvesting up to {max_slugs} slugs from Common Crawl...")
        slugs = harvest_greenhouse_slugs(max_slugs)
        print(f"  found {len(slugs)} candidate slugs, validating...")
        checked, added = add_greenhouse_companies(slugs)
        print(f"  validated {checked}, added {added} new Greenhouse companies")

    if platform in ("both", "workday"):
        print(f"[workday] harvesting up to {max_slugs} sites from Common Crawl...")
        sites = harvest_workday_sites(max_slugs)
        print(f"  found {len(sites)} candidate sites, validating...")
        checked, added = add_workday_companies(sites)
        print(f"  validated {checked}, added {added} new Workday companies")

    s = db.Session()
    try:
        total = s.query(db.Company).filter(db.Company.active == True).count()
        wd = s.query(db.Company).filter(db.Company.platform == "workday", db.Company.active == True).count()
    finally:
        s.close()
    print(f"directory now holds {total} active companies ({wd} on Workday)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Discover companies for Inlet")
    ap.add_argument("--max", type=int, default=500, help="max slugs/sites to harvest")
    ap.add_argument("--platform", choices=["both", "greenhouse", "workday"], default="both")
    ap.add_argument("--seed", action="store_true", help="only load the starter list")
    args = ap.parse_args()
    run(max_slugs=args.max, seed_only=args.seed, platform=args.platform)
