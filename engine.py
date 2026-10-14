"""
engine.py  -  field-aware brain for Inlet.

Pulls roles from company feeds, classifies each into one of nine fields,
tags its level (entry / mid / senior), and scores it:
  opportunity_score  how strong, real and fresh the role is (role-quality)
  landability        how accessible it is, mostly by level
  realness           freshness / ghost filter
"""

import datetime as dt
import html as html_lib
import json
import re
import urllib.request
import urllib.error

from successfactors_feed import fetch_successfactors
from dayforce_feed import fetch_dayforce
from shopify_feed import fetch_shopify
from jibe_feed import fetch_jibe_kinaxis
from adp_feed import fetch_adp

# ============================================================ FIELDS

FIELD_PROFILES = {
    "cybersecurity": {"label": "Cybersecurity", "title": [
        "security analyst", "soc analyst", "soc engineer", "cybersecurity",
        "cyber security", "cyber", "cyber analyst", "information security", "infosec",
        "security engineer", "security operations", "security operations center",
        "threat", "grc", "governance risk", "incident response", "incident responder",
        "vulnerability", "detection engineer", "detection analyst", "appsec",
        "application security", "it risk", "cyber risk", "security risk",
        "technology risk", "it security", "security compliance", "penetration test",
        "pen test", "red team", "blue team", "identity and access", "iam ",
        "security specialist", "security consultant", "security administrator",
        "security architect", "malware analyst", "forensic", "siem"]},
    "software_engineering": {"label": "Software Engineering", "title": [
        "software engineer", "software developer", "backend", "back end", "frontend",
        "front end", "full stack", "full-stack", "developer", "devops", "sre",
        "site reliability", "programmer", "mobile engineer", "ios engineer",
        "android engineer", "platform engineer"]},
    "data_analytics": {"label": "Data & Analytics", "title": [
        "data analyst", "data scientist", "data engineer", "analytics",
        "business intelligence", "bi developer", "machine learning", "ml engineer",
        "reporting analyst"]},
    "product_management": {"label": "Product Management", "title": [
        "product manager", "product owner", "head of product", "product lead",
        "associate product manager"]},
    "project_management": {"label": "Project Management", "title": [
        "project manager", "program manager", "project coordinator", "delivery manager",
        "scrum master", "implementation manager", "project lead", "pmo"]},
    "finance_accounting": {"label": "Finance & Accounting", "title": [
        "financial analyst", "accountant", "accounting", "fp&a", "controller",
        "auditor", "accounts payable", "accounts receivable", "treasury", "finance"]},
    "marketing": {"label": "Marketing", "title": [
        "marketing", "brand", "content strategist", "seo", "sem", "growth",
        "social media", "communications", "demand generation", "campaign"]},
    "sales": {"label": "Sales", "title": [
        "account executive", "business development", "account manager",
        "sales development", "sdr", "bdr", "sales representative", "sales manager",
        "partnerships", "sales"]},
    "operations": {"label": "Operations", "title": [
        "operations", "supply chain", "logistics", "process improvement",
        "fulfilment", "fulfillment", "procurement", "ops"]},
    "customer_support": {"label": "Customer Support", "title": [
        "customer support", "customer service", "customer care", "customer success",
        "client success", "client services", "client support", "support specialist",
        "support agent", "support representative", "support analyst", "help desk",
        "helpdesk", "service desk", "technical support", "customer experience",
        "member services", "customer advocate", "contact center", "call center",
        "call centre", "customer relations"]},
}
# resolve ties in this order (more specific fields first)
FIELD_PRIORITY = ["cybersecurity", "data_analytics", "product_management",
                  "project_management", "customer_support", "software_engineering",
                  "finance_accounting", "marketing", "sales", "operations"]

SENIOR_TOKENS = ["senior", "sr ", "sr.", "lead ", "principal", "staff ", "director",
                 "head of", " vp", "vice president", "chief", " iii", " iv"]
ENTRY_TOKENS = ["junior", "jr ", "jr.", "entry", "associate", "graduate", "new grad",
                "intern", " i ", "level i", "trainee", "apprentice"]

