"""
directory.py  -  built-in company directory (the automated-discovery layer)

Users don't supply companies. The product ships with this list of Canadian
security employers, already resolved to their hiring platform, so a friend just
opens the app and gets roles. The list grows over time.

Two kinds of entry:
  - "slug": auto-detected on Greenhouse / Lever / Ashby (probed at run time)
  - "workday": pre-resolved coordinates {tenant, pod, site} read off the careers URL
"""

DIRECTORY = [
    # Tier 1 - security firms / MSSPs (best entry-level odds)
    {"name": "Cyderes",            "tier": 1, "slug": "cyderes"},                 # confirmed: Lever
    {"name": "Arctic Wolf",        "tier": 1, "slug": "arcticwolf"},
    {"name": "eSentire",           "tier": 1, "slug": "esentire"},
    {"name": "Field Effect",       "tier": 1, "slug": "fieldeffect"},
    {"name": "GoSecure",           "tier": 1, "slug": "gosecure"},
    {"name": "Optiv",              "tier": 1, "slug": "optiv"},

    # Tier 2 - finance / fintech (high volume; Workday)
    {"name": "RBC",                "tier": 2, "workday": {"tenant": "rbc", "pod": "wd3", "site": "RBCGLOBAL1"}},          # confirmed
    {"name": "TELUS International", "tier": 2, "workday": {"tenant": "telusinternational", "pod": "wd3", "site": "External"}},  # confirmed

    # Tier 3 - logistics / supply chain / retail (the ops-background edge)
    {"name": "Kinaxis",            "tier": 3, "slug": "kinaxis"},
    {"name": "Descartes",          "tier": 3, "slug": "descartes"},
    {"name": "Shopify",            "tier": 3, "slug": "shopify"},

    # Add more by resolving each one's careers URL once, then dropping a line here.
]
