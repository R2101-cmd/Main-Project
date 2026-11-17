from pathlib import Path
from datetime import datetime, timezone

OUT=Path(r'C:\Users\Admin\Desktop\Main Project\integration_review\application_compatibility_audit')
stamp=datetime.now(timezone.utc).isoformat()
docs={
'application_model_mapping.md':'''# Application model mapping

## Existing application model

`app.py` is a single-vacancy Streamlit workflow. `_assess_input()` extracts one advertisement, obtains permitted public sources, calls `collect_vacancy_evidence()`, then sends the observations to `naive()`, `lineage_aware()`, and `assess()`. The result is held in Streamlit session state and rendered by `_render_assessment()`.

The SQLite model contains `advertisements`, `claims`, `evidence`, `lineage_relationships`, `annotations`, `source_records`, and `model_runs`. `Repository.add_advertisement()`, `add_evidence()`, `add_lineage_relationship()`, `add_claim()`, and `add_source_record()` write individual workflow records.

## Proposed staging mapping

| Proposed staging concept | Existing application representation | Compatibility |
|---|---|---|
| 780 advertisements | `advertisements` row per record | Possible, but no batch CSV loader or cohort field |
| cohort identity | None | Missing |
| employer identity claim | Generic `annotations` dimension or `claims` | Possible but not enforced separately |
| vacancy authorization claim | `evidence.evidence_state` plus generic annotation | Possible, but evidence is not ground truth |
| evidence observation | `evidence` | Partial; source hashes/independence fields are missing |
| source family/instance | None | Missing |
| retrieval event | `source_records.observed_at` only | Partial; no event ID or event table |
| response hash | `source_records.content_hash` | Partial; not linked to a retrieval-event model |
| candidate lineage | `lineage_relationships` | Partial; current table does not enforce candidate-only state |
| confirmed lineage | Same `lineage_relationships` table | Unsafe without status constraints |
| provenance field source/missingness | None | Missing |

The disposable schema can represent the proposed data safely. The current application model cannot represent all provenance semantics without an adapter or versioned migration.
''',
'repository_compatibility.md':'''# Repository and database compatibility

## Findings

The current repository is write-oriented and generates UUIDs for advertisements, evidence, lineage relationships, claims, and source records. It has no read-only import method for `disposable_staging_import.csv`, no cohort-aware query, and no method for preserving an external `case_id` as a first-class key.

`schema.sql` lacks cohort, source-family, source-instance, retrieval-event, missingness, provenance-field-source, and confirmed-versus-candidate lineage separation. `annotations` stores one generic dimension and label, so it can technically store separate dimensions but does not enforce the three-claim protocol.

## Safety conclusion

The application must not import the staging CSV directly through the current repository. A future adapter should be read-only first, retain `case_id`, and write only to a versioned staging database. The production database must remain unchanged until migration design and tests are approved.

The proposed staging schema correctly leaves `retrieval_events` empty for all 780 records and records missingness separately. It also keeps the confirmed-lineage table empty and candidate lineage separate.
''',
'ui_compatibility.md':'''# UI compatibility

## Current support

The existing UI supports pasted text, public URL, and poster-image input. It displays extracted fields, evidence availability, field comparisons, evidence states, naive aggregation, lineage-aware aggregation, and unresolved warnings. It explicitly states that unavailable evidence is not fraud and that employer identity does not itself authorize a vacancy.

The existing single-vacancy workflow can be preserved unchanged if the staging dataset is used only by a separate read-only browser or as a fixture source.

## Missing UI capabilities

The UI has no batch-record loader, cohort selector, 780-record table, source-family/source-instance display, provenance-field-source display, explicit historical-versus-derived marker, or candidate-lineage review panel. It also does not display the proposed staging database claims as imported records.

Candidate lineage should be shown as “candidate/unadjudicated”; it must never be rendered as confirmed. Labels should remain blank or unresolved. A future UI must show employer identity and vacancy authorization as separate claims.
''',
'required_code_changes.md':'''# Required code changes for a future implementation

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
''',
'integration_test_plan.md':'''# Application integration test plan

Run only in a disposable copy or against the disposable staging database.

1. Import exactly 780 records and assert 780 unique external case IDs.
2. Assert cohort is exclusively `stripe_greenhouse_780`; reject Stage 4F and Naukri IDs.
3. Assert all original/recovered fields round-trip without changes.
4. Assert missing `retrieval_event_id` remains missing and creates no synthetic event rows.
5. Assert source-family/source-instance metadata remains marked derived where applicable.
6. Assert evidence observations do not populate authorization or fraud ground-truth labels.
7. Assert employer identity and vacancy authorization are separate claims.
8. Assert 192 candidate-involved records and 207 candidate-pair references remain candidate-only.
9. Assert confirmed-lineage count is zero.
10. Assert unavailable, unverified, unresolved, and contradicted states remain distinct.
11. Assert the existing single-vacancy workflow still handles pasted text, URL, and poster fixtures.
12. Assert no production database path is opened and no production tables are written.
13. Run the existing regression suite with cache and bytecode disabled; expected baseline is 65 passed, 2 warnings.
14. Test UI pagination/filtering only after the read-only loader is validated.

The integration test should fail closed on cohort contamination, duplicate external IDs, invalid labels, fabricated retrieval events, or candidate-to-confirmed lineage conversion.
''',
'application_compatibility_report.md':'''# Application compatibility report

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
'''
}
OUT.mkdir(parents=True,exist_ok=True)
for name,text in docs.items():(OUT/name).write_text(text,encoding='utf-8')
print('created',len(docs),OUT)
