# Research evaluation report v1

## 1. Research objective

This report evaluates vacancy authorization verification, not universal fake-job detection or final fraud outcomes.

## 2. Research question and hypotheses

Does lineage-aware aggregation improve vacancy authorization verification compared with text-only and ordinary evidence aggregation when advertisements are reposted or evidence is incomplete? The primary hypothesis is a reduction in false assurance.

## 3. Architecture

The system contains ingestion/extraction, claim-level evidence collection, SQLite persistence, candidate lineage similarity, naive and lineage-aware aggregation, abstention policy, TF-IDF/logistic-regression text baseline, and evaluation utilities.

## 4. Dataset and annotation status

The evaluated artifact contains **31 records**, **29 groups**, and **12 test records** across **10 test groups**. The status is `provisional_not_independent_ground_truth`. The provisional reference labels contain 12 supported and 19 unresolved records; no contradicted records.

## 5. Annotation protocol

Labels were assigned with the v2 protocol rules: direct role-specific employer/institutional evidence can support authorization; third-party-only, stale, inaccessible, or insufficient evidence remains unresolved; absence from a careers page is not contradiction. The current set has one protocol-based reviewer and no second-reviewer agreement or adjudication.

## 6. Lineage methodology

Lineage-aware aggregation consolidates only explicitly supplied dependent lineage keys. Text similarity, shared URLs, and shared contact details are candidate signals and require review. No source consolidation occurred in this test set.

## 7. Leakage prevention

The split contains 19 training and 12 test records. Leakage groups: 0. All records from the same vacancy group remain in one partition.

## 8. Experimental methods

- E1: TF-IDF word unigrams/bigrams plus logistic regression, fitted on training text only.
- E2: not run; the benchmark JSONL does not provide a frozen structured-feature training interface.
- E3: not run; employer-context reference labels/features are not independently available.
- E4: naive evidence aggregation.
- E5: lineage-aware evidence aggregation.

## 9. Results

| Method | Accuracy | Balanced accuracy | Precision | Recall | F1 | Macro F1 | Weighted F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| E1 text-only | 0.500 | 0.500 | 0.000 | 0.000 | 0.000 | 0.222 | 0.333 |
| E4 naive evidence | 0.833 | 0.833 | 0.857 | 1.000 | 0.923 | 0.574 | 0.862 |
| E5 lineage-aware | 0.833 | 0.833 | 0.857 | 1.000 | 0.923 | 0.574 | 0.862 |

Confusion-matrix label order is `[contradicted, supported, unresolved]`.

- E1: `[[0, 0, 0], [0, 0, 6], [0, 0, 6]]`
- E4: `[[0, 0, 0], [0, 6, 0], [1, 1, 4]]`
- E5: `[[0, 0, 0], [0, 6, 0], [1, 1, 4]]`

## 10. E4 versus E5 case comparison

{
  "agree": 12,
  "e4_wrong_e5_correct": 0,
  "e4_correct_e5_wrong": 0,
  "both_wrong": 0,
  "e5_definitive_to_unresolved": 0,
  "e5_unresolved_to_definitive": 0
}

False assurance: E4 `1` / 6 non-supported cases; E5 `1` / 6. Evidence coverage was 100.0%; no source consolidation occurred.

## 11. Error and abstention analysis

The text baseline predicted the unresolved class for all test records, producing zero supported recall. E4 and E5 made identical decisions. Evidence methods abstained on unresolved cases; decision coverage and abstention must be read from the method-specific selective metrics in the JSON artifact, not confused with evidence coverage.

## 12. Limitations and threats to validity

The test set is small, has no contradicted class, and uses provisional single-reviewer labels whose provenance is tied to the collected evidence. This creates circularity risk for evidence methods. There is no inter-annotator agreement, no reviewed lineage gold standard, no fraud-outcome benchmark, and no statistically defensible superiority claim.

## 13. Research contribution supported by results

The implementation supports traceable evidence, unresolved outcomes, group-aware splitting, and a reproducible comparison pipeline. The current results do **not** establish that lineage-aware aggregation improves over naive aggregation.

## 14. Conclusion and next experiments

The finding is inconclusive. The next priority is independent double annotation of a larger fixed sample containing affirmative contradictions and reviewed repost families, followed by adjudication and a new frozen test set.

## 15. Reproducibility

```powershell
python scripts\build_independent_review.py
python scripts\run_research_evaluation.py
python scripts\render_research_report.py
pytest -q
```

Artifacts are saved under `artifacts/experiments/research_v1/`: aggregate metrics, predictions, split manifest, and experiment configuration.
