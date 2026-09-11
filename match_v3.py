"""Profile-driven matching for GetInlets V3.

V3 deliberately separates raw job discovery from candidate scoring. The matcher
accepts a raw job dictionary plus a profile dictionary and returns a transparent
candidate-specific decision. It does not write to the database.
"""

import datetime as dt
import re


SENIOR_TITLE_TERMS = (
    "senior", "sr.", "sr ", "lead", "principal", "staff", "manager", "director", "architect",
)

CANADA_REMOTE_TERMS = (
    "remote canada", "canada remote", "remote, canada", "anywhere in canada",
    "across canada", "throughout canada", "canada-wide", "canada wide",
)

OUTSIDE_ON_TERMS = (
    "alberta", "british columbia", "quebec", "québec", "manitoba", "saskatchewan",
    "nova scotia", "new brunswick", "newfoundland", "prince edward island", "yukon",
    "northwest territories", "nunavut", "calgary", "edmonton", "vancouver", "victoria",
    "montreal", "montréal", "winnipeg", "halifax", " ab", " bc", " qc", " mb", " sk", " ns",
)

SOC_OPS_EVIDENCE = (
    "soc", "security operations center", "security operations centre",
    "managed detection and response", "mdr", "siem", "microsoft sentinel", "splunk",
    "xdr", "edr", "endpoint detection and response", "alert triage",
    "triage security alerts", "triage alerts", "incident response", "incident handling",
    "incident escalation", "escalate incidents", "security monitoring", "security alerts",
    "threat detection",
)

SKILL_SYNONYMS = {
    "microsoft sentinel": ("microsoft sentinel", "azure sentinel"),
    "splunk": ("splunk",),
    "crowdstrike": ("crowdstrike", "falcon complete", "falcon edr"),
    "siem": ("siem", "security information and event management"),
    "xdr": ("xdr",),
    "edr": ("edr", "endpoint detection and response"),
    "alert triage": ("alert triage", "triage security alerts", "security alert triage", "triage alerts"),
    "incident response": ("incident response", "incident handling"),
    "incident escalation": ("incident escalation", "escalation", "escalate incidents"),
    "phishing": ("phishing", "suspicious email"),
    "malware": ("malware", "malicious software"),
    "ticket lifecycle": ("ticket lifecycle", "ticketing", "case management", "service desk", "sla"),
    "windows": ("windows",),
    "linux": ("linux",),
    "ids/ips": ("ids/ips", "intrusion detection", "intrusion prevention"),
    "firewalls": ("firewall", "firewalls"),
    "vpn": ("vpn", "virtual private network"),
    "mitre att&ck": ("mitre att&ck", "mitre attack"),
    "client-facing remediation": (
        "client-facing", "customer-facing", "client support", "customer support",
        "remediation guidance", "client communication", "trusted advisor",
    ),
}


def _norm(value):
    return " " + re.sub(r"\s+", " ", (value or "").lower()).strip() + " "


