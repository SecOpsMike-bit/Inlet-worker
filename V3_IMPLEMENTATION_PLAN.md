# GetInlets V3 — Matching & Profile Architecture

## Goal

Separate job discovery from user-specific matching so Inlet can ingest broadly, then rank the same raw job differently for each user's profile.

Primary beta goal: reliably surface high-fit entry/junior cybersecurity roles for Toronto/GTA and Canada-remote candidates, with transparent reasons for each recommendation.

## V3 flow

DISCOVER -> STORE RAW JOB -> PROFILE MATCH -> RANK -> PREPARE -> USER APPLIES

The crawler should not decide whether a job belongs to one specific candidate. It should collect valid jobs. Matching happens afterward against a user profile.

## Data model

### users
Authentication identity only.

Suggested fields:
- id
- email
- created_at
- last_login_at

### profiles
One user may have multiple career profiles, e.g. Cybersecurity and Project Management.

Suggested fields:
- id
- user_id
- name
- career_field
- target_titles JSON
- excluded_titles JSON
- preferred_locations JSON
- remote_preference
- max_required_years
- salary_min
- work_authorization JSON
- skills JSON
- certifications JSON
- active
- created_at
- updated_at

### resumes
Master and tailored versions remain separate.

Suggested fields:
- id
- user_id
- profile_id
- parent_resume_id nullable
- job_id nullable
- type: master | tailored
- filename
- storage_path
- parsed_text
- structured_content JSON
- created_at

### jobs
Raw employer job records. These should contain no candidate-specific score.

Suggested fields:
- id
- company_id
- source_platform
- source_external_id nullable
- title
- location_raw
- workplace_type nullable
- url unique
- posted_at nullable
- description
- captured_at
- last_seen_at
- active

### job_matches
A candidate-specific evaluation of one job against one profile.

Suggested fields:
- id
- profile_id
- job_id
- overall_score
- skills_score
- location_score
- experience_score
- opportunity_score
- eligibility_status: pass | warning | fail
- recommendation: strong_apply | apply | maybe | skip
- matched_skills JSON
- missing_skills JSON
- warnings JSON
- explanation JSON
- evaluated_at

Unique constraint: (profile_id, job_id)

### applications
Suggested fields:
- id
- user_id
- profile_id
- job_id
- match_id
- tailored_resume_id nullable
- status: saved | preparing | applied | interview | rejected | offer | withdrawn
- applied_at nullable
- notes
- created_at
- updated_at

## Beta cybersecurity profile logic

### Tier A target titles
- SOC Analyst / SOC Analyst I / Tier 1
- Junior Security Analyst
- Security Operations Analyst
- Cybersecurity Analyst
- MDR Analyst
- MSSP Security Analyst
- Incident Response Analyst
- Detection / Monitoring Analyst

### Tier B conditional titles
Accept only with strong SOC / blue-team evidence:
- Security Specialist
- Information Security Analyst
- Threat Analyst
- Security Consultant
- Cyber Defense / Defence Analyst

### Default hidden/off-lane
- Security Architect
- Senior / Lead / Principal / Staff roles
- AppSec / Product Security
- Pentesting / Red Team
- IAM / Identity Governance
- GRC / Compliance
- DevSecOps
- advanced Security Engineering unless explicitly junior operational work

## Experience policy

- 0–2 years required: strong positive
- 3 years required: acceptable
- 4 years required: warning; only retain when profile fit is strong
- 5+ years required: reject by default

Do not rely only on title seniority. Parse explicit candidate-facing experience requirements from the description.

## Location policy for Toronto beta

Location score should consider both the structured location and the job description.

- Toronto / North York / GTA: 100
- Canada-wide remote: 100
- Ontario remote: 95–100
- nearby Ontario hybrid: score based on commute and onsite frequency
- Ontario-unspecified: moderate
- outside Ontario onsite/hybrid: reject unless profile allows relocation
- province-restricted remote outside Ontario: reject
- foreign-only remote: reject
- unknown: retain only with a heavy confidence penalty

Important: parse onsite frequency when available. Example: St. Jacobs once per month should score materially higher than St. Jacobs 3 days/week.

## Matching dimensions

### Skills score
Compare job requirements against confirmed profile skills. Synonyms should map into skill groups so one requirement does not double-count.

### Experience score
Use required years, level markers, and nature of responsibility.

### Location score
Use city/province/country, remote constraints, and onsite frequency.

### Opportunity score
Use posting freshness, employer-feed validity, completeness, and active-listing confidence.

### Eligibility
Pass / warning / fail for hard constraints such as location restriction, mandatory clearance/citizenship, mandatory certification, or 5+ years when profile disallows it.

## Recommended overall-score starting weights

- Skills / profile fit: 45%
- Experience fit: 20%
- Location fit: 15%
- Opportunity quality / freshness: 20%

Hard eligibility failures override the numeric score and produce Skip.

Initial recommendation bands:
- 85–100: Strong Apply
- 70–84: Apply
- 55–69: Maybe
- below 55: Skip

These bands must be calibrated against the benchmark set rather than treated as permanent constants.

## Transparency requirement

Every accepted match should explain:
- why this role is in the user's target lane
- matched skills
- missing or weak skills
- experience requirement detected
- location interpretation
- warnings / hard constraints
- freshness
- final recommendation

No unexplained "AI percentage" should be shown.

## Benchmark gate

Before V3 replaces V2, build a 30–50 role regression set with:
- strong matches
- borderline roles
- obvious rejects
- misleading titles
- tricky location cases
- remote province restrictions

Target: at least 90% agreement with manual review before enabling V3 for the beta workflow.

## Migration strategy

1. Keep existing `roles` table and V2 workflow untouched.
2. Add V3 models alongside current schema.
3. Backfill raw jobs from the existing role feed where possible.
4. Run V3 matcher in parallel without changing production results.
5. Compare V2 vs V3 against benchmark cases and live discoveries.
6. Switch the UI/API to V3 only after benchmark and live-review acceptance.

## Later phases

After matching accuracy is proven:
1. Authentication and profile onboarding.
2. Master resume upload and structured parsing.
3. Truth-preserving resume tailoring per job.
4. Application tracker.
5. Additional career profiles per user.
6. Optional approved integrations such as LinkedIn OAuth if useful and permitted; never store LinkedIn passwords.
