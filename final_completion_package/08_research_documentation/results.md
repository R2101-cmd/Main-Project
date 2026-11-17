# Results summary

## Verified/completed technical outputs
- Repository audit, dataset reconciliation/manifest/validation, protected-file checksum record.
- Stage 4 artifact-based verification outputs for 780 Stage 4E records: `snapshot_match_only=763`, `inaccessible=1`, `independently_unresolved=16`, `independently_supported=0`, `independently_contradicted=0` (human-adjudicated). No live recheck performed.
- Stage 5 lineage packaging: 21 existing + stage4f/207-pair candidates preserved in queues; confirmed=0, rejected=0, unknown/pending=all.
- Annotation package: guidelines, human review queue (351 items total including 144 provisional cases + 207 lineage pairs), adjudication summary showing no completed independent adjudication.
- Existing automated tests: **65 passed, 2 warnings** (`python -m pytest -q`).

## Experimental and descriptive results (automated mode)
- **Automated lineage (687):** likely_dependent 430, possible_dependency 153, unknown_relationship 104, confirmed_by_direct_machine_verifiable_provenance 0. Conservative, machine-generated (not human-verified/confirmed lineage).
- **Automated verification states (780 artifact-based):** snapshot_match_only 763, independently_unresolved 16, inaccessible 1, independently_supported 0, independently_contradicted 0.
- **Synthetic (original, preserved):** completed controlled three-way run (60 records) — A/B/C accuracy 1.000, macro-F1 1.000, false assurance 0/20 on all cases (controlled implementation check only).
- **Extended synthetic (new, versioned, synthetic-only):** 30 records covering dependence/copy/contradiction/unavailable/unknown/independent scenarios; three-way results in `final_completion_package/automated_mode/extended_synthetic_three_way/` (not real-world ground truth).
- **Real-world descriptive analysis:** retrieval/availability/match/snapshot-only/unresolved/contradiction/duplicate/candidate-lineage rates and conservative independence/decision-abstention distributions reported in `final_completion_package/automated_mode/descriptive_real_data_analysis.json` and `descriptive_metrics.csv` — **descriptive system outputs only, no ground-truth performance metrics**.
- **Application/tests:** Streamlit automated-mode demo and AppTest smoke passed; pytest **73 passed, 2 warnings**. Hypothesis **not proven**.

## Conclusion
Engineering/prototype artifacts and evaluation scaffolding are advanced, but **the central hypothesis is not experimentally proven** with defensible real-world evidence in this execution.
