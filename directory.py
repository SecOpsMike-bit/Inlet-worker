"""
directory.py  -  built-in company directory (the automated-discovery layer)
"""

DIRECTORY = [
    # Tier 1 - security firms / MSSPs (best entry-level odds)
    {"name": "Cyderes",            "tier": 1, "slug": "cyderes"},                 # confirmed: Lever
    {"name": "Arctic Wolf",        "tier": 1, "workday": {"tenant": "arcticwolf", "pod": "wd1", "site": "External"}},        # confirmed
    {"name": "Optiv",              "tier": 1, "workday": {"tenant": "optiv", "pod": "wd5", "site": "Optiv_Careers"}},        # confirmed
    # Still to resolve (find each careers URL, then convert to a workday{} entry or correct slug):
    {"name": "eSentire",           "tier": 1, "slug": "esentire"},
    {"name": "Field Effect",       "tier": 1, "slug": "fieldeffect"},
    {"name": "GoSecure",           "tier": 1, "slug": "gosecure"},

    # Tier 2 - finance / fintech (high volume; Workday)
    {"name": "RBC",                "tier": 2, "workday": {"tenant": "rbc", "pod": "wd3", "site": "RBCGLOBAL1"}},          # confirmed
    {"name": "TELUS International", "tier": 2, "workday": {"tenant": "telusinternational", "pod": "wd3", "site": "External"}},  # confirmed

    # Tier 3 - logistics / supply chain / retail (the ops-background edge)
    {"name": "Kinaxis",            "tier": 3, "slug": "kinaxis"},
    {"name": "Descartes",          "tier": 3, "slug": "descartes"},
    {"name": "Shopify",            "tier": 3, "slug": "shopify"},
]