CANADA_TERMS = ["canada", "canadian", "ontario", "toronto", "ottawa", "mississauga",
                "vancouver", "montreal", "calgary", "alberta", "quebec", "montréal",
                "british columbia", "waterloo", "hamilton", "edmonton", "winnipeg",
                "kitchener", "london, on", "halifax", "victoria", "saskatchewan",
                "manitoba", "nova scotia", "brampton", "markham", "burnaby", " on,",
                " ab,", " bc,", " qc,", " ns,"]
# a location naming any of these is not a Canadian role, even if it says "remote"
FOREIGN_TERMS = ["united states", "usa", "u.s.", "u.s ", "(us)", "us only", "us-based",
                 "us based", "remote us", "remote, us", "remote - us", "america",
                 "india", "united kingdom", " uk", "uk ", "england", "scotland",
                 "ireland", "australia", "new zealand", "germany", "france", "spain",
                 "italy", "netherlands", "poland", "romania", "portugal", "singapore",
                 "philippines", "malaysia", "japan", "china", "hong kong", "brazil",
                 "mexico", "argentina", "colombia", "south africa", "nigeria", "kenya",
                 "egypt", "uae", "dubai", "israel", "europe", "emea", "apac", "latam",
                 "asia pacific", "latin america"]
REMOTE_TERMS = ["remote", "work from home", "wfh", "anywhere"]
VAGUE_TERMS = ["competitive salary", "fast-paced environment", "talent community",
               "talent pool", "always hiring", "evergreen", "pipeline"]
FLAG_TERMS = ["security clearance", "secret clearance", "canadian citizen",
              "permanent resident required", "pr required"]

TIER_BOOST = {1: 10, 2: 0, 3: 6}
LEVEL_LANDABILITY = {"entry": 90, "mid": 70, "senior": 42}

# ============================================================ FETCHERS

def _get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "inlet/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))

def _post_json(url, payload, timeout=25):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "inlet/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))

def _strip(s):
    return re.sub(r"<[^>]+>", " ", html_lib.unescape(s or "")).strip()

def _job(title, location, url, posted, text):
    if not title or not url:
        return None
    return {"title": title.strip(), "location": (location or "").strip(),
            "url": url.strip(), "posted": posted or "", "text": (text or "").strip()}

def fetch_greenhouse(slug):
    d = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    return [_job(j.get("title"), (j.get("location") or {}).get("name", ""), j.get("absolute_url"),
                 j.get("updated_at"), _strip(j.get("content"))) for j in d.get("jobs", [])]

