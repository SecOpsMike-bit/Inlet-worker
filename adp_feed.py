"""Read-only public ADP Workforce Now recruitment feed.

Only reads the public, anonymous career-centre job-requisitions endpoint
linked from an employer's own careers page. Does not use ADP's authenticated
client/partner API, applicant records, or private/internal career centres.

GoSecure employer-linked board and public list verified live 2026-10-13.
"""

import html
import json
import re
import urllib.parse
import urllib.request

ADP_HOST = "workforcenow.adp.com"
BOARD_PATH = "/mascsr/default/mdf/recruitment/recruitment.html"
API_BASE = (
    "https://workforcenow.adp.com/mascsr/default/"
    "careercenter/public/events/staffing/v1/job-requisitions"
)
EXTERNAL_CAREER_CENTRE = "19000101_000001"
PAGE_SIZE = 20


def _clean(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _tenant(board_url):
    parsed = urllib.parse.urlsplit(board_url or "")
    if (parsed.scheme != "https" or parsed.hostname != ADP_HOST
            or parsed.path != BOARD_PATH):
        raise ValueError("Unverified ADP recruitment board URL")
    params = urllib.parse.parse_qs(parsed.query)
    cid = (params.get("cid") or [""])[0]
    ccid = (params.get("ccId") or [EXTERNAL_CAREER_CENTRE])[0]
    if not re.fullmatch(r"[a-fA-F0-9-]{36}", cid):
        raise ValueError("Invalid ADP career-centre ID")
    # The employer-linked public URL does not specify ccId. Only the
    # verified external career centre is permitted, never an internal board.
    if ccid != EXTERNAL_CAREER_CENTRE:
        raise ValueError("Only ADP's public external career centre is supported")
    return cid, ccid


def _api_url(cid, ccid, skip=1, item_id=None):
    base = API_BASE
    if item_id is not None:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{3,80}", str(item_id)):
            raise ValueError("Invalid ADP public requisition ID")
        base += "/" + urllib.parse.quote(str(item_id), safe="")
    params = {"cid": cid, "ccId": ccid}
    if item_id is None:
        params.update({"$skip": skip, "$top": PAGE_SIZE})
    else:
        params.update({"lang": "en_US", "locale": "en_US"})
    return base + "?" + urllib.parse.urlencode(params)


def _posting_url(cid, ccid, item_id, external_id):
    query = {"cid": cid, "ccId": ccid, "lang": "en_US", "type": "JS",
             "jobId": external_id or item_id, "jwId": item_id}
    return "https://" + ADP_HOST + BOARD_PATH + "?" + urllib.parse.urlencode(query)


def _external_id(row):
    for field in ((row.get("customFieldGroup") or {}).get("stringFields") or []):
        if (field.get("nameCode") or {}).get("codeValue") == "ExternalJobID":
            value = str(field.get("stringValue") or "").strip()
            if value:
                return value
    return None


def _posted(row):
    direct = row.get("postDate")
    if isinstance(direct, str) and re.match(r"^\d{4}-\d{2}-\d{2}", direct):
        return direct[:10]
    for field in ((row.get("customFieldGroup") or {}).get("dateFields") or []):
        if (field.get("nameCode") or {}).get("codeValue") == "PostingDate":
            value = str(field.get("dateValue") or "")
            if re.match(r"^\d{4}-\d{2}-\d{2}", value):
                return value[:10]
    return ""


def _location(row):
    labels = []
    for loc in row.get("requisitionLocations") or []:
        if not isinstance(loc, dict):
            continue
        code = loc.get("nameCode") or {}
        label = str(code.get("shortName") or code.get("longName") or "").strip()
        if not label:
            addr = loc.get("address") or {}
            country = (addr.get("country") or {}).get("codeValue") or ""
            label = ", ".join(str(x).strip() for x in (
                addr.get("cityName"),
                (addr.get("countrySubdivisionLevel1") or {}).get("codeValue"),
                country,
            ) if x)
        if label and label not in labels:
            labels.append(label)
    return " / ".join(labels) if labels else "Location unverified"


def _get_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "GetInlets/3.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=18) as response:
        return json.load(response)


def fetch_adp(board_url, cap=100, max_pages=10, detail_cap=20, get_json=None):
    """Fetch bounded public ADP listings and best-effort full descriptions.

    A failed list request propagates; failed detail enrichment keeps a
    verified posting but never invents a description.
    """
    cid, ccid = _tenant(board_url)
    get_json = get_json or _get_json
    jobs, seen, skip = [], set(), 1
    for _ in range(max_pages):
        payload = get_json(_api_url(cid, ccid, skip))
        if not isinstance(payload, dict) or not isinstance(
                payload.get("jobRequisitions"), list):
            raise ValueError("Unexpected ADP public job-requisitions response")
        rows = payload["jobRequisitions"]
        if not rows:
            break
        fresh = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            item_id = str(row.get("itemID") or "").strip()
            title = _clean(row.get("requisitionTitle"))
            if not re.fullmatch(r"[a-zA-Z0-9_-]{3,80}", item_id) or not title:
                continue
            if item_id in seen:
                continue
            seen.add(item_id)
            fresh += 1
            jobs.append({
                "title": title,
                "location": _location(row),
                "url": _posting_url(cid, ccid, item_id, _external_id(row)),
                "posted": _posted(row),
                "text": "",
                "_item_id": item_id,
            })
            if len(jobs) >= cap:
                break
        if len(jobs) >= cap or fresh == 0:
            break
        skip += len(rows)  # ADP is one-based and advances by returned rows.
        total = (payload.get("meta") or {}).get("totalNumber")
        if isinstance(total, int) and skip > total:
            break
        if len(rows) < PAGE_SIZE:
            break

    # Enrich relevant security roles first so the V3 matcher has the real
    # requirements even when a company has many non-cyber postings.
    priority = sorted(
        jobs, key=lambda j: 0 if re.search(
            r"\b(?:security|cyber|soc|incident|threat|detection|malware)\b",
            j["title"], re.I
        ) else 1
    )
    for job in priority[:detail_cap]:
        try:
            detail = get_json(_api_url(cid, ccid, item_id=job["_item_id"]))
            if isinstance(detail, dict):
                job["text"] = _clean(detail.get("requisitionDescription"))
        except Exception:
            pass
    for job in jobs:
        job.pop("_item_id", None)
    return jobs
