# Limitations

- **No human-verified ground truth (automated mode):** manual review/adjudication is not required for execution and no human labels are fabricated. Employer identity, vacancy authorization, and fraud outcomes on real data are not treated as adjudicated labels.
- **No confirmed lineage by human adjudication:** 687 candidates processed by automated scoring (likely dependent/possible dependency/unknown or machine-verifiable provenance where evidenced). Similarity-based relationships are not confirmed lineage; unknown relationships are not assumed independent. Independence estimates are conservative and descriptive.
- **Stage 4 not independently live-verified:** classifications derived from existing collected artifacts; `independently_supported/contradicted` require authority-confirmed retrieval and human adjudication.
- **Dataset bias/concentration:** 780 cohort single-employer/source-family; 2,980 proposed package Greenhouse/Lever-heavy (17 employers), missing target diversity (e.g. Workday/SmartRecruiters/Ashby/third-party in reported collection) and limited generalization.
- **Naukri comparability unestablished:** 198 records kept separate.
- **Evaluation validity:** provisional results are single-reviewer/exploratory; leakage-safe grouped splits and fair thresholds need adjudicated, lineage-aware benchmark. Synthetic results do not generalize to real recruitment data.
- **Integration:** no validated staging loader/UI cohort integration for proposed package; live end-to-end and batch (~3k) application tests not completed.
- **Evidence interpretation:** snapshot/retrieval matches and third-party/ATS listings do not by themselves prove employer authorization.
