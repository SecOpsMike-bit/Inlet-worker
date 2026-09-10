"""Candidate-first cybersecurity matching for Inlet.

Michael Match v2 keeps Inlet's generic field engine for every other career lane,
but makes cybersecurity ranking answer a more useful question:

    Is this a realistic SOC / MDR / incident-response role for this profile?

The profile is intentionally explicit and auditable rather than AI-generated at
runtime.  It can later be moved to user configuration / database storage once the
scoring behaviour is proven.
"""

import re

import engine as eng

# Capture the original before worker_v2 monkey-patches engine.process.
_base_process = eng.process


# ---------------------------------------------------------------------------
# Target lane

TARGET_TITLE_SIGNALS = [
    ("SOC Analyst", 16, ("soc analyst", "security operations center analyst")),
    ("Security Operations Analyst", 16, ("security operations analyst",)),
    ("Incident Response Analyst", 16, ("incident response analyst", "incident responder")),
    ("MDR Analyst", 16, ("mdr analyst", "managed detection and response analyst")),
    ("Cyber Security Analyst", 14, ("cybersecurity analyst", "cyber security analyst", "cyber analyst")),
    ("Detection Analyst", 14, ("detection analyst", "threat detection analyst", "detection and response analyst",
                               "detection & response analyst", "cyber defense analyst", "cyber defence analyst")),
    ("Falcon Complete Analyst", 14, ("falcon complete",)),
    ("Information Security Analyst", 12, ("information security analyst", "it security analyst")),
    ("Security Analyst", 12, ("junior security analyst", "security analyst")),
    ("Security Operations Specialist", 12, ("security operations specialist",)),
    ("Security Specialist", 10, ("security specialist",)),
    ("Threat Analyst", 8, ("threat analyst",)),
    ("Monitoring Analyst", 8, ("security monitoring analyst", "monitoring analyst")),
    ("Security Consultant", 6, ("security consultant", "cybersecurity consultant", "cyber security consultant")),
]

# These are valid cybersecurity careers, but not the lane this profile is targeting.
OFF_LANE_TITLE_TERMS = (
    "security architect", "cybersecurity architect", "cloud security architect",
    "application security", "appsec", "product security", "devsecops",
    "penetration tester", "penetration test", "pen tester", "red team", "red-team",
    "offensive security", "iam analyst", "identity and access", "identity governance",
    "grc analyst", "governance risk", "security compliance", "compliance analyst",
    "privacy analyst", "security auditor", "cyber audit", "risk analyst",
    "security awareness", "vulnerability management analyst",
)

CYBER_OPS_EVIDENCE = (
    "siem", "edr", "xdr", "security operations center", "soc", "incident response",
    "incident handling", "security alert", "alert triage", "threat detection",
    "malware", "phishing", "crowdstrike", "sentinel", "splunk", "defender",
    "ids/ips", "intrusion detection", "intrusion prevention",
)


# ---------------------------------------------------------------------------
# Candidate skill profile.  Each group is scored once even if several synonyms hit.

