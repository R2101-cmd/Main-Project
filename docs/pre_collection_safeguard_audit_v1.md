# Pre-collection safeguard adversarial audit v1

Audit date: 2026-10-22

Scope: collection-readiness configuration, annotation and evidence schemas, partition/freeze enforcement, evaluation metrics, tests, and the existing frozen baseline. No records were collected, no labels were generated, no research result was regenerated, and `artifacts/experiments/research_v1_frozen/` was not modified.

## Overall conclusion

The implementation is fail-closed for the real collection configuration: collection remains **NOT READY** because the dates, sampling seed, reviewer assignments, privacy/retention decisions, and operational approval are unset. The safeguards are **not sufficient to begin collection** until those human decisions are completed.

The software safeguards are substantially stronger after this audit. Two residual limits remain: reviewer blinding is a manual process rather than a repository-enforced security boundary, and the immutable v1 frozen result contains a legacy false-assurance denominator that does not match the corrected definition. The frozen result was deliberately not changed.

## Audit findings

| # | Audit question | Status | Finding and references |
|---:|---|---|---|
| 1 | Can missing/invalid dates, reviewer setup, privacy, retention, or authorization pass? | PASS | `src.collection_readiness.evaluate_config` requires all gates. `_check_reviewers`, `_check_privacy`, `_check_operational_authorization`, `_check_window`, and `_check_schema_versions` reject incomplete or invalid settings. The real template remains pending in `config/collection_config_v1.json`. |
| 2 | Are dates and timezone handling strict? | PASS | `_parse_timestamp` requires strict ISO 8601 with `T` and an explicit `Z` or offset. `_check_window` validates the IANA timezone with `ZoneInfo`, checks offset consistency, and requires exactly 30 elapsed days plus `duration_days == 30`. Tests cover malformed syntax, invalid timezone, and incorrect duration. |
| 3 | Can placeholder reviewer identities pass? | PASS | `_is_real_identity` requires non-placeholder strings; reviewer IDs must be distinct and at least two, and the adjudicator must be distinct. Placeholder IDs are blocked by `test_missing_reviewer_setup_prevents_readiness`. |
| 4 | Are original annotations immutable after adjudication? | PASS with process limitation | `schemas/adjudication_form_v1.schema.json` requires original IDs and fingerprints. `src.annotation.validation.validate_annotation_bundle` verifies fingerprints and detects later mutation. This protects the record relationship, but the repository does not provide an append-only storage service; the original files must still be access-controlled. |
| 5 | Can a tuner access test labels or test-level errors? | NOT VERIFIED | `src.evaluation.runner.run` necessarily reads reference labels to evaluate a supplied dataset, and `scripts/run_research_evaluation.py` writes test predictions and comparisons. The configuration contains a manual blinding procedure, but no technical role separation or access-control mechanism is implemented. The project must not claim that repository access restrictions guarantee blinding. |
| 6 | Can related vacancy/lineage groups cross partitions? | PASS with process limitation | `validate_evaluation_records` checks evidence lineage groups, `validate_split_manifest` checks manifest groups, and the runner includes `lineage_groups` in its current manifest. A reviewed lineage family must still be correctly identified by human reviewers; software cannot discover an omitted relationship. |
| 7 | Does freeze enforcement protect IDs, groups, and replacement? | PASS | `frozen_test_id_differences` compares added/removed test IDs, group changes, and partition changes. `runner.run` also requires the frozen sibling `aggregate_metrics.json` and matches its dataset fingerprint, preventing silent content replacement. Tests cover changed groups, changed data, and missing fingerprint metadata. |
| 8 | Are unavailable evidence and unresolved authorization separate? | PASS | `schemas/evidence_item_v1.schema.json` separates `retrieval_state` from `evidence_state`; `authorization_label` remains a separate field in evaluation records. An unavailable-only evidence item aggregates to `unresolved`, not `contradicted`, and the test suite verifies this. |
| 9 | Are false-assurance metrics correct for zero denominators/absent classes? | FAIL for the immutable v1 artifact; PASS for current code | `selective_metrics` now uses all eligible reference non-supported cases as the denominator, including abstentions, and handles zero denominators as `None`. The current frozen `aggregate_metrics.json` stores `false_assurance_denominator: 2`, which reflects the previous assessed-only definition; the corrected denominator for that test is 6. The frozen artifact is immutable and was not rewritten. A future confirmatory evaluation must use the corrected implementation. |
| 10 | Are E4 and E5 evaluated on identical eligible cases? | PASS | `runner.run` constructs both methods from the same `test` list and records `paired_e4_e5_same_eligible_cases: true`. `scripts/run_research_evaluation.py` generates both predictions in the same loop and records paired outcomes. |
| 11 | Do scripts alter the frozen baseline? | PASS | `verify_frozen_snapshot` only reads the manifest and files. Evaluation outputs are written to a caller-supplied output path; the readiness command writes `docs/collection_readiness_report.md` and `artifacts/readiness/`, not the frozen directory. The manifest hashes remained unchanged after the audit. |
| 12 | Do tests cover failure cases? | PASS | The suite covers unset and invalid dates, invalid timezone, wrong duration, malformed strata/configuration, missing reviewers, placeholder reviewers, missing privacy decisions, invalid approval time, unavailable evidence, annotation mutation, partition/group changes, frozen-ID replacement, missing fingerprints, zero denominators, and freeze integrity. |

