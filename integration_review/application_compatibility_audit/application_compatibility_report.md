# Application compatibility report

## Answers to requested questions

**A. Can the application represent all 780 advertisements?**

The SQLite model can store one row per advertisement, but the current repository does not preserve the full proposed schema or external case identity. The disposable schema represents all 780 safely; the current application requires a staging adapter.

**B. Can it display imported advertisements without treating them as verified or legitimate?**

Not directly. The current UI has no imported-dataset loader. Its decision policy is conservative, but a future loader must keep imported evidence observations separate from labels.

**C. Can it preserve employer identity and vacancy authorization separately?**

Conceptually yes, through generic claims/annotations, but the current database does not enforce the separation. The proposed staging schema does.

**D. Can it display evidence observations and missing provenance?**

Partially. Existing evidence rendering supports observations and unavailable states, but not field-level provenance sources or explicit missingness for the proposed fields.

**E. Can it distinguish historical metadata from derived metadata?**

No. This distinction exists in the proposed staging schema, not the current application model.

**F. Can it display 192 candidate-lineage records and 207 candidate-pair references without confirming them?**

Not through the current UI/import path. The database has a lineage table, but candidate and confirmed states are not structurally separated and no candidate review panel is present. The disposable schema can do this safely.

**G. Can it preserve the existing single-vacancy review workflow?**

Yes, if staging is additive and read-only. No existing `_assess_input()` or rendering path needs to change for the current workflow.

**H. Exact functions/tables requiring future changes:**

`src/datasets/importer.py:import_csv`, `src/datasets/records.py:load_records/validate_record`, `src/database/schema.sql`, repository write/query methods, `src/evidence/collector.py:EvidenceObservation/collect_vacancy_evidence`, `src/aggregation/rules.py:naive/lineage_aware`, `src/decision/policy.py:assess`, `src/ui_support.py:evidence_ledger_rows/aggregation_summary`, and `app.py:_assess_input/_render_assessment`.

**I. Can a disposable copy use the staging database?**

Yes, after a read-only adapter or configuration-level database path is added and tested. This audit did not execute that integration. The current production database was not opened.

**J. Required tests:**

Use the test plan in `integration_test_plan.md`, including identity, cohort isolation, missingness, semantic-state, candidate-lineage, round-trip, UI regression, and production-path protection tests.

## Final decision

**CONDITIONAL PASS — specific issues must be resolved before disposable application integration.**

The architecture can support the 780-record staging model, but the current application cannot safely load and display the proposed schema without a versioned staging adapter, provenance-aware repository layer, and cohort-aware UI/read path. Production migration and behavior changes are not approved by this audit.