SKILL_GROUPS = [
    ("Microsoft Sentinel", 12, ("microsoft sentinel", "azure sentinel")),
    ("Splunk", 10, ("splunk",)),
    ("CrowdStrike Falcon", 10, ("crowdstrike", "falcon edr", "falcon complete")),
    ("MDR/MSSP/SOC", 10, ("managed detection and response", "managed detection", "mdr",
                            "managed security services", "managed security service", "mssp",
                            "security operations center", "soc analyst", "soc environment")),
    ("SIEM/XDR/EDR", 8, ("siem", "xdr", "edr", "security information and event management")),
    ("Alert triage & investigation", 8, ("alert triage", "security alerts", "event investigation",
                                             "investigate security", "threat analysis", "triage activities",
                                             "triage", "security investigation", "incident investigation")),
    ("Incident response & escalation", 8, ("incident response", "incident handling", "incident escalation",
                                                "escalation management", "containment", "remediation requirements",
                                                "cyber incident", "security incident", "incident remediation",
                                                "remediate", "resolve cyber incidents")),
    ("Detection/SIEM tuning", 7, ("siem tuning", "detection tuning", "rule tuning", "analytics rule",
                                      "correlation rule", "false positive", "use case development",
                                      "detection engineering")),
    ("Microsoft Defender", 6, ("microsoft defender", "defender for endpoint", "mde", "defender")),
    ("Ticket/SLA lifecycle", 6, ("ticket", "case management", "service desk", "sla",
                                     "service level agreement", "case documentation")),
    ("Phishing & malware", 6, ("phishing", "malware")),
    ("Vulnerability/remediation", 5, ("vulnerability assessment", "vulnerability management",
                                          "vulnerability scanning", "remediation")),
    ("Client-facing security support", 5, ("client support", "customer support", "client-facing",
                                                "customer-facing", "client communication", "client stakeholders",
                                                "trusted advisor", "knowledge transfer")),
    ("Windows/Linux", 4, ("windows", "linux")),
    ("Network security", 4, ("ids/ips", "intrusion detection", "intrusion prevention", "firewall", "vpn")),
    ("MITRE ATT&CK", 4, ("mitre att&ck", "mitre attack")),
    ("Documentation/playbooks", 4, ("playbook", "runbook", "sop", "standard operating procedure",
                                         "technical documentation", "document findings")),
    ("Networking fundamentals", 3, ("tcp/ip", "dns", "http", "smtp", "routing", "switching")),
    ("Threat intelligence", 3, ("threat intelligence", "ioc", "indicator of compromise", "ttp")),
    ("Security certifications", 3, ("security+", "cysa+", "network+", "comptia", "gsec", "gcih", "sc-200")),
    ("Python", 3, ("python",)),
]


# ---------------------------------------------------------------------------
# Location profile

GTA_TERMS = (
    "toronto", "north york", "scarborough", "etobicoke", "mississauga", "brampton",
    "markham", "vaughan", "richmond hill", "pickering", "ajax", "whitby", "oshawa",
    "oakville", "milton", "burlington",
)

NEARBY_ON_TERMS = (
    "st. jacobs", "st jacobs", "waterloo", "kitchener", "cambridge", "guelph", "hamilton",
)

OUTSIDE_ON_TERMS = (
    "alberta", "british columbia", "quebec", "québec", "manitoba", "saskatchewan",
    "nova scotia", "new brunswick", "newfoundland", "prince edward island", "yukon",
    "northwest territories", "nunavut", "calgary", "edmonton", "vancouver", "victoria",
    "montreal", "montréal", "winnipeg", "halifax", " ab", " bc", " qc", " mb", " sk", " ns",
)

NATIONWIDE_REMOTE = (
    "anywhere in canada", "across canada", "throughout canada", "remote anywhere in canada",
    "canada-wide remote", "nationwide remote",
)


# ---------------------------------------------------------------------------
# Helpers


def _normalise(text):
    return " " + re.sub(r"\s+", " ", (text or "").lower()).strip() + " "


def _has(blob, term):
    """Whole-ish phrase matching while tolerating punctuation around terms."""
    term = term.lower().strip()
    if not term:
        return False
    acronym_terms = {"soc", "mdr", "mssp", "siem", "xdr", "edr", "sop", "ioc", "ttp", "vpn", "dns", "http", "smtp"}
    if term in acronym_terms:
        plural = r"s?" if term in {"sop", "ioc", "ttp"} else ""
        return re.search(r"(?<![a-z0-9])" + re.escape(term) + plural + r"(?![a-z0-9])", blob) is not None
    return term in blob


def _count_ops_evidence(blob):
    return sum(1 for term in CYBER_OPS_EVIDENCE if _has(blob, term))


