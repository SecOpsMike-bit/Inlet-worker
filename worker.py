"""
worker.py  -  field-aware refresh worker for Inlet.

Reads the company directory from the database (the `companies` table, populated
by discovery.py), classifies every role into a field, scores it, and writes the
results to the `roles` table. Runs on a schedule.

    python worker.py            # live
    python worker.py --demo     # sample roles, no network
    python worker.py --loop --interval 10800
"""

import argparse
import datetime as dt
import time

import db
import engine as eng
from directory import DIRECTORY


def _company_dict(c):
    """Turn a Company row into the dict engine.pull_company expects."""
    base = {"name": c.name, "tier": c.tier or 3}
    if c.platform == "workday" and c.wd_tenant:
        base["workday"] = {"tenant": c.wd_tenant, "pod": c.wd_pod, "site": c.wd_site}
    else:
        base["slug"] = c.slug
    return base


def load_companies():
    """Read active companies from the DB; seed from directory.py the first time."""
    s = db.Session()
    try:
        rows = s.query(db.Company).filter(db.Company.active == True).all()
        if not rows:
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
            rows = s.query(db.Company).filter(db.Company.active == True).all()
        return [_company_dict(c) for c in rows]
    finally:
        s.close()


def _demo_jobs():
    def ago(d):
        return (dt.date.today() - dt.timedelta(days=d)).strftime("%Y-%m-%d")
    return [
        ({"name": "Cyderes", "tier": 1},
         eng._job("Junior SOC Analyst", "Remote, Canada", "https://example.com/1", ago(2),
                  "Monitor SIEM alerts, triage and incident response, threat hunting. Splunk, EDR, MITRE ATT&CK. Entry level.")),
        ({"name": "Shopify", "tier": 3},
         eng._job("Backend Software Engineer", "Remote, Canada", "https://example.com/2", ago(4),
                  "Build and scale backend payment systems. Ruby, Go, distributed systems, APIs. Mid level.")),
        ({"name": "Kinaxis", "tier": 3},
         eng._job("Technical Project Manager", "Ottawa, Ontario", "https://example.com/3", ago(3),
                  "Lead cross-functional delivery of supply chain software. Stakeholder management, Agile, roadmaps.")),
        ({"name": "RBC", "tier": 2},
         eng._job("Data Analyst, Risk", "Toronto, Ontario", "https://example.com/5", ago(5),
                  "SQL, Power BI, build dashboards and reporting for risk teams. Associate level.")),
    ]


def refresh(demo=False):
    db.init_db()
    started = time.time()
    rows, ok, failed = [], [], []

    if demo:
        for c, j in _demo_jobs():
            r = eng.process(j, c) if j else None
            if r:
                rows.append(r)
        ok = ["(demo)"]
    else:
        companies = load_companies()
        for c in companies:
            jobs = eng.pull_company(c)
            if jobs:
                ok.append(c["name"])
                for j in jobs:
                    r = eng.process(j, c)
                    if r:
                        rows.append(r)
            else:
                failed.append(c["name"])

    s = db.Session()
    try:
        s.query(db.Role).delete()
        for r in rows:
            s.add(db.Role(**r))
        s.add(db.Run(status="ok", role_count=len(rows), companies_ok=ok, companies_failed=failed))
        s.commit()
    finally:
        s.close()

    by_field = {}
    for r in rows:
        by_field[r["field"]] = by_field.get(r["field"], 0) + 1
    secs = round(time.time() - started, 1)
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M}] wrote {len(rows)} roles "
          f"from {len(ok)} companies ({len(failed)} no feed) in {secs}s")
    if by_field:
        print("  by field: " + ", ".join(f"{k} {v}" for k, v in sorted(by_field.items())))
    return len(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Refresh Inlet roles")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=10800)
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