## Validation performed

Full suite:

```powershell
python -m pytest -q
```

Result: **58 passed, 2 warnings**. The warnings are scikit-learn single-class metric warnings from the existing pilot test; they are not failures.

Readiness gate:

```powershell
python scripts\validate_collection_readiness.py
```

Result: expected exit code **1** and `collection_ready: false`. Pending requirements are the exact collection window, sampling seed, reviewer/adjudicator setup, privacy/retention approvals, and operational authorization.

Frozen baseline verification:

```powershell
python -c "import json; from src.collection_readiness import verify_frozen_snapshot; print(json.dumps(verify_frozen_snapshot('artifacts/experiments/research_v1_frozen'), indent=2))"
```

Result: **ready**. The manifest matched all four files:

- `aggregate_metrics.json`: `D795F32C665ACE281085C89B6F896D8F79AEB3F95D215BA761EB9CA9907023CD`
- `experiment_config.json`: `E2BA849AF66D52629F1214B11FBB3FC3414C7E6506247E767974484A1ECC6078`
- `predictions.jsonl`: `21C4A02E3D4266E11CC2D80FFF130708AE254E39D2B0E2493504F6364990EE14`
- `split_manifest.json`: `32D354091E3FC6ED9692CF175C3B3BD7C14EDF90ACA68835C02385CF17B785C7`

Frozen test and dataset check:

```powershell
python -m src.evaluation.runner --data data/annotations/job_ad_independent_review_v1.jsonl --frozen-test-manifest artifacts/experiments/research_v1_frozen/split_manifest.json --output artifacts/readiness/frozen_test_id_check.json
```

Result: successful. The current dataset fingerprint matched the frozen aggregate and no test IDs, groups, or partitions changed.

The invalid and incomplete configuration cases are isolated in `tests/test_collection_readiness.py` and `tests/test_runner.py`; they use in-memory or `tmp_path` fixtures and do not enter the research benchmark.

## Prioritized follow-up actions

1. **Before collection:** complete the real 30-day window, sampling seed, two reviewer IDs, separate adjudicator, privacy/redaction/snapshot/retention/access decisions, and named operational approval in a controlled review process. Do not use placeholders.
2. **Before confirmatory evaluation:** regenerate a new frozen evaluation set using the corrected false-assurance definition. Preserve the current v1 result as an immutable legacy snapshot; do not overwrite it.
3. **Before claiming independent annotation:** enforce reviewer access separation outside this codebase, retain original annotation files as append-only or version-controlled records, and document who could access model predictions and test errors.
4. **During collection:** require human review of candidate lineage relationships and record unknown when dependence or independence cannot be established.

## Final decision

The repository is **not collection-ready**. The validator correctly blocks collection until actual human and operational decisions are supplied. The software should not be described as providing technical blinding, independent annotation, statistical power, or evidence that lineage-aware aggregation improves verification.
