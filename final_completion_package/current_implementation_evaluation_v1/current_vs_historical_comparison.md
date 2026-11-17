# Current vs historical evaluation

Historical Stage 7B and this v3 evaluation use different test cases and different frozen implementation points. Percentages below are separate descriptive results; their differences are not interpretable as direct improvement or degradation. Historical metrics are preserved in `final_completion_package/synthetic_evaluation_v2/`.

| Stage 7B approach | Accuracy | Macro F1 | False assurance / denominator | Coverage |
|---|---:|---:|---:|---:|
| A_text_only | 0.550 | 0.549 | 10/40 | 0.700 |
| B_ordinary_aggregation | 0.867 | 0.861 | 8/40 | 0.800 |
| C_lineage_aware_aggregation | 1.000 | 1.000 | 0/40 | 0.667 |

Current v3 raw and live-policy metrics are in `metrics_summary.json`; the live C policy has no exact historical counterpart.
