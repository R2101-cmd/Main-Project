# TrustHire final research package

This package was generated non-destructively. The proposed unified dataset contains 2,980 main-cohort records: 780 Stripe/Greenhouse and 2,200 Stage 4F expansion records. The 198-record Naukri/ATS cohort is included only as a separately identified copy and is not in the main unified dataset.

Validation is structural only. Human ground truth, adjudicated lineage, source-family balance, and application integration are not approved. Do not replace the current application data automatically.

Recommended loading order: validate `validation_report.json`; load `unified_proposed_dataset.csv` into a staging table; retain `cohort_id`; join evidence and adjudicated labels only when available; keep Naukri behind a separate cohort filter.
