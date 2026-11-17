# Test and validation results

## Commands

| Command | Exit | Result |
|---|---:|---|
| `python -m pytest tests\test_url_fetcher.py tests\test_extraction.py tests\test_evidence_collection.py tests\test_phase2_verification.py tests\test_live_reliability.py tests\test_core.py tests\test_aggregation_verification.py tests\test_ui_support.py -q` | 0 | 107 passed, 2.33 seconds |
| `python -m pytest -q` | 0 | 163 passed, 7 warnings, 14.59 seconds (final run) |
| `python scripts\smoke_test_streamlit.py` | 0 | All input modes rendered; pasted-text result workflow completed; no exception |
| `python scripts\create_synthetic_benchmark_v2_split.py --validate` | 0 | Existing split validated; no split files regenerated |
| `python scripts\validate_staging_package.py integration_review\schema_test\disposable_staging_import.csv --cohort stripe_greenhouse_780` | 0 | 780 rows loaded read-only; counts below |

The full suite’s 7 warnings were: 2 scikit-learn warnings for a test fixture containing a single class, and 5 SciPy/L-BFGS deprecation warnings emitted by synthetic evaluation regression tests. No test failed in the final run.

The first expanded smoke-test attempt used an unsupported `AppTest.file_uploader` attribute and exited 1. The smoke script was corrected to use the supported `AppTest.get("file_uploader")` API; the final rerun exited 0.

## Staging classifications

- Input and loaded: 780.
- Evidence states: 744 `snapshot_match_only`, 19 `unverified`, 16 `unresolved`, 1 `unavailable`.
- Lineage: 192 candidate rows; 0 confirmed rows.
- Read-only: true; supervised labels assigned: false.

## Smoke-test behavior

The AppTest run rendered Pasted text, Public URL and Poster image modes. It submitted pasted text with no network source and returned Employer identity `Unresolved`, Vacancy authorization `Unresolved`, Fraud outcome `Unresolved`, as expected for a case without source evidence. The only runtime warning was Streamlit’s standard missing ScriptRunContext warning in bare AppTest mode.

## Scope note

The full suite includes synthetic evaluation compatibility and reproducibility tests. The historical `final_completion_package/synthetic_evaluation_v2/` Stage 7B experiment was not rerun, retuned or rewritten.
