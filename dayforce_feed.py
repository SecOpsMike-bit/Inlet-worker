"""Read-only adapter for the documented anonymous Dayforce JobFeeds endpoint.

The employer's own public career site links to Dayforce. Unlike Dayforce's
newer geo-search API (which can return 403), JobFeeds is an officially
documented public GET feed when the employer has enabled it.
No authentication or candidate/application endpoints are used.
"""

import html
import re
import urllib.request
from urllib.parse import quote, urlsplit


COUNTRIES = {
    "ca": "Canada", "can": "Canada", "canada": "Canada",
    "us": "United States", "usa": "United States",
    "ie": "Ireland", "irl": "Ireland", "gb": "United Kingdom",
    "uk": "United Kingdom", "in": "India", "de": "Germany",
    "au": "Australia", "ph": "Philippines",
}


def _clean(value):
    return re.sub(r"\\s+", " ", html.unescape(re.sub(
        r"<[^>]+>", " ", str(value or "")
    ))).strip()


def _location(row):
    country_raw = str(row.get("Country") or "").strip()
    country = COUNTRIES.get(country_raw.lower(), country_raw)
    parts = [
        str(row.get("City") or "").strip(),
        str(row.get("State") or "").strip(),
        country,
    ]
    location = ", ".join(x for x in parts if x)
    if not location:
        # Do not let missing structured geography become an assumed
        # Canada-wide remote opening via description keyword matching.
        return "Location unverified"
    return location


def _safe_url(raw, namespace):
    url = str(raw or "").strip()
    parsed = urlsplit(url)
    if (parsed.scheme == "https" and parsed.hostname and
            (parsed.hostname == "dayforcehcm.com" or
             parsed.hostname.endswith(".dayforcehcm.com")) and
            ("/" + namespace.lower() + "/") in parsed.path.lower()):
        return url
    return None


def parse_jobfeeds(payload, namespace, cap=200):
    """Normalize public feed records without guessing eligibility or locations."""
    if not isinstance(payload, list):
        raise ValueError("Unexpected Dayforce JobFeeds response shape")
    out, seen = [], set()
    for row in payload:
        if not isinstance(row, dict):
            continue
        title = _clean(row.get("Title"))
        url = _safe_url(row.get("JobDetailsUrl"), namespace)
        if not url:
            url = _safe_url(row.get("ApplyUrl"), namespace)
        if not url:
            ref = row.get("ReferenceNumber")
            if ref is not None and str(ref).isdigit():
                url = (
                    "https://jobs.dayforcehcm.com/en-US/" +
                    quote(namespace) + "/CANDIDATEPORTAL/jobs/" + str(ref)
                )
        if not title or not url or url in seen:
            continue
        seen.add(url)
        posted = str(row.get("DatePosted") or "").split("T")[0]
        out.append({
            "title": title,
            "location": _location(row),
            "url": url,
            "posted": posted,
            "text": _clean(row.get("Description")),
        })
        if len(out) >= cap:
            break
    return out


def fetch_dayforce(namespace, cap=200, get_json=None):
    """Fetch only public employer job listings from the official GET JobFeeds."""
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", namespace or ""):
        raise ValueError("Invalid Dayforce employer namespace")
    url = (
        "https://www.dayforcehcm.com/api/" + quote(namespace) +
        "/V1/JobFeeds"
    )
    if get_json is None:
        import json
        req = urllib.request.Request(url, headers={
            "Accept": "application/json", "User-Agent": "GetInlets/1.0"
        })
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.load(response)
    else:
        payload = get_json(url)
    return parse_jobfeeds(payload, namespace, cap=cap)
