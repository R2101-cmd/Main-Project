# TrustHire proposed unified schema

The unified dataset is a proposed integration artifact, not an approved replacement. Empty values mean unavailable, not false. Naukri remains separate.

| Field | Meaning | Allowed/notes |
|---|---|---|
| cohort_id | Source cohort identity | `stripe_greenhouse_780` or `stage4f_expansion_2200` |
| case_id | Original advertisement record ID | Must be unique within cohort |
| employer_id / employer_name | Employer identity fields | Identity is not authorization |
| job_title / job_description / location | Advertised content | Preserve source values |
| original_source_url | Observed source URL | Public URL if available |
| source_family_id / source_instance_id | Source family and employer board instance | Different URLs do not prove independence |
| retrieval_timestamp / http_status / response_hash | Retrieval provenance | Preserve missingness |
| canonical_vacancy_id | Source-normalized vacancy identity | Not a human lineage decision |
| vacancy_status_observation | Listing observation | Active/removed/etc.; not fraud |
| evidence_state | Evidence classification | Snapshot/fresh/independent/unresolved as available |
| source_independence_status | Independence of source | Separate from retrieval independence |
| lineage_group_id | Human-confirmed lineage group | Blank until adjudicated |
| confirmed_lineage_status | Confirmed lineage state | Not confirmed in current package |
| employer_identity_label / vacancy_authorization_label / fraud_outcome_label | Human ground truth | Blank/unresolved until adjudicated |
| adjudication_status | Review state | `unreviewed`, `not_started`, or adjudicated value |
