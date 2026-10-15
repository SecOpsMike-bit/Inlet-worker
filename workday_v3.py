"""Strict Workday adapter for Inlet v3 staging.

Unlike the legacy fetch_workday, request errors propagate to the collector.
A successful zero-posting response is distinguished from a failed request.
"""
from __future__ import annotations

import engine

SEARCH_TERMS = tuple(engine.WORKDAY_TERMS)


def fetch_workday_strict(tenant: str, pod: str, site: str, *, per_term: int = 20,
                         cap: int = 120) -> list[dict]:
    if not all((tenant, pod, site)):
        raise ValueError("Workday tenant, pod and site are required")
    base = f"https://{tenant}.{pod}.myworkdayjobs.com"
    cxs = f"{base}/wday/cxs/{tenant}/{site}"
    seen: set[str] = set()
    out: list[dict] = []
    for term in SEARCH_TERMS:
        offset = 0
        while offset < per_term and len(out) < cap:
            # Deliberately do not catch HTTP errors, timeouts or malformed JSON.
            response = engine._post_json(
                f"{cxs}/jobs",
                {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term},
            )
            posts = response.get("jobPostings")
            if not isinstance(posts, list):
                raise ValueError("Workday response lacks jobPostings array")
            if not posts:
                break
            for post in posts:
                external = post.get("externalPath") or ""
                if not external:
                    continue
                url = f"{base}/en-US/{site}{external}"
                if url in seen:
                    continue
                seen.add(url)
                # Detail fetching is best effort; listing retrieval is strict.
                description = engine._workday_detail(cxs, external) or post.get("title", "")
                job = engine._job(
                    post.get("title"), post.get("locationsText", ""), url,
                    engine._workday_date(post.get("postedOn", "")), description,
                )
                if job:
                    out.append(job)
            offset += 20
            if len(posts) < 20:
                break
        if len(out) >= cap:
            break
    return out
