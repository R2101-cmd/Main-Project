# Supported-record reconciliation audit

Generated: `2026-11-14T05:30:25.594249+00:00`  
Records crosswalked: **780**

## Finding

The **744 supported** result was calculated from `integration_review\schema_test\disposable_staging_import.csv` using its `evidence_state` column. The 744 source values are `independent_official_confirmation`. The new staging loader maps that source-specific value to the generic application evidence state `supported`.

That mapping is an evidence-state normalization. It does **not** establish independent official authorization, and it does not change `verification_status` to `independently_supported`.

## Counts by layer

| Layer | Counts |
|---|---|
| Stage 4E raw evidence classification | `{'independent_official_confirmation': 744, 'fresh_same_system_retrieval': 19, 'unresolved': 16, 'unavailable': 1}` |
| New staging normalized evidence state | `{'supported': 744, 'unverified': 19, 'unresolved': 16, 'unavailable': 1}` |
| Phase 2 artifact verification status | `{'snapshot_match_only': 763, 'inaccessible': 17}` |
| Historical Stage 4 verification state | `{'independently_unresolved': 780}` |
| Lineage status | `{'none': 588, 'candidate': 192}` |

The Stage 4E quality artifact reports 744 `independent_official_confirmation`, 19 `fresh_same_system_retrieval`, 16 `unresolved`, and 1 `unavailable`. Those become 744 `supported`, 19 `unverified`, 16 `unresolved`, and 1 `unavailable` in the staging loader. The 763/16/1 snapshot summary is not the same field: the prior Phase 2 authority artifact contains 763 `snapshot_match_only` and 17 `inaccessible`; the historical Stage 4 verification CSV contains 780 `independently_unresolved`.

## Answers to the audit questions

1. The exact input is `integration_review\schema_test\disposable_staging_import.csv`, field `evidence_state`; the 744 raw values are `independent_official_confirmation`.
2. `supported` means the staging evidence-state vocabulary after normalization. It is not a supervised vacancy-authorization label.
3. It represents collected/source evidence classification, not structural validation alone and not independent official authorization. Snapshot context and authority limitations remain in the other artifacts; this loader does not promote verification status.
4. The complete 780-row mapping is in `supported_record_reconciliation.csv`.
5. No record was promoted from snapshot-only to `independently_supported`; the crosswalk marks all 780 promotion flags `no`.
6. No unavailable, unverified, or snapshot-only evidence was silently promoted to independent authorization. The 19 `fresh_same_system_retrieval` rows remain `unverified`, and the 1 unavailable row remains `unavailable`.
7. The 192 lineage candidates remain `lineage_status=candidate`; confirmed lineage count is 0. No candidate was treated as confirmed.
8. Original datasets and historical outputs were not modified.

## Source checksums

- `DatasetCollection/processed/stage4e_evidence_records.csv` — original Stage 4E evidence artifact; SHA-256 `a0a78bccdb7358a928812311ebd144e2b401ecd7407d09c89fd875ca07d25676`.
- `integration_review/schema_test/disposable_staging_import.csv` — exact input used by the staging CLI; SHA-256 `4461839cde8472c97cd0287ebb51242112c7de8243315d6fa29e2e446b7c4b74`.
- `final_completion_package/phase2_verification_improvement/source_authority_analysis.csv` — prior Phase 2 artifact-level verification classification; SHA-256 `3110652ef947d60e30ca4db01dfdb4f1c9b81ecf27753865dbf89c2d0a5c0451`.
- `final_completion_package/03_stage4_verification/verification_results.csv` — historical verification output; SHA-256 `0664e8c668bff09ca8118a1709d6668769b1e6c9f27bb3e4696c6bc7baecce43`.

The audit output itself is new and versioned under `final_completion_package/phase2_verification_improvement/reconciliation_audit/`.