def _title_lane(title, text):
    """Return (lane label, title bonus) or (None, 0) when this is not our cyber lane."""
    t = _normalise(title)
    blob = _normalise((title or "") + " " + (text or ""))

    # Engineering is intentionally excluded from this profile's search unless the
    # employer actually titles it as an analyst role as well.
    if "engineer" in t and "analyst" not in t:
        return None, 0
    if any(term in t for term in OFF_LANE_TITLE_TERMS):
        return None, 0

    ops_evidence = _count_ops_evidence(blob)
    for label, bonus, phrases in TARGET_TITLE_SIGNALS:
        if any(phrase in t for phrase in phrases):
            # Broad titles such as Security Specialist / Threat Analyst / Consultant
            # need evidence that the job is really blue-team operations.
            if label in {"Security Specialist", "Threat Analyst", "Monitoring Analyst", "Security Consultant",
                         "Security Analyst", "Information Security Analyst", "Cyber Security Analyst"}:
                if ops_evidence < 2:
                    return None, 0
            return label, bonus
    return None, 0


def _required_years(text):
    """Extract candidate-facing experience requirements, avoiding company-history numbers."""
    s = _normalise(text)
    found = []
    patterns = [
        # "minimum of 5 years ...", "you have 3+ years ...", "requires 4 years ..."
        r"(?:minimum(?:\s+of)?|at\s+least|required|requires|requirement[s]?|must\s+have|you\s+(?:have|bring|possess)|candidates?\s+(?:have|with))[^.;\n]{0,90}?(\d+)\s*\+?\s*years?",
        # "3+ years of relevant experience", "2 years cybersecurity experience"
        r"(\d+)\s*\+?\s*years?(?:\s+of)?\s+(?:relevant\s+|professional\s+|hands[- ]on\s+)?(?:cybersecurity\s+|cyber\s+security\s+|security\s+|soc\s+|information\s+security\s+|incident\s+response\s+|it\s+|technology\s+|technical\s+)?experience",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, s):
            y = int(m.group(1))
            if 0 <= y <= 20:
                found.append(y)
    return max(found) if found else None


def _skill_match(text):
    blob = _normalise(text)
    matched = []
    points = 0
    for label, weight, terms in SKILL_GROUPS:
        if any(_has(blob, term) for term in terms):
            matched.append(label)
            points += weight
    return points, matched


def _location_fit(location, text):
    """Return 0 for incompatible location, otherwise a 0-100 convenience score."""
    loc = _normalise(location)
    blob = _normalise((location or "") + " " + (text or ""))

    if any(term in loc for term in GTA_TERMS):
        return 100
    if any(term in loc for term in NEARBY_ON_TERMS):
        return 78

    remote = any(term in blob for term in (" remote ", "work from home", "wfh", "fully remote"))
    nationwide = any(term in blob for term in NATIONWIDE_REMOTE)
    outside_on = any(term in loc for term in OUTSIDE_ON_TERMS)

    if remote:
        if outside_on and not nationwide:
            return 0                         # e.g. Canada - Remote AB / BC only
        if nationwide or " canada " in loc:
            return 100
        if " ontario " in loc or " on " in loc:
            return 100
        if not loc.strip():
            return 85
        # Remote with no country/province constraint: keep, but rank below verified Canada-remote.
        if not outside_on:
            return 85

    if " ontario " in loc or " on " in loc:
        return 65                           # Ontario-unspecified: possible, but not verified GTA

    # A named Canadian city/province outside Ontario that is not nationwide-remote is incompatible.
    if outside_on:
        return 0

    # Unknown location is retained conservatively, but heavily discounted.
    if not (location or "").strip():
        return 55
    return 0


