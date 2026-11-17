# Data splitting and leakage control

All records from the same underlying vacancy or repost/lineage group must share one partition. The evaluator rejects groups appearing in multiple partitions. Text vectorizers and classifiers are fitted on training text only.

The current provisional review split contains 19 training records and 12 test records across 10 test groups, with no detected leakage. The split is stored in `data/annotations/job_ad_independent_review_v1.jsonl`; the reproducible runner also emits a split manifest under `artifacts/experiments/`.

The split is exploratory because the reviewed subset has only 31 records, 12 supported labels, 19 unresolved labels, and no contradicted labels. Employer-held-out evaluation is not currently available because employer-level reviewed groups are too sparse and are not frozen in a manifest.
