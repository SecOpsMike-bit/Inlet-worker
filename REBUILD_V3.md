# Inlet worker v3 — isolated rebuild

Status: **experimental; not deployed**. This branch does not alter the hourly production workflow.

## Why rebuild
The v2 workflow calls `worker.refresh()` and monkey-patches its processing function with a candidate-specific cybersecurity matcher. This mixes collection with filtering and discards jobs that could be relevant to other users. The legacy worker also deletes a company's stored roles when a nonempty feed returns, and formerly swept all stale records globally.

## Stage 1 — completed in branch
- `collector_v3.py`: raw postings with stable source identity, URL normalization, company-level failure isolation, separate empty-feed status, duplicate detection, collection metadata, and explicit local JSON staging.
- `test_collector_v3.py`: regression tests for preserving senior and out-of-region roles, deduplication, failed/empty feeds, invalid jobs, and staging.
- **No database access or production writes.** Raw jobs are not discarded because they fail a candidate's scoring rules.

Run tests locally: `python -m unittest -v test_collector_v3.py`.

## Stage 2 — pending
- Add a standalone CLI to run against selected known-good employer feeds and write a staging snapshot.
- Validate company feed URLs; separate fetch failure from legitimately empty feeds.
- Audit current company registry versus database, and explicitly recover cybersecurity source coverage.
- Add a dedicated Supabase staging schema/table with restricted write credentials and migration review; do not write to production `roles`.
- Store source snapshots and per-company collection results, then build field classification as a separate derived step.
- Add metrics for fetched, deduplicated, classified, rejected, expired and displayed roles.
- Test resume personalization only at query/ranking time; keep raw jobs independent of any one user's profile.

## Promotion gates
1. Tests and static checks pass.
2. Demonstrated cybersecurity coverage with real, verified employer job feeds.
3. All fields continue to be represented; explicit coverage comparison to current worker.
4. Failure and downtime recovery do not delete unvisited company records.
5. Preview points to staging; owner reviews results.
6. Production switch only after explicit approval and rollback plan.


## TELUS Digital source verification (2026-10-14)

- Legacy `TELUS International` Workday listing endpoint returned HTTP 403 in staging; **not a verified working feed**.
- Official replacement careers listing: https://careers.telusdigital.com/search/jobs/in
- Canada filter: https://careers.telusdigital.com/search/jobs/in/country/canada
- Do not equate the accessible HTML careers page with a validated automated API or full job coverage. Preserve `companies_error` until a source adapter is implemented and tested against the official site.
- Do not use login bypass, rate-limit evasion, or undocumented Workday endpoints. Keep the staging audit read-only; do not deploy.
