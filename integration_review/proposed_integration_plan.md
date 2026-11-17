# Proposed safe integration plan

This is a plan only. It was not implemented.

## Recommended order

1. Add a read-only staging loader outside the current runtime path for `unified_proposed_dataset.csv`.
2. Validate the package against the data dictionary and cohort manifest before any database write.
3. Store original `case_id`, `cohort_id`, `source_family_id`, `source_instance_id`, `retrieval_event_id`, and response hashes without overwriting existing IDs.
4. Keep Naukri in a separate staging table or separate database and separate metrics namespace.
5. Add explicit evidence rows for employer identity and vacancy authorization, retaining `unavailable` and `unresolved` distinctly.
6. Store candidate lineage separately from human-confirmed/adjudicated lineage.
7. Join human labels only after reviewers and adjudicator complete the Stage 5B/5C artifacts.
8. Add group-aware split construction that keeps same-vacancy, source-family, and confirmed lineage groups together.

## Files/functions that would need future modification

- Add a loader module near `src/datasets/importer.py` for the proposed CSV and cohort manifest.
- Extend `src/datasets/records.py` validation for cohort/provenance/evidence-state fields.
- Extend `src/database/schema.sql` and `src/database/repository.py` only through a versioned migration, not by replacing the existing database.
- Update `src/evidence/collector.py` data structures to preserve source family, source instance, retrieval event, hashes, and field-level comparisons.
- Update `src/aggregation/rules.py` to accept explicit source-independence and confirmed-lineage inputs.
- Update `src/decision/policy.py` only after the claim-state mapping is reviewed; preserve unresolved as an outcome.
- Update `src/ui_support.py` and `app.py` for cohort filtering and provenance display.
- Update `src/evaluation/runner.py` only for a separately validated adjudicated benchmark; do not use the proposed package as ground truth.

## Dataset to use first

Use the 780-record Stripe cohort first for a read-only staging smoke test because its source schema and evidence history are best documented. Do not use it as a supervised benchmark until human annotation is complete. Add Stage 4F only after the loader passes cohort/provenance tests. Keep Naukri separate.
