"""Inlet v3: lossless, read-only collection and classification boundary.

This module never writes to production. Use it to stage normalized postings,
inspect rejected candidates, and test matching without destroying raw jobs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True)
class RawPosting:
    source_company: str
    source_url: str
    title: str
    location: str
    description: str
    posted: str
    collected_at: str
    source_platform: str
    identity: str


def canonical_url(value: str) -> str:
    value = (value or "").strip()
    parsed = urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError("A valid http(s) job URL is required")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", ""))


def normalize(company: dict[str, Any], job: dict[str, Any], *, collected_at: str | None = None) -> RawPosting:
    url = canonical_url(job.get("url", ""))
    company_name = str(company.get("name") or "").strip()
    title = str(job.get("title") or "").strip()
    if not company_name or not title:
        raise ValueError("Company and job title are required")
    identity = sha256((company_name.casefold() + "|" + url).encode()).hexdigest()
    return RawPosting(
        source_company=company_name,
        source_url=url,
        title=title,
        location=str(job.get("location") or "").strip(),
        description=str(job.get("text") or job.get("description") or "").strip(),
        posted=str(job.get("posted") or ""),
        collected_at=collected_at or datetime.now(timezone.utc).isoformat(),
        source_platform=str(company.get("platform") or "unknown"),
        identity=identity,
    )


def collect_batch(
    companies: list[dict[str, Any]],
    fetch: Callable[[dict[str, Any]], list[dict[str, Any]]],
    *,
    collected_at: str | None = None,
) -> dict[str, Any]:
    """Fetch and preserve postings without field, seniority, or location filtering.

    Failed and empty feeds are distinguishable. No database writes or deletion.
    """
    records: dict[str, RawPosting] = {}
    company_results = []
    invalid = []
    for company in companies:
        name = str(company.get("name") or "unknown")
        try:
            jobs = fetch(company)
            if jobs is None:
                raise ValueError("Fetcher returned None")
            valid = 0
            for job in jobs:
                try:
                    item = normalize(company, job, collected_at=collected_at)
                    records[item.identity] = item
                    valid += 1
                except (ValueError, TypeError, AttributeError) as exc:
                    invalid.append({"company": name, "reason": str(exc)})
            company_results.append({"company": name, "status": "ok" if jobs else "empty",
                                    "fetched": len(jobs), "valid": valid})
        except Exception as exc:
            company_results.append({"company": name, "status": "error",
                                    "error_type": type(exc).__name__, "fetched": 0, "valid": 0})
    return {
        "schema_version": 1,
        "postings": [asdict(x) for x in records.values()],
        "companies": company_results,
        "invalid": invalid,
        "stats": {
            "companies_attempted": len(companies),
            "companies_ok": sum(x["status"] == "ok" for x in company_results),
            "companies_empty": sum(x["status"] == "empty" for x in company_results),
            "companies_error": sum(x["status"] == "error" for x in company_results),
            "raw_postings": sum(x["fetched"] for x in company_results),
            "unique_postings": len(records),
            "invalid_postings": len(invalid),
        },
    }


def save_staging_json(result: dict[str, Any], path: str | Path) -> None:
    """Explicitly write only a local JSON staging artifact, never the live roles table."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
