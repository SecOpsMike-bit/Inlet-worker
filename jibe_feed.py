"""Public iCIMS/Jibe careers adapter for Kinaxis' employer-hosted job API.

The public /api/jobs endpoint is distinct from iCIMS' credentialed partner API.
Verified live on 2026-10-13: join.kinaxis.com/api/jobs?page=1 returns
{"jobs": [{"data": {...}}], "totalCount": 108, ...}, 10 postings/page.
"""

import html
import json
import re
import urllib.request

HOST = "https://join.kinaxis.com"
JOBS_API = HOST + "/api/jobs?page={page}"


def _fetch_page(page):
    req = urllib.request.Request(
        JOBS_API.format(page=page),
        headers={"User-Agent": "Mozilla/5.0 (compatible; GetInlets/3.0)",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def _clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value or ""))).strip()


def _location(data):
    parts = [data.get("city"), data.get("state"), data.get("country")]
    location = ", ".join(str(x).strip() for x in parts if x)
    return location or (data.get("full_location") or data.get("short_location")
                        or data.get("location_name") or "").strip()


def fetch_jibe_kinaxis(cap=120, max_pages=12):
    """Fetch only public searchable vacancies; preserve full descriptions.

    Failure propagates to diagnostic fetch_error, rather than pretending an
    inaccessible board means the employer has no vacancies.
    """
    jobs, seen = [], set()
    for page in range(1, max_pages + 1):
        response = _fetch_page(page)
        if not isinstance(response, dict) or not isinstance(response.get("jobs"), list):
            raise ValueError("Unexpected Kinaxis Jibe jobs response")
        records = response["jobs"]
        if not records:
            break
        for entry in records:
            data = entry.get("data", {}) if isinstance(entry, dict) else {}
            if not isinstance(data, dict):
                continue
            if data.get("internal") is True or data.get("searchable") is False:
                continue
            slug = str(data.get("slug") or data.get("req_id") or "").strip()
            if not re.fullmatch(r"\d{2,10}", slug) or slug in seen:
                continue
            title = _clean(data.get("title"))
            if not title:
                continue
            seen.add(slug)
            posted = str(data.get("posted_date") or "").strip()
            text = _clean(data.get("description"))
            jobs.append({
                "title": title,
                "location": _location(data),
                "url": f"{HOST}/jobs/{slug}?lang=en-us",
                "posted": posted,
                "text": text,
            })
            if len(jobs) >= cap:
                return jobs
        total = response.get("totalCount")
        if isinstance(total, int) and page * len(records) >= total:
            break
    return jobs
