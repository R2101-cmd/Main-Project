# Required code changes for a future implementation

No changes were implemented in this audit.

Future changes would be required in:

- `src/datasets/importer.py`: add a read-only, cohort-aware staging CSV loader that preserves external `case_id` and all original/recovered fields.
- `src/datasets/records.py`: validate cohort IDs, provenance status, evidence states, missingness, and label separation.
- `src/database/schema.sql`: use a versioned migration or separate staging database; add cohort, provenance, source-family, retrieval-event, and candidate/confirmed-lineage structures.
- `src/database/repository.py`: add read-only staging queries and explicit external-ID handling; do not reuse UUID generation for imported case identity.
- `src/evidence/collector.py`: extend observation serialization for source independence, retrieval independence, response hashes, and field-level provenance.
- `src/aggregation/rules.py`: accept explicit source-family and confirmed-lineage inputs; do not count same-source observations as independent.
- `src/decision/policy.py`: preserve unresolved/unavailable/unverified separately and prevent evidence observations from becoming ground truth labels.
- `src/ui_support.py` and `app.py`: add cohort filtering, provenance display, and candidate-only lineage display while preserving the current single-vacancy route.
- `src/evaluation/runner.py`: accept only independently adjudicated benchmark records; never use this staging import as ground truth.

No migration should be made until the disposable integration test passes and the staging database is versioned separately from the production SQLite file.
