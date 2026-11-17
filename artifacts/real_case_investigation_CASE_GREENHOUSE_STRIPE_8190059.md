# Read-only real-world decision investigation

## Case

**Case ID:** `CASE_GREENHOUSE_STRIPE_8190059`  
**Employer:** Stripe  
**Role:** Account Executive, Product Sales (Data)  
**Location:** US-SF-HQ, US-NYC, US-CHI, US-SEA  
**Job identifier:** `8190059`  
**Stored official page:** `stripe.com/careers/listing/account-executive-product-sales-data/8190059`  
**Stored retrieval:** HTTP 200, 2026-11-12  

This is a useful unexpected case because the preserved collection artifact describes it as `independent_official_confirmation`, while the current live decision is unresolved.

## Expected versus actual result

The stored evidence supports a human expectation that the posting corresponds to an active Stripe vacancy: the employer, title, location, description, and job identifier match the preserved official page/API records. However, the underlying ground-truth review remains pending and the collection report explicitly says that snapshot consistency is not automatic authorization ground truth.

Under the current conservative live policy, the correct expected result is therefore **unresolved**, not supported. The system must not convert a genuine employer or a matching snapshot into a definitive authorization decision without verified authority and adjudicated independent lineage.

**Actual live result:** `unresolved` / abstain  
**Fraud outcome:** `unresolved`  
**Employer identity:** `unresolved` in the live replay  

## Decision trace

### 1. Original advertisement

The preserved advertisement contains a Stripe role, the exact title above, four listed US locations, an application URL containing `gh_jid=8190059`, and a long HTML description. The description includes Stripe team information, responsibilities, minimum requirements, and preferred qualifications.

### 2. Extracted and normalized fields

The replay normalized the stored fields as:

| Field | Value/status |
|---|---|
| Employer | Stripe |
| Job title | Account Executive, Product Sales (Data) |
| Location | US-SF-HQ, US-NYC, US-CHI, US-SEA |
| Job ID | 8190059 |
| Application URL | Stripe careers URL with `gh_jid=8190059` |
| Description | 5,348 characters in the preserved advertisement |

No material advertisement-side field conflict was found.

### 3. Retrieved evidence

Two preserved source records were replayed without network access:

| Source | Field matching | Live evidence result |
|---|---|---|
| Stripe careers page | Employer, title, job ID, application URL and posting date matched; vacancy correspondence `true` | `unverified`, `independently_unresolved` |
| Greenhouse API | Stored artifact says it matched, but current JSON extraction did not expose comparable fields during replay; vacancy correspondence `false` | `unverified`, `independently_unresolved` |

The preserved collection row separately records exact employer/title/location/description/job-identifier matches and classifies the collection result as `independent_official_confirmation`. That classification is not the same field/value pair consumed by the current live aggregator.

### 4. Employer authority

`config/employer_sources_v1.json` contains zero verified mappings. Therefore:

- `stripe.com` is not treated as an explicitly verified employer-owned domain by the live collector.
- `boards-api.greenhouse.io` is recognized as an ATS host, but the Stripe-to-Greenhouse relationship is not configured as verified.
- The sources are classified as `unverified_recruiter_page` and `unverified_ats` in the replay.
- `source_authoritative = false`.

### 5. Vacancy correspondence

- Stripe careers source: `vacancy_match = true`.
- Greenhouse API source: `vacancy_match = false` in the current replay because the JSON source was not converted into the comparable extracted fields expected by the live matcher.
- No material conflict was found; the second result is a comparability/extraction limitation, not evidence of fraud.

### 6. Freshness

- Stripe careers source: `current`, based on the preserved posting date, 42 days old under the configured 180-day window.
- Greenhouse API source: `unknown`, because the current extractor did not expose a recognized source date from the replayed JSON.
- The combined policy freshness input is `unresolved` because no qualifying source set passed all gates.

### 7. Lineage

Both live evidence observations have:

- `source_relationship = unknown`
- `lineage_review_status = not_assessed`
- No adjudicated lineage group

The stored source-independence description is preserved collection metadata, not a live adjudicated lineage relationship. The lineage-aware aggregator correctly refuses to treat unknown relationships as independent confirmation.

### 8. Aggregation

**Ordinary aggregation:**

