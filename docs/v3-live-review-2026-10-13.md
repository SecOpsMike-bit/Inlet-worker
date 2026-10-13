# GetInlets V3 — employer-feed and job-eligibility review (13 October 2026)

**Status:** Review of independently verified employer postings and the last **completed** shadow scan. The new 17-employer comparison must finish before its figures can be reported. V3 remains a draft branch; production V2 is unchanged.

## Baseline and comparison correction

The completed 8 October shadow scan (GitHub Actions run 37808626765) fetched **571 jobs from 7 of 14 companies**. It counted **60 V2 keeps, 1 V3 keep and 59 disagreements**. Those disagreement figures are **not an apples-to-apples evaluation**: the old shadow script counted V2's non-cybersecurity fallback career lanes, whereas V3 was deliberately limited to the beta cybersecurity profile. Commit `1419d051` changes the shadow comparison to use `match_v2.explain_cyber_match`, so future disagreement figures compare cybersecurity against cybersecurity.

The single V3 recommendation in that baseline was CDW's Mississauga **Security Specialist** (score 76, `apply`), with a warning to verify **two intermediate-level security certifications**. **Do not treat that as confirmed eligibility**: the job explicitly requires two intermediate Managed Security Services certifications; Security+/CySA+ should not automatically be assumed to satisfy this requirement.

## Verified live job requirements

| Employer / verified vacancy | Evidence | Human eligibility review | Product implication |
| --- | --- | --- | --- |
| [AlphaSense — Security Operations Analyst II](https://job-boards.greenhouse.io/alphasense/jobs/8693315002) | Fully remote **within Canada**, but must work **Pacific time-zone hours**; 2–4+ years SOC; cloud and identity monitoring; SIEM/EDR, MITRE, investigation | Plausible SOC fit, but **confirm Pacific schedule** and actual cloud/identity exposure; experience is at the lower bound | Support `Remote - Canada; Vancouver` without mistakenly rejecting it as BC-only. Keep a timezone warning in manual review. |
| [Posh — Security Administrator](https://jobs.ashbyhq.com/posh-ai/95f93660-b1dc-4cd1-9dab-f89e9b7ebd4d) | Role is operational SOC: SIEM alert triage, log investigations, security tooling, 1–3 years experience, GCP; advertises Canada compensation | Promising conditional title. **Confirm remote Canadian eligibility**, on-call expectations, and GCP familiarity before claiming a strong fit | Admit Security Administrator **only** with operational SOC evidence, not physical/facilities security. |
| [Take-Two — Security Operations Engineer](https://job-boards.greenhouse.io/taketwo/jobs/8143808) | Toronto; 1–3 years; junior support of SOAR playbooks/integrations; foundational Python; prior SOC is a plus | Strong **bridge-role candidate**, conditional on foundational scripting and **at least four days per week physically in office** (requirement appears in application form, not main job description). Salary listed CA$71,400–105,660 | Add a narrow junior SOAR-engineering title path. Flag onsite requirements in application questions; ordinary ATS descriptions can miss them. |
| [CDW — Security Specialist](https://www.cdwjobs.com/en/jobs/17403780-security-specialist-siem-technologies) | Mississauga; Microsoft Sentinel/Defender MDR; requires **at least two intermediate-level Managed Security Services certifications** | **Hold for credential verification**. The beta profile has no verified qualifying intermediate certifications. | Certification warning must remain visible; do not infer qualification from keyword overlap. |

These are **verified posting facts**, not claims that GetInlets successfully ingested or recommended all four jobs. Current openings and terms may change; the links are for re-verification.

## Employer-feed integration triage

| Employer(s) | Current directory configuration | Interpretation / action |
| --- | --- | --- |
| eSentire | Dayforce (unsupported) | **Dedicated Dayforce connector needed**. A zero-job count means unsupported, not zero vacancies. |
| Descartes | SuccessFactors (unsupported) | **Dedicated SAP SuccessFactors connector needed**. Same zero-count caveat. |
| Field Effect, GoSecure, Kinaxis, Shopify | Automatic Greenhouse/Lever/Ashby/SmartRecruiters slug probing | If diagnostic status is `unresolved_feed`, inspect the actual employer careers URL before selecting a provider or declaring no openings. |
| TELUS International | Configured Workday tenant/site | A zero result is `empty_or_feed_error` until its Workday endpoint and response are verified. |
| AlphaSense, Posh, Take-Two | Explicit Greenhouse, Ashby, Greenhouse slugs | Confirm `status=ok` and relevant posting URLs in the **next completed shadow report**; do not assume success from slug configuration alone. |

## Next validation gates

1. Review the **latest completed** 17-employer shadow report: provider status by company, total fetched, V2 cyber vs V3 disagreements, and candidate URLs. Distinguish `unsupported_platform`, `unresolved_feed`, `empty_or_feed_error`, and `ok`.
2. Manually verify all recommended roles against original employer posting and application questions; record location, citizenship/work authorization, years, mandatory certifications, time zone, onsite schedule and title lane.
3. For high-value employers with unsupported/unresolved feeds, add the appropriate connector and fixture-based tests before declaring coverage.
4. Keep PR #3 in **draft** until CI is green, comparison quality is validated, and manual hard-blocker checks pass. Do **not** merge/deploy V3 on this report alone.
