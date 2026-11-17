# Limitations

- All 60 test cases and their expected labels are synthetic; metrics are not real-world accuracy or evidence of operational performance.
- The test set contains all 15 scenario families seen in train and validation. No unseen-scenario generalization is tested.
- There are only four test examples per scenario family and 20 per expected class; confidence intervals and per-family metrics are imprecise.
- Text-only classification is a small TF-IDF/logistic-regression baseline trained on 180 synthetic examples. It is not a validated production language model.
- The scenario construction explicitly encodes evidence states and lineage. Results depend on those authored scenarios and do not establish that real official sources, ATS control, or lineage can be identified with the same reliability.
- B and C are deterministic production aggregation functions. Their behavior reflects current rules, including conservative exclusion of unverified lineage and aggregation's contradiction precedence.
- The paired significance test has low power at this sample size. A non-significant result is not evidence of equivalence.
- No real advertisement records, evidence rows, annotations, or historical evaluation outputs were used as labels or modified.
