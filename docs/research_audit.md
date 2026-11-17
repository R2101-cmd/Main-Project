# Research audit

Audit date: 2026-10-22. This audit describes files actually present in the repository; it does not treat a generated file as human validation.

## Architecture

The repository contains ingestion and extraction (`src/ingestion`), claim-level evidence collection (`src/evidence`), SQLite persistence (`src/database`), candidate lineage similarity (`src/lineage`), aggregation (`src/aggregation`), abstention policy (`src/decision`), a TF-IDF/logistic-regression text baseline (`src/ml`), and evaluation utilities (`src/evaluation`). The Streamlit interface is optional and is not the research evaluator.

## Data and counts

| Artifact | Records | Groups | Authorization labels | Status |
|---|---:|---:|---|---|
| `data/annotations/pilot.jsonl` | 4 | 4 | 2 supported, 2 unresolved | single-reviewer pilot |
| `data/annotations/job_ad_authorization_evaluation.jsonl` | 145 | 143 | 12 supported, 133 unresolved | provisional evidence-derived benchmark |
| `data/annotations/job_ad_independent_review_v1.jsonl` | 31 | 29 | 12 supported, 19 unresolved | provisional single-reviewer subset; no second reviewer |

The 145-record artifact contains 145 evidence items: 13 supported, 1 contradicted, and 131 unverified. The 31-record subset contains 13 supported, 1 contradicted, and 17 unverified evidence items. There are no defensible confirmed-fraud or confirmed-legitimate outcomes in these artifacts.

## Methods

- E1 text-only: TF-IDF word n-grams with logistic regression, fitted on the training partition.
- Naive evidence: counts every evidence appearance and prioritizes contradiction, then support, then unresolved.
- Lineage-aware evidence: removes repeated items sharing a known dependent lineage key before applying the naive rule.
- Employer-context, metadata, and text-plus-metadata baselines are not yet implemented in the evaluator.

## Defects and risks

1. The earlier `job_ad_independent_review_v1.jsonl` was generated from the existing evidence-derived artifact. It is not independent multi-reviewer ground truth; its provenance is now explicitly marked provisional.
2. The evaluator previously saved aggregate results only and did not emit predictions, a split manifest, a case-level E4/E5 comparison, or a configuration artifact.
3. The evidence aggregation code has no calibrated sufficiency threshold and can return `supported` from one supported observation. This is a rule-based assessment, not a probability.
4. The current lineage implementation uses a manually supplied dependent-group key and does not itself validate whether that relationship was manually reviewed.
5. The 145-record workbook includes 100 search-result candidates whose individual advertisement pages were not captured. These records are useful for collection planning but not equivalent to independently verified vacancies.
6. The evaluation labels and evidence are not independent for the provisional benchmark; evidence-derived metrics must not be presented as unbiased model performance.

## What can be claimed

The repository demonstrates a traceable vacancy-authorization workflow, explicit unresolved states, evidence provenance fields, group-aware leakage checks, and an abstaining evidence comparison. It does not yet establish that lineage-aware aggregation improves authorization verification, nor does it detect fraud generally. A publication-quality claim requires independently reviewed labels, affirmative contradiction examples, reviewed lineage references, and a larger test set.
