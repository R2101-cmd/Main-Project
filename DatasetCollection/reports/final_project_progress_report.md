# TrustHire Final Project Progress Report

## Overview
**Research:** Beyond Fake-Job Classification: Lineage-Aware Evidence for Vacancy Authorization Verification.
**Application:** TrustHire — Authorization Evidence Workspace.

The project studies whether evidence provenance and source lineage reduce false assurance in vacancy authorization verification. No research hypothesis is claimed as proven.

## Completed work
Stages 1–3 established the original Stripe/Greenhouse records, unresolved Table B labels, and snapshot evidence. Stages 4A–4E developed retrieval, field matching, employer-to-ATS checks, a Stripe pilot, and controlled full-cohort evidence collection. Stage 4F added a multi-employer expansion. Stages 5A–5C designed adjudication and checked reviewer files; the reviewer worksheets remain blank, so no supervised benchmark exists.

## Dataset summary
- Stripe/Greenhouse: 780 records, one employer.
- Stage 4F expansion: 2200 records, 17 employers.
- Separate Naukri/ATS: 198 records.
- Main proposed integration: 2980 records.
- Raw total across all three cohorts: 3178.
- Main source families: {'stripe_greenhouse': 780, 'Greenhouse': 1747, 'Lever': 453}.
- Stage 4F near-duplicate candidates: 459; Stripe candidate pairs: 207; confirmed lineage: 0.

## Evidence and lineage
Stage 4E contains 780 Stripe evidence records. Its evidence classifications are {'independent_official_confirmation': 744, 'fresh_same_system_retrieval': 19, 'unresolved': 16, 'unavailable': 1}. Stage 4F has 91 exact description-duplicate records and 459 near-duplicate candidates. Similarity has not been converted into confirmed reposts or copy direction.

## Limitations
The expansion is concentrated in Greenhouse and Lever, with no collected Workday, SmartRecruiters, Ashby, third-party, or other-source records. Only 17 expansion employers were observed. Human annotation is incomplete: both Stage 5B reviewer label sets and all 207 Stripe pair decisions are blank. The current workspace contains no identifiable application or Streamlit loader, so runtime integration was not tested. Existing evidence is provenance evidence, not automatic ground truth.

## Readiness
| Area | Decision | Reason |
|---|---|---|
| Data collection | CONDITIONAL GO | Records are preserved, but source diversity targets were not met. |
| Evidence collection | CONDITIONAL GO | Provenance exists; authorization remains claim-specific. |
| Multi-employer evaluation | NO-GO | Source-family concentration and no ground truth. |
| Human adjudication | NO-GO | Reviewer labels and lineage decisions are blank. |
| Lineage evaluation | NO-GO | Candidates exist, confirmed edges do not. |
| Supervised model evaluation | NO-GO | No adjudicated benchmark. |
| Application integration | CONDITIONAL GO | Prepare staging only; no application loader was found. |
| Final research claims | NO-GO | Hypothesis has not been tested with valid ground truth. |

## Essential next actions
1. Complete independent human annotations and adjudicate disagreements.
2. Review lineage candidates without automatic confirmation.
3. Add and test an application loader for the proposed schema.
4. Keep Naukri separate unless compatibility and audit approval are documented.

## Recommendation
The project is ready for non-destructive staging and application integration design, but not for replacing the application dataset, supervised evaluation, or final research claims.
