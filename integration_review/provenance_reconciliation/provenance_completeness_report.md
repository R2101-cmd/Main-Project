# Stripe provenance completeness report

## Result

- Input records: **780**.
- Exact case-ID matches to Table A and Stage 4E: **780**.
- Complete core provenance using recovered plus derived-package fields: **0**.
- Partial provenance: **780**.
- No recoverable provenance: **0**.
- Strict historical complete provenance excluding derived source-instance/canonical fields: **0**.
- Unmatched records: **0**.
- Ambiguous matches: **0**.

## Interpretation

The original Stripe staging preview has only the 12 advertisement columns. Stage 4E recovers official URL, Greenhouse URL/job identifier, retrieval timestamp, response hash, updated date where present, evidence state, and source-independence values by exact `case_id`. The final package supplies `source_family_id`, `source_instance_id`, and `canonical_vacancy_id`, but these are derived package fields rather than original retrieval-event records. No `retrieval_event_id` exists in the inspected historical artifacts.

Therefore the cohort is not fully historically provenance-complete. The derived fields are clearly marked in `recovered_field_sources.csv` and must not be presented as independently captured event identifiers.

## Field completeness

- `case_id`: 780 present, 0 missing; sources: none
- `cohort_id`: 780 present, 0 missing; sources: final_research_package/cohort_manifest.json:main_integration_cohorts; final_research_package/unified_proposed_dataset.csv:cohort_id
- `employer_id`: 780 present, 0 missing; sources: processed/table_A_advertisements.csv:employer_id
- `source_family_id`: 780 present, 0 missing; sources: final_research_package/unified_proposed_dataset.csv:source_family_id
- `source_instance_id`: 780 present, 0 missing; sources: final_research_package/unified_proposed_dataset.csv:source_instance_id
- `retrieval_event_id`: 0 present, 780 missing; sources: none
- `source_url`: 780 present, 0 missing; sources: staging_test/stripe_staging_preview.csv:advertisement_url/application_url; processed/table_A_advertisements.csv:same case_id
- `official_employer_url`: 780 present, 0 missing; sources: processed/stage4e_evidence_records.csv:official_employer_url
- `canonical_vacancy_id`: 780 present, 0 missing; sources: final_research_package/unified_proposed_dataset.csv:canonical_vacancy_id
- `retrieved_at`: 780 present, 0 missing; sources: processed/stage4e_evidence_records.csv:retrieval_timestamp
- `updated_at`: 763 present, 17 missing; sources: processed/stage4e_evidence_records.csv:updated_date
- `response_hash`: 780 present, 0 missing; sources: processed/stage4e_evidence_records.csv:greenhouse_response_hash
- `evidence_state`: 780 present, 0 missing; sources: processed/stage4e_evidence_records.csv:evidence_classification
- `source_independence`: 780 present, 0 missing; sources: processed/stage4e_evidence_records.csv:source_independence
- `lineage_candidate_id`: 192 present, 588 missing; sources: processed/stage5b_lineage_pair_review.csv:pair_id
- `confirmed_lineage_id`: 0 present, 780 missing; sources: none

## Lineage and semantics

Stage 5B pair IDs were recovered only as candidate lineage references. Confirmed lineage IDs recovered: 0. No description-only matching was used for provenance joins. Same-ATS retrieval was not converted into independent authorization. No labels were generated, and no missing or unavailable evidence was converted into contradiction.

## Files and integrity

The reconciliation preserves all original staging-preview columns and appends reconciliation fields. Original datasets, application files, SQLite, and historical outputs were not modified. No scraping or database write occurred.

## Recommendation

**CONDITIONAL — not ready for a future database integration test that requires complete historical provenance.** A read-only schema test may proceed, but an integration test should either allow explicit missing `retrieval_event_id` and derived-field provenance or first establish an auditable retrieval-event registry.
