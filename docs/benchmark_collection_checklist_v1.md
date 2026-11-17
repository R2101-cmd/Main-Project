# Benchmark collection and annotation checklist v1

This checklist is the gate for Milestone 2. No record should enter the frozen benchmark until the required provenance and review fields are complete.

## A. Sampling frame — freeze before collection

### Unit hierarchy

- **Vacancy group:** the underlying job opening being investigated; this is the independent sampling and split unit.
- **Advertisement record:** one observed posting or representation of that vacancy group.
- **Evidence item:** one source observation used to assess a claim about an advertisement or vacancy.
- **Lineage relationship:** a reviewed relationship between evidence sources or advertisement records.

Report all four counts separately. Do not describe advertisement or evidence counts as independent vacancy groups.

### Proposed frame

- **Geography:** India, including remote roles explicitly open to applicants in India.
- **Collection period:** one fixed 30-day window, recorded as ISO start/end timestamps before collection begins.
- **Unit:** one advertisement instance, linked to an underlying vacancy group when reposts or copies are found.
- **Target:** 100–200 underlying vacancy groups, subject to feasibility; no artificial class balancing.
- **Primary role scope:** data analyst, data science, business analyst, analytics, machine-learning, product/data insights, and closely related internships or entry-level vacancies.

### Source strata

Collect from each stratum rather than relying on one platform:

- employer-controlled careers pages and employer ATS pages;
- public job portals and professional-network listings;
- university, government, and institutional recruitment pages;
- public newsletters or social posts only as lower-confidence provenance sources.

Record the stratum and source type for every advertisement. Do not treat a source stratum as an authorization label.

### Informative-case coverage gate

Before freezing the test set, report whether the collected groups include:

- affirmative support;
- affirmative contradiction;
- unresolved cases;
- reviewed copied/derived families;
- genuinely independent corroboration;
- incomplete, blocked, redirected, or unavailable evidence.

Do not manufacture a missing category. If a category is rare or absent, reduce the claim scope and report the limitation.

### Inclusion rules

Include a record only when it has:

- a stable case ID;
- a visible role title and claimed employer;
- a source URL or a permitted pasted-text/poster/PDF reference;
- a collection timestamp;
- enough content to distinguish the vacancy from a generic employer page.

### Exclusion rules

Exclude from the final evaluated benchmark, but retain in a collection log, records that are:

- inaccessible with no usable source record;
- obvious advertisements outside the role/geography scope;
- exact duplicates of the same source capture;
- job-search result pages where the individual listing cannot be identified;
- records containing unnecessary private applicant or recruiter information.

Inaccessible and excluded records must not be converted into `contradicted` labels.

## B. Collection record requirements

For every included advertisement, complete:

- `case_id`, `employer_id`, claimed employer, title, location, description or permitted snapshot reference;
- submitted URL, final URL after redirects, application URL/route, platform/source type;
- `observed_at`, source publication/deadline timestamps when available;
- source snapshot reference or documented reason a snapshot could not be retained;
- redaction/privacy status;
- initial duplicate and lineage candidate fields.

## C. Evidence-before-label gate

Before any reviewer assigns a label, collect evidence records containing:

- evidence ID and case ID;
- claim type: employer identity, vacancy authorization, contact, or application route;
- source URL and source type;
- retrieval timestamp and publication timestamp when known;
- retrieval state: available, unavailable, blocked, redirected, or not searched;
- evidence state: supported, contradicted, unverified, or unavailable;
- matched fields and contradiction details;
- concise rationale and permitted snapshot reference.

The evidence table must be frozen before reviewers see or assign the authorization label.

### Operational label examples

| Observation | Interpretation |
|---|---|
| Official employer evidence explicitly links the employer to the specific opening | Potential support for authorization; confirm role-specific match |
| Employer is legitimate but the specific vacancy cannot be confirmed | Unresolved |
| Vacancy is absent from a careers page | Not sufficient by itself for contradiction |
| Multiple portals repeat the same advertisement | Potentially dependent evidence, not independent corroboration |
| Reliable evidence directly conflicts with the claimed opening or authorization | Potential contradiction, subject to protocol review |
| Source is inaccessible | Evidence unavailable, not proof of fraud |

Every final label must cite evidence IDs and explain why the evidence addresses the specific vacancy rather than only the employer generally.

## D. Independent double annotation

- Give reviewers the same advertisement/evidence packet and protocol version.
- Hide the other reviewer’s labels, adjudication notes, model predictions, and aggregate outputs.
- Require separate reviewer IDs, timestamps, label, rationale, evidence IDs, and unresolved-information request.
- Calculate raw agreement and Cohen’s kappa or another appropriate statistic only when class support permits interpretation.
- Adjudicate disagreements after both independent labels are stored; retain both original labels.
- Do not use adjudicated test labels to tune thresholds or method rules.

