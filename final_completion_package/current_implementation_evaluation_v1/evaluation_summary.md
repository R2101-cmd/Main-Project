# Current implementation synthetic evaluation

| Approach | Accuracy | Macro F1 | False assurance / non-supported | Coverage |
|---|---:|---:|---:|---:|
| A_text_only | 0.367 | 0.276 | 82/100 (0.820) | 0.9066666666666666 |
| B_ordinary_aggregation | 0.800 | 0.775 | 25/100 (0.250) | 0.8666666666666667 |
| C_lineage_aware_raw | 0.867 | 0.857 | 15/100 (0.150) | 0.8 |
| C_lineage_aware_live_policy | 1.000 | 1.000 | 0/100 (0.000) | 0.6666666666666666 |


C raw minus B: accuracy +0.067, macro F1 +0.083, false-assurance rate -0.100, coverage -0.067. C live minus B: accuracy +0.200, macro F1 +0.225, false-assurance rate -0.250, coverage -0.200. The perfect C live score is mechanically aligned with the authored evidence rules and is a policy-conformance result on this constructed set, not an estimate of generalization or real-world accuracy.

The 150 records are authored synthetic cases (50 per design label), not human-reviewed ground truth. The same cases were presented to all approaches; A sees advertisement text only, while B/C use evidence. C live-policy is the current conservative final decision path. False-assurance rate denominator is all 100 expected non-supported cases. Coverage is the fraction predicted supported or contradicted; unresolved is abstention. See per-class metrics and matrices in JSON.

## Class distributions and confusion matrices

See `metrics_summary.json` and `confusion_matrices.json` for per-class precision, recall, F1 and all confusion counts.
