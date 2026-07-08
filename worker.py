"""
worker.py  -  incremental, field-aware refresh worker for Inlet.

Instead of re-pulling every company every run (which times out at scale), each run
refreshes a rotating SLICE of companies, oldest-checked first, bounded by a time
budget so it always finishes well under CI limits.

Per company: if the fetch succeeds, that company's roles are replaced with a fresh
pull (removing its expired postings). If the fetch fails, its existing roles are
left alone (a blip never wipes the board). A stale-sweep removes any role not seen
in STALE_DAYS as a catch-all for expiry.

    python worker.py            # one incremental slice
    python worker.py --demo     # sample roles, no network
    python worker.py --loop --interval 3600
"""

import argparse
import datetime as dt
import os
import time

import db
import engine as eng
from directory import DIRECTORY

SLICE_SIZE = int(os.environ.get("INLET_SLICE_SIZE", "120"))       # max companies per run
TIME_BUDGET = int(os.environ.get("INLET_TIME_BUDGET", "1200"))  # seconds, ~23 min
STALE_DAYS = int(os.environ.get("INLET_STALE_DAYS", "4"))       # expire roles not seen in N days


def _company_dict(c):
    base = {"name": c.name, "tier": c.tier or 3, "id": c.id, "platform": c.platform}
    if c.platform == "workday" and c.wd_tenant:
        base["workday"] = {"tenant": c.wd_tenant, "pod": c.wd_pod, "site": c.wd_site}
    else:
        base["slug"] = c.slug
    return base


def _seed_if_empty(s):
    if s.query(db.Company).count() > 0:
        return
    for c in DIRECTORY:
        if "workday" in c:
            w = c["workday"]
            s.add(db.Company(name=c["name"], tier=c["tier"], platform="workday",
                             wd_tenant=w["tenant"], wd_pod=w["pod"], wd_site=w["site"],
                             active=True, source="seed"))
        else:
            s.add(db.Company(name=c["name"], tier=c["tier"], platform="auto",
                             slug=c["slug"], active=True, source="seed"))
    s.commit()


def _demo_jobs():
    def ago(d):
        return (dt.date.today() - dt.timedelta(days=d)).strftime("%Y-%m-%d")
    return [
        ({"name": "Cyderes", "tier": 1, "id": -1},
         eng._job("Junior SOC Analyst", "Remote, Canada", "https://example.com/1", ago(2),
                  "Monitor SIEM alerts, triage and incident response. 0-2 years. CompTIA Security+.")),
        ({"name": "RBC", "tier": 2, "id": -2},
         eng._job("IT Risk Analyst", "Toronto, Ontario", "https://example.com/2", ago(1),
                  "Assess technology and cyber risk, governance and controls. 1-2 years.")),
    ]


def refresh(demo=False):
    db.init_db()
    started = time.time()
    s = db.Session()
    try:
        # remove legacy roles from the old full-wipe design (they carry no company_id)
        s.query(db.Role).filter(db.Role.company_id.is_(None)).delete(synchronize_session=False)
        s.commit()

        if demo:
            for c, j in _demo_jobs():
                r = eng.process(j, c)
                if r:
                    s.add(db.Role(company_id=c["id"], **r))
            s.commit()
            print("demo: wrote sample roles")
            return

        _seed_if_empty(s)
        companies = s.query(db.Company).filter(db.Company.active == True).all()
        # oldest-checked first (never-checked count as oldest) -> fair rotation.
        # normalise timestamps so tz-aware and naive values sort together.
        def _sort_key(c):
            lc = c.last_checked
            if lc is None:
                return float("-inf")           # never checked -> refresh first
            if lc.tzinfo is not None:
                lc = lc.replace(tzinfo=None)
            return (lc - dt.datetime(1970, 1, 1)).total_seconds()
        companies.sort(key=_sort_key)

        processed, ok, failed, wrote = 0, [], [], 0
        for c in companies:
            if processed >= SLICE_SIZE or (time.time() - started) > TIME_BUDGET:
                break
            cd = _company_dict(c)
            # roles we already have for this company: reused so slow feeds skip detail fetches
            known = {r.url: r.description for r in
                     s.query(db.Role.url, db.Role.description).filter(db.Role.company_id == c.id)}
            jobs = eng.pull_company(cd, known=known)
            if jobs:
                rows = [eng.process(j, cd) for j in jobs]
                rows = [r for r in rows if r]
                s.query(db.Role).filter(db.Role.company_id == c.id).delete(synchronize_session=False)
                for r in rows:
                    s.add(db.Role(company_id=c.id, **r))
                c.roles_found = len(rows)
                wrote += len(rows)
                ok.append(c.name)
            else:
                failed.append(c.name)          # leave existing roles untouched
            c.last_checked = dt.datetime.utcnow()
            processed += 1
            s.commit()                          # persist progress per company

        # expiry catch-all: drop roles not refreshed within STALE_DAYS
        cutoff = dt.datetime.utcnow() - dt.timedelta(days=STALE_DAYS)
        swept = s.query(db.Role).filter(db.Role.captured_at < cutoff).delete(synchronize_session=False)
        total = s.query(db.Role).count()
        remaining = s.query(db.Company).filter(
            db.Company.active == True,
            (db.Company.last_checked.is_(None)) | (db.Company.last_checked < cutoff)
        ).count()
        s.add(db.Run(status="ok", role_count=total, companies_ok=ok, companies_failed=failed))
        s.commit()

        secs = round(time.time() - started, 1)
        print(f"[{dt.datetime.now():%Y-%m-%d %H:%M}] slice of {processed} companies "
              f"({len(ok)} ok, {len(failed)} no feed) in {secs}s")
        print(f"  wrote {wrote} roles, swept {swept} stale; table now holds {total} roles")
        return total
    finally:
        s.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Refresh Inlet roles (incremental)")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=3600)
    args = ap.parse_args()

    if args.loop:
        print(f"Worker loop, every {args.interval}s. Ctrl+C to stop.")
        while True:
            try:
                refresh(demo=args.demo)
            except Exception as e:
                print(f"  refresh error: {e}")
            time.sleep(args.interval)
    else:
        refresh(demo=args.demo)