def fetch_lever(slug):
    d = _get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for j in d:
        cats = j.get("categories") or {}
        posted = ""
        if j.get("createdAt"):
            posted = dt.datetime.fromtimestamp(j["createdAt"] / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
        out.append(_job(j.get("text"), cats.get("location", ""), j.get("hostedUrl"),
                        posted, j.get("descriptionPlain", "")))
    return out

def fetch_ashby(slug):
    d = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    return [_job(j.get("title"), j.get("location", ""), j.get("jobUrl") or j.get("applyUrl"),
                 j.get("publishedAt", ""), _strip(j.get("descriptionHtml") or j.get("descriptionPlain")))
            for j in d.get("jobs", [])]

COUNTRY_MAP = {"ca": "Canada", "us": "United States", "usa": "United States",
               "gb": "United Kingdom", "uk": "United Kingdom", "in": "India",
               "au": "Australia", "de": "Germany", "fr": "France", "ie": "Ireland",
               "sg": "Singapore", "ph": "Philippines", "nl": "Netherlands",
               "br": "Brazil", "mx": "Mexico", "es": "Spain", "it": "Italy"}


def sr_location(loc):
    """Build a readable location string from a SmartRecruiters location object."""
    loc = loc or {}
    country = COUNTRY_MAP.get((loc.get("country") or "").lower(), loc.get("country") or "")
    parts = [loc.get("city"), loc.get("region"), country]
    s = ", ".join([x for x in parts if x])
    if loc.get("remote"):
        s = (s + ", Remote") if s else "Remote"
    return s


def fetch_smartrecruiters(slug, cap=200, known=None):
    base = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    out, offset = [], 0
    while offset < cap:
        d = _get_json(f"{base}?limit=100&offset={offset}")
        content = d.get("content", [])
        if not content:
            break
        for p in content:
            pid = p.get("id")
            url = f"https://jobs.smartrecruiters.com/{slug}/{pid}"
            if known and url in known:              # already have it: reuse, skip detail call
                text = known[url] or p.get("name", "")
            else:
                text = _sr_detail(slug, pid) or p.get("name", "")
            out.append(_job(p.get("name"), sr_location(p.get("location")), url,
                            p.get("releasedDate", ""), text))
        offset += 100
        if offset >= d.get("totalFound", 0):
            break
    return out


def _sr_detail(slug, pid):
    try:
        d = _get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{pid}")
        secs = ((d.get("jobAd") or {}).get("sections")) or {}
        keys = ["companyDescription", "jobDescription", "qualifications", "additionalInformation"]
        return " ".join(_strip((secs.get(k) or {}).get("text", "")) for k in keys).strip()
    except Exception:
        return ""


_AUTO = [("greenhouse", fetch_greenhouse), ("lever", fetch_lever),
         ("ashby", fetch_ashby), ("smartrecruiters", fetch_smartrecruiters)]

def discover(slug):
    for platform, fetch in _AUTO:
        try:
            jobs = [j for j in fetch(slug) if j]
            if jobs:
                return platform, jobs
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                continue
        except Exception:
            continue
    return None, []

# Prioritize specific SOC/MDR queries before broad keywords. Workday commonly
# limits search results to the first page; broad "security" alone can miss
# relevant junior analyst positions buried under unrelated listings.
WORKDAY_TERMS = [
    "soc analyst", "security operations", "incident response", "cybersecurity",
    "threat analyst", "managed detection", "mdr", "security analyst", "security",
    "software engineer", "developer", "data", "analyst", "product manager",
    "project manager", "finance", "accounting", "marketing", "sales", "operations",
]

def fetch_workday(tenant, pod, site, per_term=20, cap=120, known=None):
    base = f"https://{tenant}.{pod}.myworkdayjobs.com"
    cxs = f"{base}/wday/cxs/{tenant}/{site}"
    seen, out = set(), []
    for term in WORKDAY_TERMS:
        offset = 0
        while offset < per_term and len(out) < cap:
            try:
                d = _post_json(f"{cxs}/jobs",
                               {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term})
            except Exception:
                break
            posts = d.get("jobPostings", [])
            if not posts:
                break
            for p in posts:
                ext = p.get("externalPath", "")
                url = f"{base}/en-US/{site}{ext}" if ext else base
                if url in seen:
                    continue
                seen.add(url)
                if known and url in known:          # already have it: reuse, skip detail call
                    text = known[url] or p.get("title", "")
                else:
                    text = _workday_detail(cxs, ext) or p.get("title", "")
                out.append(_job(p.get("title"), p.get("locationsText", ""), url,
                                _workday_date(p.get("postedOn", "")), text))
            offset += 20
        if len(out) >= cap:
            break
    return out

def _workday_detail(cxs, ext):
    if not ext:
        return ""
    try:
        d = _get_json(f"{cxs}{ext}")
        return _strip((d.get("jobPostingInfo") or {}).get("jobDescription", ""))
    except Exception:
        return ""

def _workday_date(s):
    s = (s or "").lower()
    today = dt.date.today()
    if "today" in s:
        return today.strftime("%Y-%m-%d")
    if "yesterday" in s:
        return (today - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\+?\s*day", s)
    if m:
        return (today - dt.timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\+?\s*month", s)
    if m:
        return (today - dt.timedelta(days=30 * int(m.group(1)))).strftime("%Y-%m-%d")
    return ""

_FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever,
             "ashby": fetch_ashby, "smartrecruiters": fetch_smartrecruiters}


def pull_company(company, known=None):
    """known: {url: description} of roles already stored for this company.
    Lets Workday/SmartRecruiters skip the per-role detail fetch for unchanged roles."""
    try:
        if "workday" in company:
            w = company["workday"]
            return [j for j in fetch_workday(w["tenant"], w["pod"], w["site"], known=known) if j]
        platform = company.get("platform")
        if platform == "jibe":
            return [j for j in fetch_jibe_kinaxis() if j]
        if platform == "adp":
            return [j for j in fetch_adp(company.get("board_url")) if j]
        if platform == "shopify":
            return [j for j in fetch_shopify() if j]
        if platform == "dayforce":
            return [j for j in fetch_dayforce(company.get("slug")) if j]
        if platform == "successfactors":
            return [j for j in fetch_successfactors(company.get("board_url")) if j]
        if platform == "smartrecruiters":
            return [j for j in fetch_smartrecruiters(company["slug"], known=known) if j]
        if platform in _FETCHERS:                     # greenhouse/lever/ashby: list already has text
            return [j for j in _FETCHERS[platform](company["slug"]) if j]
        _, jobs = discover(company["slug"])           # unknown -> auto-detect
        return jobs
    except Exception:
        return []


def pull_company_diagnostic(company, workday_cap=120):
    """Fetch a company once and report whether a zero result is trustworthy.

    Returns (jobs, diagnostic). A zero-job result from an unsupported provider,
    failed HTTP request or unsuccessful auto-discovery must NEVER be interpreted
    as proof the employer has no open positions.
    """
    name = company.get("name", "Unknown")
    platform = company.get("platform", "auto")
    if "workday" in company:
        platform = "workday"
    diagnostic = {"company": name, "platform": platform, "status": "unknown",
                  "attempts": []}

    if platform == "jibe":
        try:
            jobs = fetch_jibe_kinaxis()
            diagnostic["status"] = "ok" if jobs else "empty_feed"
            return jobs, diagnostic
        except Exception as exc:
            diagnostic["status"] = "fetch_error"
            diagnostic["error"] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError):
                diagnostic["http_status"] = exc.code
            return [], diagnostic

    if platform == "adp":
        if not company.get("board_url"):
            diagnostic["status"] = "missing_board_url"
            return [], diagnostic
        try:
            jobs = fetch_adp(company["board_url"])
            diagnostic["status"] = "ok" if jobs else "empty_feed"
            return jobs, diagnostic
        except Exception as exc:
            diagnostic["status"] = "fetch_error"
            diagnostic["error"] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError):
                diagnostic["http_status"] = exc.code
            return [], diagnostic

    if platform == "shopify":
        try:
            jobs = fetch_shopify()
            diagnostic["status"] = "ok" if jobs else "empty_feed"
            return jobs, diagnostic
        except Exception as exc:
            diagnostic["status"] = "fetch_error"
            diagnostic["error"] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError):
                diagnostic["http_status"] = exc.code
            return [], diagnostic

    if platform == "dayforce":
        if not company.get("slug"):
            diagnostic["status"] = "missing_slug"
            return [], diagnostic
        try:
            jobs = fetch_dayforce(company["slug"])
            diagnostic["status"] = "ok" if jobs else "empty_feed"
            return jobs, diagnostic
        except urllib.error.HTTPError as exc:
            diagnostic["status"] = (
                "access_blocked" if exc.code in (401, 403) else "fetch_error"
            )
            diagnostic["error"] = type(exc).__name__
            diagnostic["http_status"] = exc.code
            return [], diagnostic
        except Exception as exc:
            diagnostic["status"] = "fetch_error"
            diagnostic["error"] = type(exc).__name__
            return [], diagnostic

    if platform == "successfactors":
        if not company.get("board_url"):
            diagnostic["status"] = "missing_board_url"
            return [], diagnostic
        try:
            jobs = fetch_successfactors(company.get("board_url"))
            diagnostic["status"] = "ok" if jobs else "empty_feed"
            return jobs, diagnostic
        except Exception as exc:
            diagnostic["status"] = "fetch_error"
            diagnostic["error"] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError):
                diagnostic["http_status"] = exc.code
            return [], diagnostic

    if "workday" in company:
        w = company["workday"]
        try:
            jobs = [j for j in fetch_workday(w["tenant"], w["pod"], w["site"], cap=workday_cap) if j]
            # Workday's existing fetcher handles request errors internally.
            # Zero results could therefore mean either an empty feed or an error.
            diagnostic["status"] = "ok" if jobs else "empty_or_feed_error"
            return jobs, diagnostic
        except Exception as exc:
            diagnostic["status"] = "fetch_error"
            diagnostic["error"] = type(exc).__name__
            return [], diagnostic

    slug = company.get("slug", "")
    if platform in _FETCHERS or platform == "smartrecruiters":
        fetch = fetch_smartrecruiters if platform == "smartrecruiters" else _FETCHERS[platform]
        try:
            jobs = [j for j in fetch(slug) if j]
            diagnostic["status"] = "ok" if jobs else "empty_feed"
            return jobs, diagnostic
        except Exception as exc:
            diagnostic["status"] = "fetch_error"
            diagnostic["error"] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError):
                diagnostic["http_status"] = exc.code
            return [], diagnostic

    if not slug:
        diagnostic["status"] = "missing_slug"
        return [], diagnostic

    for provider, fetch in _AUTO:
        try:
            jobs = [j for j in fetch(slug) if j]
            diagnostic["attempts"].append({"platform": provider,
                                            "status": "ok" if jobs else "empty_feed"})
            if jobs:
                diagnostic["platform"] = provider
                diagnostic["status"] = "ok"
                return jobs, diagnostic
        except Exception as exc:
            attempt = {"platform": provider, "status": "fetch_error",
                       "error": type(exc).__name__}
            if isinstance(exc, urllib.error.HTTPError):
                attempt["http_status"] = exc.code
            diagnostic["attempts"].append(attempt)
    diagnostic["status"] = "unresolved_feed"
    return [], diagnostic


