# TrustHire Metric Analysis

Generated from existing prediction/label artifacts only. No datasets, annotations, benchmarks, source code, model logic, or labels were modified.

## Scope and integrity

- Synthetic v2 and current synthetic v3 are reported separately; no metrics are combined across versions.
- The provisional 145-record evaluation is reported separately and flagged as circularity-risk/evidence-derived.
- v3 prediction keys were checked against the 150 expected-label keys: exact one-to-one alignment.
- v2 contains 60 test cases with 20 cases per class; all methods use the same test cases.
- The provisional test contains 16 records: 15 unresolved, 1 supported, and 0 contradicted; this is insufficient for class-balanced claims.
- Accuracy and false-assurance 95% intervals are Wilson intervals where raw vectors were available. Per-class recall Wilson intervals are included. Precision, F1, macro metrics, and balanced accuracy have no simple binomial interval here and are reported without fabricated intervals.

## Summary

| Benchmark | Method | n | Accuracy | Balanced accuracy | Macro F1 | False assurance | Coverage | Selective accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| synthetic_v2 | E1_text_only | 60 | 0.550 | 0.550 | 0.549 | 0.250 (10/40) | 0.700 | 0.548 |
| synthetic_v2 | E4_ordinary_aggregation | 60 | 0.867 | 0.867 | 0.861 | 0.200 (8/40) | 0.800 | 0.833 |
| synthetic_v2 | E5_lineage_aware_aggregation | 60 | 1.000 | 1.000 | 1.000 | 0.000 (0/40) | 0.667 | 1.000 |
| synthetic_v3_current_implementation | E1_text_only | 150 | 0.367 | 0.367 | 0.276 | 0.820 (82/100) | 0.907 | 0.353 |
| synthetic_v3_current_implementation | E4_ordinary_aggregation | 150 | 0.800 | 0.800 | 0.775 | 0.250 (25/100) | 0.867 | 0.769 |
| synthetic_v3_current_implementation | E5_lineage_aware_raw | 150 | 0.867 | 0.867 | 0.857 | 0.150 (15/100) | 0.800 | 0.833 |
| synthetic_v3_current_implementation | E5_lineage_aware_live_policy | 150 | 1.000 | 1.000 | 1.000 | 0.000 (0/100) | 0.667 | 1.000 |
| provisional_145_record_evaluation | naive_evidence | 16 | 0.938 | 0.500 | 0.323 | 0.000 (0/15) | 0.000 | NA |
| provisional_145_record_evaluation | lineage_aware_evidence | 16 | 0.938 | 0.500 | 0.323 | 0.000 (0/15) | 0.000 | NA |
| provisional_145_record_evaluation | text_only_baseline | 16 | 0.938 | 0.500 | 0.323 | NA | NA | NA |
| provisional_145_record_evaluation | E2_text_plus_metadata | 16 | 0.938 | 0.500 | 0.323 | NA | NA | NA |
| provisional_145_record_evaluation | E3_employer_context | 16 | 0.938 | 0.500 | 0.323 | NA | NA | NA |

## Per-class and confusion-matrix outputs

Complete per-class precision, recall, F1, support, recall intervals, and confusion matrices are in `metrics_complete.json`, `per_class_metrics.csv`, and `confusion_matrices.json`.

## Interpretation and limitations

- Synthetic v2/v3 metrics are valid calculations for their authored benchmarks, but their labels are synthetic design labels. They are implementation checks, not real-world performance estimates.
- The current v3 live-policy E5 result must not be called operational accuracy: its labels are constructed from the same policy conditions.
- The provisional metrics are not suitable for paper performance claims because the labels are evidence-derived, the test set is tiny, and the contradicted class is absent.
- Accuracy alone is inadequate because unresolved abstention is a meaningful outcome. Report coverage, selective accuracy, abstention, false assurance, per-class recall, and confusion matrices together.
- Macro metrics are preferable to weighted metrics under class imbalance, but macro values are unstable when a class has few or zero test examples.
- No real-world accuracy is available for the 2,980-record cohort or the separate 198-record Naukri cohort.

## Research-paper suitability

Suitable: benchmark-specific synthetic accuracy, per-class metrics, confusion matrices, Wilson intervals, coverage, selective accuracy, and false-assurance rates when explicitly labeled as synthetic implementation results.

Not suitable as real-world claims: any extrapolation from v2/v3 to deployment, any claim of improved real-world E5 performance, and any accuracy claim for the 2,980-record collected cohort without independent adjudication.

## Protected-file confirmation

Protected annotation and synthetic split hashes remained unchanged during this analysis; no protected dataset, label, annotation, benchmark, or model file was modified.
