# Evidence Integration Correction Report

## Files modified

- `src/evidence/representation.py` — explicit conservative collection-to-live conversion layer.
- `src/datasets/staging.py` — uses the explicit mapping and exposes a non-promoting live conversion alongside preserved raw data.
- `src/ingestion/content_extractor.py` — structured ATS JSON normalization.
- `tests/test_evidence_integration_correction.py` — regression coverage for mapping, Greenhouse extraction, lineage, authority, freshness, and policy behavior.
- `docs/evidence_representation_mapping.md` — documented conversion rules.

No dataset, annotation, label, authority mapping, benchmark, or evaluation-result file was changed.

## Evidence mapping before and after

Before, collection vocabularies such as `independent_official_confirmation` existed in staging helpers but did not have one explicit live conversion boundary.

After:

- `independent_official_confirmation` maps to `snapshot_match_only`.
- `fresh_same_system_retrieval` maps to `unverified`.
- Collection classifications and timestamps are preserved in conversion details.
- Unknown lineage remains `source_relationship=unknown` and `lineage_review_status=not_assessed`.
- No adjudicated lineage is manufactured.
- No authority mapping is manufactured.
- Current support requires explicit current authorization, verified authority, and adjudicated independent lineage.

## Greenhouse extraction before and after

Before, the Greenhouse JSON response was treated as plain text and did not populate comparable fields reliably.

After, structured ATS JSON extracts:

- Stable ATS job ID
- Title
- Employer
- Location
- Description/content
- Posting date
- Modification date
- Application URL
- Optional employment and salary fields when present

Missing fields remain `None`. Retrieval time remains separate from source publication/modification time.

## Stripe replay

Case: `CASE_GREENHOUSE_STRIPE_8190059`

After the correction:

- Stripe page vacancy correspondence: `true`
- Greenhouse API vacancy correspondence: `true`
- Stripe freshness: `current`
- Greenhouse freshness: `current`
- Greenhouse job ID: `8190059`
- Qualifying independent source groups: `0`
- Ordinary aggregation: `unresolved`
- Lineage-aware aggregation: `unresolved`
- Final live decision: `unresolved`, abstain
- Fraud outcome: `unresolved`

The final decision did not change. It remains unresolved because authority mappings are empty, both source relationships remain unknown/not adjudicated, and the two-source policy is intentionally preserved. The correction fixes evidence correspondence and ATS field extraction without weakening authorization safeguards.

## Regression results

- Focused correction tests: **71 passed**.
- Full test suite: **175 passed, 7 warnings**.
- Python compilation: passed.
- Streamlit pasted-text, URL, and poster smoke workflows: passed.
- Protected hash manifest: unchanged.

## Accuracy and research interpretation

No real-world accuracy claim was made. This change only improves evidence representation and Greenhouse field extraction. Independent adjudicated real-world evaluation remains necessary before reporting accuracy or improved authorization performance.