## E. Lineage review

For every possible relationship, record:

- pair or group of case IDs;
- observed signals: exact text, edited text, shared URL, requisition ID, contact, dates, or redirect;
- relationship: original, independent, copied/derived, or unknown;
- reviewer ID, review timestamp, rationale, and confidence/status.

Similarity is a candidate signal only. If the evidence does not establish dependence, retain `unknown`.

## F. Split and freeze gate

Before final evaluation:

- assign one partition to every vacancy/lineage group;
- use a recorded random seed and split manifest;
- check that no group appears in more than one partition;
- freeze the test IDs and group IDs;
- prohibit threshold, feature, or rule changes based on test errors;
- keep test labels and test-level error analysis unavailable to anyone tuning thresholds or aggregation rules;
- preserve the benchmark fingerprint and configuration.

Recommended initial split: 70% train, 15% validation, 15% test by vacancy group, adjusted only for minimum class/group support and recorded in the manifest.

## G. Evaluation gate

Run E1, E4, and E5 on the same eligible test cases. Add E2/E3 only when their features and labels are independently available. Report:

- class counts and per-class precision, recall, F1, macro F1, balanced accuracy, and confusion matrix;
- evidence coverage, decision coverage, and abstention rate;
- false-assurance numerator and denominator;
- paired E4/E5 disagreements and whether each change was correct;
- uncertainty intervals where the sample supports them.

Evaluate E4 and E5 on exactly the same eligible test groups. Record paired outcomes for every group: both correct, both wrong, E4 wrong/E5 correct, E4 correct/E5 wrong, and whether any decision change is specifically attributable to lineage handling. If no reviewed dependent relationships occur in the test set, state that the lineage hypothesis was not meaningfully tested.

If a test result leads to a method change, create a new confirmatory evaluation set. The old test result remains exploratory and immutable.

Primary false assurance:

`unsupported cases predicted supported / all adjudicated non-supported cases`

Always report the number of definitive decisions alongside this rate.

## H. Current readiness review

| Gate | Status | Required action |
|---|---|---|
| High-level plan exists | ready | Use this checklist as the operational version |
| Exact collection window | pending | Freeze start/end timestamps before collection |
| Source/employer strata | ready | Record stratum on every case |
| Unit hierarchy and four-level counts | ready | Report groups, advertisements, evidence items, and relationships separately |
| Informative lineage variation | pending | Verify reviewed dependent and independent families before test freeze |
| Evidence-before-label workflow | ready | Freeze evidence packet before annotation |
| Two reviewer identities | pending | Assign reviewers and access controls |
| Lineage reference form | ready | Keep uncertain relationships unknown |
| Frozen split manifest | pending | Generate only after reviewed groups exist |
| Contradicted examples | pending | Collect affirmative contradictions; do not infer them |
| Final test set | not started | Freeze after double annotation and adjudication |

The benchmark must not be described as independently validated until the pending reviewer, agreement, adjudication, and frozen-test gates are complete.

## I. Machine-enforced pre-collection gate

The machine-readable template is [`config/collection_config_v1.json`](../config/collection_config_v1.json), validated by `scripts/validate_collection_readiness.py`. The template is an example configuration and is deliberately not authorized for collection. The validator does not require records or labels to exist, and it exits non-zero until all operational decisions are complete.

The gate requires all of the following before collection can be authorized:

- explicit ISO 8601 start/end timestamps with timezone, exactly 30 days apart;
- defined India-focused scope, source strata, selection procedure, collection log, and non-model/non-balanced selection policy;
- the required configuration, advertisement, evidence, annotation, lineage, and collection-log schema versions;
- two distinct assigned reviewers and a distinct adjudicator, with real identifiers rather than placeholders;
- approved privacy, redaction, snapshot, retention, and access-control decisions;
- an explicit named operator and timestamp authorizing collection; and
- an intact hash-verified frozen baseline.

Run the gate with:

```powershell
python scripts\validate_collection_readiness.py
```

The command writes [`docs/collection_readiness_report.md`](collection_readiness_report.md) and a machine-readable report under `artifacts/readiness/`. A `pending` item requires a human or operational decision; a `blocked` item indicates invalid or contradictory configuration. Neither state permits collection.

The machine-readable forms are in `schemas/`: advertisement records, evidence items, collection-log events, independent annotations, adjudications, and lineage reviews. Original reviewer annotations must remain separate from adjudication records; adjudication records reference the original annotation IDs and never overwrite them.

The existing evaluation runner can optionally enforce frozen test identifiers with `--frozen-test-manifest`. This is a software check, not a substitute for the human blinding and access-control process. Repository access restrictions alone do not guarantee blinding.