# ============================================================ CLASSIFY + SCORE

import functools

# financial/business risk roles that are not cybersecurity, even if they contain "risk"
NON_CYBER_RISK = ["credit risk", "market risk", "financial risk", "operational risk",
                  "enterprise risk", "liquidity risk", "investment risk", "insurance risk",
                  "actuarial", "underwriting"]


@functools.lru_cache(maxsize=2048)
def _kw_re(kw):
    return re.compile(r"\b" + re.escape(kw.strip()) + r"\b")


def _matches(kw, text):
    return _kw_re(kw).search(text) is not None


def classify_field(title):
    t = title.lower()
    # a finance/business risk title is never cybersecurity
    cyber_blocked = any(p in t for p in NON_CYBER_RISK)
    best, best_hits, best_kw = None, 0, None
    for field in FIELD_PRIORITY:
        if field == "cybersecurity" and cyber_blocked:
            continue
        kws = FIELD_PROFILES[field]["title"]
        matched = [k for k in kws if _matches(k, t)]   # whole-word match, no substrings
        if len(matched) > best_hits:
            best, best_hits, best_kw = field, len(matched), matched[0]
    if best is None:
        return None, None, 0
    label = best_kw.title() if best_kw else FIELD_PROFILES[best]["label"]
    return best, label, best_hits

