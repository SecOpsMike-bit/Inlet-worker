"""
directory.py  -  built-in company directory (the automated-discovery layer)
"""

DIRECTORY = [
    # Tier 1 - security firms / MSSPs (best entry-level odds)
    {"name": "Cyderes",            "tier": 1, "slug": "cyderes"},                 # confirmed: Lever
    {"name": "Arctic Wolf",        "tier": 1, "workday": {"tenant": "arcticwolf", "pod": "wd1", "site": "External"}},        # confirmed
    {"name": "Optiv",              "tier": 1, "workday": {"tenant": "optiv", "pod": "wd5", "site": "Optiv_Careers"}},        # confirmed
    {"name": "CrowdStrike",        "tier": 1, "workday": {"tenant": "crowdstrike", "pod": "wd5", "site": "crowdstrikecareers"}}, # verified employer Workday
    {"name": "AlphaSense",         "tier": 1, "slug": "alphasense", "platform": "greenhouse"}, # verified active Canada SOC role
    {"name": "Posh AI",            "tier": 1, "slug": "posh-ai", "platform": "ashby"},          # verified Security Administrator / SOC role

    # Still to resolve (find each careers URL, then convert to a workday{} entry or correct slug):
    {"name": "eSentire",           "tier": 1, "slug": "esentire", "platform": "dayforce"},  # verified official public JobFeeds API
    {"name": "Field Effect",       "tier": 1, "slug": "fieldeffect"},
    {"name": "GoSecure",           "tier": 1, "slug": "gosecure", "platform": "adp",
     "board_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=5d5085c5-5799-40cd-ae96-c7e0621cd1bc"},  # employer-linked ADP recruiting

    # Tier 2 - finance / fintech (high volume; Workday)
    {"name": "RBC",                "tier": 2, "workday": {"tenant": "rbc", "pod": "wd3", "site": "RBCGLOBAL1"}},          # confirmed
    {"name": "Finastra",           "tier": 2, "workday": {"tenant": "finastra", "pod": "wd3", "site": "FINC"}},              # verified employer Workday
    {"name": "CDW",                "tier": 2, "workday": {"tenant": "cdw", "pod": "wd5", "site": "careers"}},                 # verified employer Workday
    {"name": "TELUS Digital Solutions", "tier": 2, "slug": "telus-digital", "platform": "ashby"},  # employer-linked Digital Solutions board

    # Tier 3 - logistics / supply chain / retail (the ops-background edge)
    {"name": "Kinaxis",            "tier": 3, "slug": "kinaxis", "platform": "jibe",
     "board_url": "https://join.kinaxis.com/jobs"},  # verified public /api/jobs feed
    {"name": "Descartes",          "tier": 3, "slug": "descartes", "platform": "successfactors",
     "board_url": "https://jobs.descartes.com/go/View-All-Jobs/2574817/"},  # verified official employer board
    {"name": "Shopify",            "tier": 3, "platform": "shopify", "slug": "shopify"},  # official first-party careers HTML
    {"name": "Take-Two",           "tier": 3, "slug": "taketwo", "platform": "greenhouse"},    # verified Toronto security ops posting

]
