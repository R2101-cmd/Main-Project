from pathlib import Path
from datetime import datetime, timezone

APP=Path(r'C:\Users\Admin\Desktop\Main Project')
OUT=APP/'integration_review'
created=datetime.now(timezone.utc).isoformat()

docs={
'application_architecture.md':f'''# TrustHire application architecture review

Audit time: {created}. Inspection only; no application files were changed.

## Current architecture

`app.py` is a Streamlit single-review workflow. It imports `Repository` and `DEFAULT_DATABASE`, but normal verification is held in Streamlit session state; the SQLite repository is used when a poster image is submitted to persist an advertisement and source record.

Input flow:

1. `_render_input_panel()` accepts pasted text, a public URL, or a poster image.
2. `_assess_input()` extracts fields with `src.ingestion.content_extractor.extract_text` or OCR, discovers explicit/specific public URLs, and calls `collect_vacancy_evidence`.
3. `naive()` and `lineage_aware()` create separate aggregate assessments.
4. `assess()` produces a conservative vacancy-authorization action.
5. `_render_assessment()` displays evidence, comparisons, availability, and unresolved warnings.

Relevant modules:

- `src/ingestion/content_extractor.py`: HTML/JSON-LD/meta extraction.
- `src/ingestion/url_fetcher.py`: public URL validation and retrieval.
- `src/evidence/collector.py`: evidence observations and field comparison.
- `src/aggregation/rules.py`: naive and lineage-aware aggregation.
- `src/decision/policy.py`: supported/contradicted/unresolved decision policy.
- `src/database/repository.py` and `src/database/schema.sql`: SQLite persistence.
- `src/lineage/similarity.py`: candidate similarity only.
- `src/evaluation/runner.py`: JSONL evaluation workflow requiring reviewed authorization labels and partitions.

No application-level loader for `final_research_package/unified_proposed_dataset.csv` was found. No Streamlit page for browsing the 2,980-record package was found. The existing application is therefore not a drop-in batch dataset viewer.

## Current behaviour that is safe

The UI preserves unavailable evidence as unresolved, explicitly warns that retrieval failure is not fraud, separates naive from lineage-aware aggregation, and states that a verified employer does not by itself authorize a vacancy. Poster input is already supported through OCR.

## Current behaviour that is incomplete for the final package

The workflow does not persist or display `cohort_id`, `source_family_id`, `source_instance_id`, response hashes, canonical vacancy IDs, evidence independence, publication/update dates, or the separate employer-identity/authorization/fraud labels from the proposed package. `lineage_aware()` only consolidates explicitly supplied lineage groups and the UI does not load candidate/confirmed lineage tables from CSV.
''',
'current_schema.md':'''# Current application schema

## SQLite tables

`src/database/schema.sql` defines:

- `advertisements(id, input_type, source_url, raw_text, retrieval_status, observed_at, synthetic)`
- `claims(id, advertisement_id, claim_type, value, extraction_state)`
- `evidence(id, advertisement_id, claim_type, source_url, source_type, observed_at, source_timestamp, retrieval_status, summary, evidence_state, rationale)`
- `lineage_relationships(id, left_advertisement_id, right_advertisement_id, relationship, similarity, rationale, reviewer_decision, created_at)`
- `annotations(id, advertisement_id, dimension, label, rationale, annotator, created_at)`
- `source_records(id, advertisement_id, source_type, source_url, content_hash, raw_content, extracted_text, retrieval_status, observed_at, warnings_json)`

Current evidence states are `supported`, `contradicted`, `unverified`, and `unavailable`. Current lineage relationships are `original`, `independent`, `copied_derived`, and `unknown`.

## Proposed package schema comparison

The proposed package adds stable cohort and source identity (`cohort_id`, `source_family_id`, `source_instance_id`), retrieval provenance, response hashes, canonical vacancy identity, explicit evidence/source independence, separate identity/authorization/fraud labels, and lineage review fields. These do not map one-to-one into the current SQLite schema.

The proposed CSV also uses `case_id` and `employer_id`, while the application database uses generated UUID advertisement IDs. A compatibility layer must retain both the original `case_id` and an internal database key; it must not replace the original ID.

Current schemas do not represent cohort membership, source-family identity, retrieval-event identity, update date, official employer URL, or separate employer identity and vacancy authorization evidence states.
''',
'dataset_compatibility.md':'''# Dataset compatibility review

## Cohorts

| Cohort | Records | Integration status |
|---|---:|---|
| Stripe/Greenhouse | 780 | Suitable for staging as a separate cohort |
| Stage 4F expansion | 2,200 | Suitable for staging with provenance warnings |
| Naukri/ATS | 198 | Must remain separate; not in the proposed unified main dataset |

The proposed main CSV contains 2,980 records. The final package validation report had no structural errors, but it recorded unresolved warnings for missing human ground truth, incomplete source-family diversity, and missing application integration tests.

## Compatibility findings

- Stable IDs can be preserved as `case_id`; the application must maintain an internal database ID separately.
- Existing text fields map reasonably to title, description, and location.
- Existing evidence records are observation-oriented and use `unverified`; the proposed package needs an explicit mapping to unresolved/unavailable without collapsing distinctions.
- Existing SQLite evidence has no response-hash, source-family, retrieval-event, or source-independence columns.
- Existing lineage storage can represent a reviewed pair but not the full candidate-versus-confirmed workflow or cohort-scoped lineage groups.
- Existing annotations are generic dimension/label rows, while the proposed package has three explicitly separate claims.
- Existing application data is case-by-case; importing 2,980 records would need a batch importer and an explicit cohort filter.

## Duplicate and leakage risks

Different URLs must not be treated as independent. Source families and source instances must be retained. Candidate similarity must not become a confirmed repost. Group-aware partitions are required before any model evaluation; the existing evaluation runner rejects missing labels and cross-partition lineage groups, but it expects JSONL evaluation records rather than this CSV.
''',
'integration_risks.md':'''# Integration risks

1. **Ground-truth leakage:** Stage 4E evidence classifications are not human ground truth. Loading them into `annotations` would create circular evaluation.
2. **Source independence inflation:** Greenhouse, employer pages, and copied postings may belong to one source family. Repeated retrievals are not independent authorization.
3. **Schema loss:** A direct import into the current SQLite tables would discard cohort, source-instance, response-hash, canonical-vacancy, freshness, and separate claim fields.
4. **Label collision:** Existing `supported` evidence states are not equivalent to adjudicated `vacancy_authorization_label=supported`.
5. **Lineage overclaim:** `src.lineage.similarity.candidate_relationship()` returns a candidate relationship; it does not establish human-confirmed lineage.
6. **Decision-policy limitation:** `src.decision.policy.assess()` treats any retrieval failure as a reason to abstain but does not model source independence, freshness, or explicit employer identity evidence.
7. **Batch-scale risk:** The UI has no pagination, cohort selector, package loader, or batch evidence ledger for approximately 3,000 records.
8. **Naukri contamination:** The 198-record Naukri cohort must not enter the main benchmark or be mixed with Stripe/Stage 4F metrics.
9. **Existing evaluation assumptions:** `src.evaluation.runner.run()` requires reviewed `authorization_label`, `partition`, and `vacancy_group`; the proposed CSV does not provide a valid frozen benchmark.
10. **Privacy/raw retention:** SQLite stores raw content blobs for poster/source records; any future batch import needs an explicit retention and access decision.
''',
'proposed_integration_plan.md':'''# Proposed safe integration plan

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
''',
'integration_readiness_report.md':'''# Integration readiness report

## What works

- The application launches as a Streamlit evidence-review interface.
- Pasted text, public URL, and poster-image input paths exist.
- Public URL safety checks and bounded retrieval are implemented.
- HTML/JSON-LD/meta extraction exists.
- Evidence ledger, field comparison, unresolved handling, and retrieval warnings exist.
- Naive and lineage-aware aggregation are both displayed.
- Existing tests and schemas cover the current application workflow.

## What is missing

- No loader for the final research CSV package.
- No cohort selector or separate Naukri data boundary in the UI.
- No full representation of source-family/source-instance/retrieval-event identity.
- No explicit freshness, response-hash, official-employer URL, or canonical-vacancy display in the application schema.
- No separate persisted employer-identity and vacancy-authorization evidence model for imported package rows.
- No confirmed-lineage workflow tied to the Stage 4F/Stripe candidate worksheets.
- No valid frozen human-ground-truth benchmark; Stage 5B reviewer labels and lineage decisions were inspected as blank.
- No application-level batch import or approximately-3,000-record integration test.

## Safety decision

**CONDITIONAL GO for a read-only staging adapter and schema test only.**

**NO-GO for automatic dataset replacement, production integration, supervised evaluation, or merging Naukri.**

## Recommended tests before integration

- Schema and allowed-value validation, including explicit missingness.
- 780-record Stripe import dry run with zero writes to the current database.
- Stage 4F import dry run with employer/source-family counts preserved.
- Naukri exclusion test proving it cannot enter the main cohort query.
- Stable-ID and URL/job-identifier duplicate tests.
- Evidence-state test proving unavailable/unresolved are never converted into fraud.
- Source-independence test proving same-ATS retrieval is not independent authorization.
- Lineage test proving candidates remain candidates until adjudication.
- Group-aware split leakage test.
- Poster/PDF fixture tests preserving input type and provenance.
- Existing regression suite run in a disposable environment.

No existing application file was modified during this review. The exact modifications listed in `proposed_integration_plan.md` should be approved separately before implementation.
'''
}
OUT.mkdir(parents=True,exist_ok=True)
for name,text in docs.items():(OUT/name).write_text(text,encoding='utf-8')
print('created',len(docs),'reports in',OUT)