def explain_cyber_match(job):
    """Return the v2 matching explanation without writing anything to the database."""
    title = job.get("title", "")
    text = job.get("text", "")
    lane, lane_bonus = _title_lane(title, text)
    if lane is None:
        return {"accepted": False, "reason": "off_target_lane"}

    required_years = _required_years(text)
    if required_years is not None and required_years >= 5:
        return {"accepted": False, "reason": "requires_5_plus_years", "required_years": required_years}

    # Existing title classifier remains useful for explicit Senior/Lead/Principal markers.
    if eng.classify_level(title, text) == "senior":
        return {"accepted": False, "reason": "senior_level", "required_years": required_years}

    location_fit = _location_fit(job.get("location", ""), text)
    if location_fit <= 0:
        return {"accepted": False, "reason": "location_incompatible", "required_years": required_years}

    skill_points, matched = _skill_match(title + " " + text)
    # 20-point floor rewards being in the exact lane; title bonus differentiates
    # SOC/MDR/IR from broad Security Specialist/Consultant titles.
    match_score = min(100, 20 + lane_bonus + skill_points)
    if match_score < 55:
        return {"accepted": False, "reason": "weak_profile_match", "score": match_score,
                "matched": matched, "required_years": required_years, "location_fit": location_fit}

    age = eng._age_days(job.get("posted", ""))
    # Employer feeds are an active-listing signal, so exceptional matches may survive
    # beyond 30 days; stale ordinary matches do not.
    if age is not None and age > 60:
        return {"accepted": False, "reason": "stale", "score": match_score, "age_days": age}
    if age is not None and age > 30 and match_score < 92:
        return {"accepted": False, "reason": "older_not_exceptional", "score": match_score, "age_days": age}

    return {
        "accepted": True,
        "lane": lane,
        "score": match_score,
        "matched": matched,
        "required_years": required_years,
        "location_fit": location_fit,
        "age_days": age,
    }


def _looks_cyber_target(job):
    """Cheap pre-check so MDR/Falcon titles can bypass the old field classifier."""
    t = _normalise(job.get("title", ""))
    if any(phrase in t for _, _, phrases in TARGET_TITLE_SIGNALS for phrase in phrases):
        return True
    return False


def process_v2(job, company):
    """Drop-in replacement for engine.process with candidate-first cyber matching."""
    # Preserve Inlet's existing behaviour for non-target career fields.
    field, _, _ = eng.classify_field(job.get("title", ""))
    if field != "cybersecurity" and not _looks_cyber_target(job):
        return _base_process(job, company)

    detail = explain_cyber_match(job)
    if not detail.get("accepted"):
        return None

    realness = eng.score_realness(job.get("title", ""), job.get("text", ""), job.get("posted", ""))
    if realness < 45:
        return None
    recency = eng.score_recency(job.get("posted", ""))

    match_score = detail["score"]
    location_fit = detail["location_fit"]
    tier_bonus = {1: 5, 2: 2, 3: 0}.get(company.get("tier", 3), 0)

    opportunity = min(100, round(
        0.55 * match_score + 0.15 * location_fit + 0.15 * recency + 0.15 * realness
    ) + tier_bonus)

    level = eng.classify_level(job.get("title", ""), job.get("text", ""))
    level_score = 92 if level == "entry" else 74
    landability = round(
        0.55 * match_score + 0.20 * level_score + 0.15 * location_fit + 0.10 * recency
    )
    years = detail.get("required_years")
    if years == 4:
        landability -= 8
    elif years == 3:
        landability -= 3
    landability = max(0, min(100, landability))

    flags = [f for f in eng.FLAG_TERMS if f in _normalise(job.get("title", "") + " " + job.get("text", ""))]
    posted_date = None
    raw_posted = str(job.get("posted", "")).replace("Z", "").split("T")[0].split(" ")[0]
    try:
        posted_date = eng.dt.datetime.strptime(raw_posted, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        pass

    return {
        "company": company["name"],
        "tier": company.get("tier", 3),
        "field": "cybersecurity",
        "role_label": detail["lane"],
        "title": job.get("title", ""),
        "location": job.get("location", ""),
        "url": job.get("url", ""),
        "posted": posted_date,
        "opportunity_score": opportunity,
        "landability": landability,
        "realness": realness,
        "level": level,
        "flags": flags,
        "description": job.get("text", "")[:2000],
    }