- State: `unresolved`
- Supporting sources: 0
- Contradicting sources: 0
- Effective sources: 0

The ordinary aggregator only accepts `evidence_state=supported` together with `verification_status=independently_supported`. The replay observations are `unverified` / `independently_unresolved`, so they are excluded.

**Lineage-aware aggregation:**

- State: `unresolved`
- Supporting sources: 0
- Contradicting sources: 0
- Effective sources: 0

The lineage-aware aggregator excludes both observations because neither has an adjudicated independent or copied/derived relationship.

### 9. Final live policy

| Policy input | Value |
|---|---|
| Qualifying independent source count | 0 |
| Minimum required | 2 |
| Source authoritative | `false` |
| Vacancy correspondence | `false` overall because no qualifying set exists |
| Freshness | `unresolved` |
| Retrieval failures | 0 |
| Material conflicts | none |

The final policy returns:

```text
vacancy_authorization = unresolved
action = insufficient evidence; abstain
fraud_outcome = unresolved
```

## Exact rules responsible

1. Authority mappings must be explicitly verified; none are configured.
2. Live support requires `evidence_state=supported` and `verification_status=independently_supported`.
3. Lineage-aware aggregation requires an adjudicated independent or copied/derived relationship.
4. Unknown or unreviewed lineage is not counted as independent evidence.
5. The live policy requires at least two qualifying independent source groups.
6. Current freshness and vacancy correspondence must pass the policy gates.
7. Missing authority or evidence is treated as unresolved, not fraudulent.

## Root cause

The primary root cause is a **provenance/schema mismatch**, not a contradiction in the vacancy:

- The collection artifact uses fields such as `evidence_classification=independent_official_confirmation`, `employer_identity_evidence=independently_confirmed`, and `vacancy_authorization_evidence=independently_confirmed`.
- The live aggregation/policy expects `evidence_state`, `verification_status`, `source_relationship`, and `lineage_review_status` with stricter values.
- The preserved collection labels are not automatically promoted into those live fields, correctly preventing unreviewed research artifacts from becoming live authorization evidence.

Secondary causes are:

- No verified Stripe domain/ATS mapping.
- No adjudicated lineage metadata.
- Current ATS JSON extraction does not expose the comparable fields used by the live matcher during replay.

This is not caused by freshness falsely marking the official source stale, and it is not caused by a fraud rule.

## User-facing explanation assessment

The decision state is conservative and appropriate, but a generic explanation such as “insufficient evidence” hides the more specific reason: the stored official-source match is not yet accepted as live authorization because authority and lineage requirements are incomplete. The user-facing message is therefore safe but underspecified for this type of case.

## Raw aggregation versus final decision

For the replayed live observations, raw ordinary aggregation and raw lineage-aware aggregation are both `unresolved`. The final live decision is also `unresolved`, but it adds the policy action `insufficient evidence; abstain` and records the failed sufficiency/authority/freshness gates.

There is no state disagreement between raw aggregation and final policy in this case. The apparent disagreement comes from comparing the preserved collection artifact’s `independent_official_confirmation` label with the stricter live evidence schema.

## Recommended correction

No correction was implemented. The investigation recommends, for a future separately approved change:

1. Define an explicit, reviewed conversion from preserved collection evidence to live evidence fields.
2. Keep snapshot consistency distinct from independently adjudicated authorization.
3. Add documented verified employer-domain and ATS mappings only after authority review.
4. Improve JSON/ATS extraction so job ID, title, employer, location, description, and source dates are comparable.
5. Preserve the two-source minimum and unknown-lineage abstention rules.
6. Improve the explanation to say that a matching official snapshot exists but live authorization requirements are not yet satisfied.

## Potential impact

This pattern can affect many Stripe/Greenhouse cases and other collected ATS records:

- Real vacancies may remain unresolved because preserved research classifications are not live support values.
- Missing authority mappings can suppress otherwise strong employer/ATS evidence.
- ATS JSON extraction gaps can reduce correspondence and freshness evidence.
- The conservative behavior reduces false assurance but increases abstention and unresolved outcomes.

## Integrity confirmation

This investigation was read-only. No source code, datasets, annotations, labels, configuration, benchmarks, evaluation results, or research files were modified. Only this investigation report was created.
