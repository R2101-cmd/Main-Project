# E1–E5 Experimental Comparison

Source: `artifacts/experiments/e2_e3_mvp.json`, using the 145-record provisional annotation artifact. This is not real-world accuracy: the evaluation has circularity risk, only one supported test case, and no contradicted test cases.

| Method | Status | Accuracy | Balanced accuracy | Macro F1 | Confusion matrix | Missing test classes |
|---|---|---:|---:|---:|---|---|
| E1 Text-only | run | 0.9375 | 0.5000 | 0.3226 | `[[0, 0, 0], [0, 0, 1], [0, 0, 15]]` | contradicted |
| E2 Text + Metadata | run | 0.9375 | 0.5000 | 0.3226 | `[[0, 0, 0], [0, 0, 1], [0, 0, 15]]` | contradicted |
| E3 Employer-Context | run | 0.9375 | 0.5000 | 0.3226 | `[[0, 0, 0], [0, 0, 1], [0, 0, 15]]` | contradicted |
| E4 Ordinary evidence | run | 0.9375 | 0.5000 | 0.3226 | `[[0, 0, 0], [0, 0, 1], [0, 0, 15]]` | contradicted |
| E5 Lineage-aware evidence | run | 0.9375 | 0.5000 | 0.3226 | `[[0, 0, 0], [0, 0, 1], [0, 0, 15]]` | contradicted |

Confusion-matrix label order is `[contradicted, supported, unresolved]`. E2 and E3 are executable training-fitted token baselines; their results are provisional and must not be interpreted as validated improvements.
