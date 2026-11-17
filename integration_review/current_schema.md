# Current application schema

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
