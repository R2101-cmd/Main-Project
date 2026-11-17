# Stripe staging validation report

Status: **CONDITIONAL PASS**

## Input identification

Selected from the manifest-listed package by actual contents: `stripe_cohort.csv`. It contains 780 rows, all Stripe case IDs, and employer ID set `['EMP_STRIPE']`. The preview preserves all 780 rows and all 12 original columns.

## Checks

| Check | Status | Result |
|---|---|---|
| record_count | PASS | {"status": "PASS", "expected": 780, "actual": 780} |
| unique_case_ids | PASS | {"status": "PASS", "unique": 780, "duplicates": 0} |
| cohort_identity | PASS | {"status": "PASS", "case_id_prefixes": {"GREENHOUSE": 780}, "employer_ids": {"EMP_STRIPE": 780}, "unexpected_stage4f": 0, "unexpected_naukri": 0} |
| duplicate_urls | PASS | {"status": "PASS", "populated": 780, "duplicates": 0} |
| vacancy_identifiers | PASS | {"status": "PASS", "field_present": false, "duplicates": "not assessed because no proposed job_identifier field is present"} |
| urls | PASS | {"status": "PASS", "invalid": 0} |
| timestamps | PASS | {"status": "PASS", "invalid_observed_at": 0, "missing_observed_at": 0, "missing_update_date": 780} |
| provenance | CONDITIONAL | {"status": "CONDITIONAL", "complete_records": 0, "total_records": 780, "missing_fields": {"cohort_id": 780, "employer_name": 780, "original_source_url": 780, "official_employer_url": 780, "ats_platform": 780, "source_family_id": 780, "source_instance_id": 780, "retrieval_timestamp": 780, "http_status": 780, "response_hash": 780, "job_identifier": 780, "canonical_vacancy_id": 780, "vacancy_status_observation": 780, "evidence_state": 780, "employer_identity_state": 780, "vacancy_authorization_stat |
| allowed_values | PASS_OR_NOT_APPLICABLE | {"status": "PASS_OR_NOT_APPLICABLE", "invalid": {}, "absent_allowed_fields": ["evidence_state", "employer_identity_state", "vacancy_authorization_state", "confirmed_lineage_status", "fraud_outcome_label"]} |
| research_semantics | PASS | {"status": "PASS", "unavailable_preserved": "not applicable; field absent", "unresolved_preserved": "not applicable; field absent", "unverified_preserved": "not applicable; field absent", "candidate_lineage_confirmations": 0, "same_ats_independent_authorization_generated": 0, "active_to_legitimate_labels_generated": 0, "fraud_or_authorization_labels_generated": 0, "missing_to_contradiction_conversions": 0} |
| duplicates_and_lineage | PASS_WITH_WARNINGS | {"status": "PASS_WITH_WARNINGS", "exact_description_duplicate_records": 61, "near_duplicate_candidate_pairs": 186, "records_deleted": 0, "confirmed_lineage_edges_created": 0, "interpretation": "Similarity candidates are reported only; no records or lineage decisions were changed."} |

## Completeness and provenance

The selected source is the original 12-column Stripe cohort copy. The proposed provenance/evidence fields are not present in this file, so they remain missing; no values were copied from Stage 4F, Naukri, or another evidence table. Missing update dates, response hashes, retrieval-event identifiers, source-instance identifiers, evidence states, and labels are reported as missing rather than fabricated.

## Duplicate and lineage findings

Duplicate IDs and populated URLs were checked. Exact and near-duplicate descriptions are reported without deleting records. Candidate similarity was not converted into confirmed lineage.

## Semantic safeguards

No fraud, authorization, employer-identity, or confirmed-lineage labels were generated. Unavailable, unresolved, and unverified states were not changed; these fields are absent from the selected source and therefore remain missing. Active/listed observations were not treated as legitimacy.

## Errors and warnings

Errors: none

Warnings: provenance, allowed_values, duplicates_and_lineage

## Integrity

Input and preview semantic fingerprints match: `True`. SQLite was not opened. No scraping or collection was performed. Original application files, datasets, database, and historical outputs were not modified.
