# GetInlets V3 — employer feed coverage (updated 13 October 2026)

**Branch:** `v3-profile-matching`, draft PR #3. **Production V2 unchanged.**

## Current result: all 17 configured employers now have verified working feeds

The last completed full shadow before resolving the final two sources, [run 38486580376](https://github.com/SecOpsMike-bit/Inlet-worker/actions/runs/38486580376), evaluated **949 raw jobs from 15 working feeds**. It retained **two V3 `maybe` recommendations**, AlphaSense Security Operations Analyst II (Canada remote; 4 years) and Take-Two Security Operations Engineer (Toronto; 3 years). Do not claim a later full total until the 17-employer shadow finishes.

Live [priority-feed smoke run 38487872296](https://github.com/SecOpsMike-bit/Inlet-worker/actions/runs/38487872296) passed for **all six** newly verified employer feeds:

| Employer | Public source | Live postings | Canadian-location postings | V3 matches |
|---|---|---:|---:|---:|
| eSentire | Dayforce JobFeeds | 18 | 9 | 0 |
| TELUS Digital Solutions | Ashby | 56 | 13 | 0 |
| Shopify | First-party careers HTML | 31 | 2 | 0 |
| Kinaxis | Public iCIMS/Jibe `/api/jobs?page=N` | 108 | 46 | 0 |
| Field Effect | Dayforce JobFeeds (`fieldeffect`) | 3 unique | 3 | 0 |
| GoSecure | ADP Workforce Now public career-centre requisitions | 2 | 2 | 0 |

Counts are point-in-time snapshots, not guarantees of future vacancy counts.

## Final two sources resolved

### Field Effect — official Dayforce

Field Effect's own [careers page](https://fieldeffect.com/careers) links to `https://can231.dayforcehcm.com/CandidatePortal/en-US/fieldeffect`. The officially documented public `https://www.dayforcehcm.com/api/fieldeffect/V1/JobFeeds` redirects to an accessible Dayforce services host and returned four records, including one duplicate, for **three unique roles**.

One role looks highly relevant by title: [Cyber Security Analyst](https://jobs.dayforcehcm.com/en-US/fieldeffect/CANDIDATEPORTAL/jobs/702), posted 2026-09-29. However, the feed's structured location is **BC, Canada**, and the description explicitly says **Western Canada (remote position)**. The Toronto/Ontario beta profile correctly rejects it with `outside_ontario`. **Do not loosen the remote eligibility rule or present this as an Ontario-eligible match.**

### GoSecure — public ADP recruiting API

GoSecure's [official careers page](https://legacy.gosecure.ai/careers/) links to the ADP Workforce Now recruitment page with `cid=5d5085c5-5799-40cd-ae96-c7e0621cd1bc`.

The verified **public, anonymous** list endpoint is:

`https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions`

with `cid`, external `ccId=19000101_000001`, one-based `$skip=1` and `$top=20`. The feed returned two roles: Account Executive (Ontario Only) and SOC Director. The latter is excluded for seniority by V3's existing `excluded_title` rule, even though its locations include Toronto.

New `adp_feed.py` uses only the public external career centre, validates the employer-hosted URL, pages conservatively, deduplicates by requisition ID, and optionally enriches from public requisition detail. It does **not** access authenticated ADP partner APIs or applicant data.

## Engineering and validation

- `directory.py` now has **17/17 verified platform configurations**, with Field Effect as `dayforce` and GoSecure as `adp`.
- `engine.py` uses `fetch_adp` in both normal and diagnostic paths. Failed list requests are `fetch_error`, not `empty_feed`.
- `test_adp_feed.py` covers tenant safety, public-only centre, one-based pagination, duplicate removal, detail failures and schema errors.
- `test_feed_diagnostics.py` covers GoSecure and Field Effect wiring and HTTP error handling.
- `test_realworld_v3.py` includes the exact Field Effect BC-only and GoSecure SOC Director eligibility signals.
- [CI run 38487876577](https://github.com/SecOpsMike-bit/Inlet-worker/actions/runs/38487876577) passed with both adapters active; subsequent regression additions also require CI.
- `shadow-compare-v3.yml` now triggers on all current adapter files, including `adp_feed.py`, `shopify_feed.py`, and `jibe_feed.py`. The shadow workflow remains read-only and does not write production records.

## Next priority

Now that employer feed health is resolved, **increase eligible Canadian SOC/MDR coverage** by verifying additional employer-hosted feeds for organizations with genuine junior SOC, security operations, incident response and MSSP roles in Ontario or Canada-remote. Maintain strict eligibility and geography checks; do not inflate recommendation counts with senior, BC-only, US-only or unrelated jobs. Keep V3 in draft PR #3 until explicit merge/deployment authorization.
