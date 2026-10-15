# eSentire / Dayforce feed investigation (2026-10-15)

Status: **not yet collected**. The official eSentire careers site links to Dayforce, but a publicly accessible machine-readable feed for the eSentire tenant has not been verified from GitHub Actions.

## Documented read-only option

Dayforce documents an anonymous **GET JobFeeds** service at
`https://www.dayforcehcm.com/api/{CompanyName}/V1/JobFeeds`.
See: https://dayforce.fluidtopics.net/r/documents/Dayforce-Web-Services-Introduction-Guide/RESTful-Get-Job-Feeds?contentId=8by9wRuiJpEetR5JKBir~Q

**Important:** The employer must enable job-feed access. The URL is a documented template, **not** a verified working eSentire endpoint. Another Dayforce job-postings API requires authentication; do not use it without authorization.

## Implementation acceptance criteria

1. Verify the eSentire-specific read-only feed endpoint from CI; classify 403/404/disabled feeds as errors, never zero vacancies.
2. Validate job title, location, source URL and stable ID; preserve all raw postings and per-employer status.
3. Add deterministic response fixtures and unit tests; then add eSentire to the staging audit only after the live feed passes.
4. Keep MDR support roles distinct from SOC/security analyst roles and retain the Canadian cybersecurity release gate.
5. No production DB writes, credentials, unauthorized scraping or deployment during this investigation.

Current public job evidence (not yet in the automated feed): eSentire Support Center Analyst I, Waterloo, Ontario, listed on its investor job board: https://jobs.edisonpartners.com/companies/esentire/jobs/95905404-support-center-analyst-i