def _min_years(text):
    """Smallest years-of-experience figure mentioned in the description, if any."""
    yrs = [int(x) for x in re.findall(r"(\d+)\s*\+?\s*years?", (text or "").lower())]
    yrs = [y for y in yrs if y <= 20]
    return min(yrs) if yrs else None

def classify_level(title, text=""):
    """Title signals first, then years-of-experience from the description."""
    t = " " + title.lower() + " "
    if any(tok in t for tok in SENIOR_TOKENS):
        return "senior"
    if any(tok in t for tok in ENTRY_TOKENS):
        return "entry"
    y = _min_years(text)
    if y is not None:
        if y <= 2:
            return "entry"
        if y <= 5:
            return "mid"
        return "senior"
    return "mid"

def score_recency(posted):
    """Freshness score, 0-100. Fresh postings rank higher (early-application edge)."""
    age = _age_days(posted)
    if age is None:
        return 55
    if age <= 2:
        return 100
    if age <= 7:
        return 85
    if age <= 14:
        return 70
    if age <= 30:
        return 50
    if age <= 60:
        return 30
    return 15

# security sub-lanes that are more open to career-changers with certs
ACCESSIBLE_CYBER = ["grc", "it risk", "cyber risk", "security risk", "governance",
                    "security compliance", "soc analyst", "information security analyst",
                    "security analyst", "it security analyst", "compliance analyst"]
