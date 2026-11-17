# TrustHire Stage 5A Research Readiness Report

## Decision

**CONDITIONAL GO** for Stage 5B design implementation, but not for supervised model training or final hypothesis testing yet.

## Dataset audit

- Stripe/Greenhouse cohort: 780 records, 780 unique case IDs, 1 employer ID.
- Naukri/ATS cohort: 198 records.
- Cross-dataset case-ID overlap: 0.
- Unique Stripe vacancy identifiers: 780.
- Exact duplicate advertisement groups in Stripe: 0.
- Near-duplicate candidate pairs in Stripe: 207.
- Confirmed reposts: 0.
- Independent source relationships in Stripe: 0.
- Incomplete lineage records: 780 (Table A has no lineage-group/source-parent fields).

The Stripe records derive from one Greenhouse/Stripe source family. It supports source-consistency and authorization-evidence evaluation, but it has limited lineage variation. The 198-record Naukri dataset should remain a separate, explicitly labelled lineage experiment.

## Ground truth

Table B contains no independently reviewed cases. All 780 records remain unresolved/pending, with no evidence-backed authorization labels, employer identity labels, or fraud outcomes. Stage 4E evidence must not be converted automatically into ground truth.

Human adjudication requires two independent annotators, blinded duplicate cases, explicit evidence references, separate employer and authorization labels, and an adjudication log. Missing evidence must remain distinct from contradiction.

## Evidence reconciliation

The six evidence states are mutually exclusive. Snapshot consistency and fresh same-system retrieval do not establish independent authorization. Independent official confirmation is candidate positive evidence, not an automatic ground-truth label. Unavailable and unresolved remain unresolved; contradiction requires an explicit authoritative conflict.

## Evaluation design

The three approaches must use identical adjudicated case IDs and grouped splits:

1. Text-only baseline: advertisement text and text-derived features only.
2. Ordinary evidence aggregation: evidence fields without source/lineage dependency correction.
3. Lineage-aware aggregation: source-family deduplication, lineage grouping, retrieval/source independence, freshness, contradictions, and missingness.

Exact and near-duplicate groups must not cross train, validation, and test splits. The current Stripe data has insufficient verified lineage variation to test the hypothesis strongly by itself.

## Metrics

Primary metrics are false-assurance rate, precision, recall, F1, specificity, unresolved decision rate, coverage, contradiction handling, repost-group performance, and incomplete-evidence performance. Accuracy must not be used as the sole metric. No supervised metrics are currently meaningful because ground truth is unresolved.

## Required before Stage 5B

1. Complete human adjudication for a calibration and evaluation subset.
2. Manually review the 207 Stripe near-duplicate candidate pairs or define a sampled lineage protocol.
3. Create grouped, leakage-safe splits after adjudication.
4. Define the positive authorization target and treatment of unresolved cases before scoring.
5. Keep the Naukri lineage experiment separate from the Stripe benchmark.
6. Freeze the test set and annotation protocol before model evaluation.
