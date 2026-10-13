# GetInlets V3 — verified employer feed coverage (13 October 2026)

**Branch:** `v3-profile-matching`, draft PR #3. **Production V2 unchanged.**

## Verified live coverage

- **17 employers configured.** Last completed full shadow comparison before the new connectors: [run 38484430605](https://github.com/SecOpsMike-bit/Inlet-worker/actions/runs/38484430605): **810 raw jobs from 13 employers**, 7 V2 cyber-lane keeps, 2 V3 maybes (AlphaSense and Take-Two).
- **eSentire** public Dayforce JobFeeds: 18 postings, 9 Canadian-location, 0 V3 cyber matches. Live verified in [run 38486617332](https://github.com/SecOpsMike-bit/Inlet-worker/actions/runs/38486617332).
- **TELUS Digital Solutions** Ashby: 56 postings, 13 Canadian-location, 0 V3 cyber matches. Same smoke run.
- **Shopify** employer-hosted `https://www.shopify.com/careers`: **31 live role links**, 2 Canadian-location, 0 V3 cyber matches. First-party HTML adapter `shopify_feed.py` is in place and smoke-tested. Do **not** assume `jobs.ashbyhq.com/shopify` exists; both lowercase and capitalized public Ashby job-board API slugs returned HTTP 404.
- **Kinaxis** employer-hosted iCIMS/Jibe public `https://join.kinaxis.com/api/jobs?page=N`: **108 live postings**, 46 Canadian-location, 0 V3 cyber matches. `jibe_feed.py` fetches paginated public JSON with title, location, employer-hosted application URL, posting date and description. Smoke-tested in the same run. The credentialed `api.icims.com` partner API is **not used**.
- **Descartes** employer-hosted SuccessFactors: 24 postings in the last completed full comparison; diagnostic `ok`.

These numbers are snapshots, not guarantees of vacancy counts later.

## Remaining unresolved / unsupported sources

1. **GoSecure** — official careers page links to ADP Workforce Now recruiting, with `cid=5d5085c5-5799-40cd-ae96-c7e0621cd1bc`. The directory records the actual recruitment URL. Diagnostic status `unsupported_platform` is **not** a claim of zero vacancies. A safe ADP public job-list integration is the next connector task.
2. **Field Effect** — `https://fieldeffect.com/careers` returns a careers page but no recognized job-board links in its static HTML. The directory remains `unresolved_feed`; investigate its dynamically rendered openings source. Do not report zero vacancies.

## Safeguards and test evidence

- The four newly investigated sources are not silently assigned fake Greenhouse/Lever/Ashby slugs.
- New adapters are read-only, use public employer-hosted endpoints, bound request counts, and emit the normalized job fields expected by `match_v3.evaluate`.
- The `test_shopify_feed.py` and `test_jibe_feed.py` suites cover parsing, deduplication, bounded fetches, error status and normalization. `test_feed_diagnostics.py` checks that unsupported ADP is not misreported as empty.
- Latest [smoke test run 38486617332](https://github.com/SecOpsMike-bit/Inlet-worker/actions/runs/38486617332) and [test run 38486622730](https://github.com/SecOpsMike-bit/Inlet-worker/actions/runs/38486622730) both **passed**.
- A fresh full shadow comparison with Kinaxis activated was running at the time of this note; do not report a new total until it completes.

## Next priority

Resolve GoSecure ADP's publicly accessible posting feed and Field Effect's dynamically rendered source **without** using third-party scraped job links as authoritative employer vacancies. Then audit the resulting V3 decisions and ensure employer location and hard eligibility requirements remain intact. Keep PR #3 draft until explicitly authorized to merge.