ENTRY_CERTS = ["security+", "sec+", "cysa", "network+", "comptia", "csap", "gsec"]

def _age_days(posted):
    if not posted:
        return None
    s = str(posted).replace("Z", "").split("T")[0].split(" ")[0]
    try:
        return (dt.date.today() - dt.datetime.strptime(s, "%Y-%m-%d").date()).days
    except ValueError:
        return None

def score_realness(title, text, posted):
    score = 100
    age = _age_days(posted)
    if age is None:
        score -= 5
    elif age <= 14:
        pass
    elif age <= 30:
        score -= 10
    elif age <= 60:
        score -= 25
    else:
        score -= 45
    blob = (title + " " + text).lower()
    score -= 8 * sum(1 for v in VAGUE_TERMS if v in blob)
    if len(text) < 300:
        score -= 15
    return max(0, score)

def location_ok(location):
    """Keep Canadian roles and genuinely unspecified-remote roles; reject foreign ones.
    A role that names another country is rejected even when it also says 'remote'."""
    loc = (location or "").lower().strip()
    if not loc:
        return True                                  # unknown location -> keep (conservative)
    if any(t in loc for t in CANADA_TERMS):
        return True                                  # names a Canadian place -> keep
    if any(t in loc for t in FOREIGN_TERMS):
        return False                                 # names another country -> reject
    if any(t in loc for t in REMOTE_TERMS):
        return True                                  # remote with no foreign country -> keep
    return False                                     # a named non-Canadian place -> reject

def process(job, company):
    """Turn one raw job into a scored, field-tagged row, or None to skip."""
    if not location_ok(job["location"]):
        return None
    field, role_label, hits = classify_field(job["title"])
    if field is None:
        return None
    level = classify_level(job["title"], job["text"])
    realness = score_realness(job["title"], job["text"], job["posted"])
    if realness < 45:
        return None
    recency = score_recency(job["posted"])
    field_fit = min(100, 55 + 15 * hits)
    # best-match ranking now blends fit, quality, and freshness (early-application edge)
    opportunity = min(100, round(0.4 * field_fit + 0.3 * realness + 0.3 * recency)
                      + TIER_BOOST.get(company["tier"], 0))
    # landability = how likely THIS profile lands it: level, plus accessible cert-friendly lanes
    blob = (job["title"] + " " + job["text"]).lower()
    t = job["title"].lower()
    landability = LEVEL_LANDABILITY[level]
    if level != "senior" and any(k in t for k in ACCESSIBLE_CYBER):
        landability += 8
    if any(c in blob for c in ENTRY_CERTS):
        landability += 5
    if realness >= 80:
        landability += 3
    landability = min(100, landability)
    flags = [f for f in FLAG_TERMS if f in (job["title"] + " " + job["text"]).lower()]
    posted_date = None
    s = str(job["posted"]).split("T")[0].split(" ")[0]
    try:
        posted_date = dt.datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        posted_date = None
    return {"company": company["name"], "tier": company["tier"], "field": field,
            "role_label": role_label, "title": job["title"], "location": job["location"],
            "url": job["url"], "posted": posted_date, "opportunity_score": opportunity,
            "landability": landability, "realness": realness, "level": level,
            "flags": flags, "description": job["text"][:2000]}