def _age_days(posted):
    if not posted:
        return None
    if isinstance(posted, dt.date):
        d = posted
    else:
        raw = str(posted).replace("Z", "").split("T")[0].split(" ")[0]
        try:
            d = dt.datetime.strptime(raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None
    return max(0, (dt.date.today() - d).days)


def _required_years(text):
    """Return the strongest explicit candidate-facing years requirement found."""
    blob = _norm(text)
    years = []
    patterns = [
        r"(?:minimum(?:\s+of)?|at\s+least|required|requires|must\s+have|you\s+(?:have|bring|possess))[^.;\n]{0,100}?(\d+)\s*\+?\s*years?",
        r"(\d+)\s*\+?\s*years?(?:\s+of)?\s+(?:relevant\s+|professional\s+|hands[- ]on\s+)?(?:cybersecurity\s+|cyber\s+security\s+|security\s+|soc\s+|information\s+security\s+|incident\s+response\s+|it\s+|technical\s+)?experience",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, blob):
            value = int(match.group(1))
            if 0 <= value <= 20:
                years.append(value)
    return max(years) if years else None


def _soc_evidence_count(text):
    blob = _norm(text)
    return sum(1 for term in SOC_OPS_EVIDENCE if term in blob)


def _title_fit(title, text, profile):
    t = _norm(title)
    excluded = [x.lower() for x in profile.get("excluded_titles", [])]
    if any(term in t for term in excluded):
        return 0, "excluded_title"
    if any(term in t for term in SENIOR_TITLE_TERMS):
        return 0, "senior_title"

    targets = [x.lower() for x in profile.get("target_titles", [])]
    conditional = [x.lower() for x in profile.get("conditional_titles", [])]
    if any(term in t for term in targets):
        return 100, "target_title"
    if any(term in t for term in conditional):
        if _soc_evidence_count(text) < 2:
            return 0, "conditional_title_without_soc_evidence"
        return 90, "conditional_title_with_soc_evidence"
    return 0, "off_target_title"


def _skills(job_text, profile):
    blob = _norm(job_text)
    profile_skills = [s.lower() for s in profile.get("skills", [])]
    matched = []
    missing = []

    for skill in profile_skills:
        synonyms = SKILL_SYNONYMS.get(skill, (skill,))
        if any(term in blob for term in synonyms):
            matched.append(skill)

    for skill, synonyms in SKILL_SYNONYMS.items():
        if skill in profile_skills:
            continue
        if any(term in blob for term in synonyms):
            missing.append(skill)

    if not profile_skills:
        return 50, matched, missing
    score = round(100 * len(matched) / max(1, min(len(profile_skills), 10)))
    return min(100, score), matched, missing


def _experience_score(text, profile):
    years = _required_years(text)
    max_years = profile.get("max_required_years", 4)
    if years is None:
        return 72, None, None
    if years <= 2:
        return 100, years, None
    if years == 3:
        return 82, years, "requires_3_years"
    if years == 4:
        return 62, years, "requires_4_years"
    if years > max_years:
        return 0, years, "requires_too_many_years"
    return 50, years, "experience_stretch"


def _onsite_frequency_penalty(text):
    blob = _norm(text)
    if re.search(r"(?:3|three)\s+days?\s+(?:per|a)\s+week", blob):
        return 35, "hybrid_3_days_week"
    if re.search(r"(?:2|two)\s+days?\s+(?:per|a)\s+week", blob):
        return 22, "hybrid_2_days_week"
    if re.search(r"(?:1|one)\s+day\s+(?:per|a)\s+week", blob):
        return 12, "hybrid_1_day_week"
    if re.search(r"(?:once|1 time|one time)\s+(?:per|a)\s+month", blob):
        return 4, "onsite_monthly"
    return 0, None


def _location_score(location, text, profile):
    loc = _norm(location)
    blob = _norm((location or "") + " " + (text or ""))
    preferred = [x.lower() for x in profile.get("preferred_locations", [])]
    nearby = [x.lower() for x in profile.get("nearby_ontario_locations", [])]

    if any(term in loc for term in preferred):
        return 100, None

    remote = any(term in blob for term in (" remote ", "fully remote", "work from home", "wfh"))
    canada_remote = any(term in blob for term in CANADA_REMOTE_TERMS)
    outside_on = any(term in loc for term in OUTSIDE_ON_TERMS)

    if remote and canada_remote:
        return 100, None
    if remote and outside_on:
        return 0, "province_restricted_remote"
    if remote and (" ontario " in loc or " on " in loc):
        return 98, None
    if remote and not outside_on:
        return 85, "remote_scope_unverified"

    if any(term in loc for term in nearby):
        penalty, warning = _onsite_frequency_penalty(text)
        return max(35, 78 - penalty), warning

    if " ontario " in loc or " on " in loc:
        return 65, "ontario_location_not_gta"
    if outside_on:
        return 0, "outside_ontario"
    if not (location or "").strip():
        return 50, "location_unknown"
    return 0, "location_incompatible"


def _opportunity_score(posted):
    age = _age_days(posted)
    if age is None:
        return 55, age
    if age <= 2:
        return 100, age
    if age <= 7:
        return 90, age
    if age <= 14:
        return 80, age
    if age <= 30:
        return 62, age
    if age <= 60:
        return 35, age
    return 10, age


def evaluate(job, profile):
    """Evaluate a raw job against one profile and return an explainable result."""
    title = job.get("title", "")
    text = job.get("description") or job.get("text") or ""
    location = job.get("location_raw") or job.get("location") or ""
    posted = job.get("posted_at") or job.get("posted")

    title_score, title_reason = _title_fit(title, text, profile)
    if title_score == 0:
        return {
            "overall_score": 0,
            "eligibility_status": "fail",
            "recommendation": "skip",
            "reason": title_reason,
        }

    skills_score, matched_skills, missing_skills = _skills(title + " " + text, profile)
    experience_score, required_years, exp_warning = _experience_score(text, profile)
    location_score, loc_warning = _location_score(location, text, profile)
    opportunity_score, age_days = _opportunity_score(posted)

    warnings = [w for w in (exp_warning, loc_warning) if w]
    eligibility = "pass"
    if experience_score == 0 or location_score == 0:
        eligibility = "fail"
    elif warnings:
        eligibility = "warning"

    base = round(
        0.45 * skills_score +
        0.20 * experience_score +
        0.15 * location_score +
        0.20 * opportunity_score
    )
    overall = round(base * (title_score / 100))

    if eligibility == "fail":
        recommendation = "skip"
    elif overall >= 85:
        recommendation = "strong_apply"
    elif overall >= 70:
        recommendation = "apply"
    elif overall >= 55:
        recommendation = "maybe"
    else:
        recommendation = "skip"

    return {
        "overall_score": max(0, min(100, overall)),
        "skills_score": skills_score,
        "location_score": location_score,
        "experience_score": experience_score,
        "opportunity_score": opportunity_score,
        "eligibility_status": eligibility,
        "recommendation": recommendation,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "warnings": warnings,
        "explanation": {
            "title_reason": title_reason,
            "required_years": required_years,
            "age_days": age_days,
            "location": location,
            "soc_evidence_count": _soc_evidence_count(text),
        },
    }
