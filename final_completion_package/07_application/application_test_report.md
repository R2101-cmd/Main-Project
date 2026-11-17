# Application test report

**Date:** 2026-11-14

## Automated tests executed
- Command: `python -m pytest -q`
- Result: **65 passed, 2 warnings** (sklearn confusion-matrix warning in `tests/test_runner.py` exploratory pilot case; warnings not test failures).
- Coverage relevant to app/research components (existing suite): ingestion/content/image/URL fetcher, evidence collection, aggregation/decision/core, dataset import, database, metrics/runner, collection readiness, UI support.

## Application smoke checks
- Static/functional confidence from existing passing tests covering extraction, evidence collection, UI support, URL fetcher safety behavior, and evaluation/metrics logic.
- Interactive Streamlit runtime (`streamlit run app.py`) not executed in this non-interactive audit pass; no UI regression screenshots captured.

## Targeted scenario status (requested)
| Scenario | Status | Evidence/notes |
|---|---|---|
| Pasted text | Covered by existing tests/logic | Extraction + evidence flow supported in app/tests |
| Valid public URL | Partially covered | Fetch/extract/evidence logic tested; live network not re-run here |
| Invalid URL | Covered in existing safety/fetcher tests | Unsafe/invalid handling present |
| Inaccessible URL | Covered in logic/tests patterns | Recorded as retrieval failure/unavailable, not fraud |
| Missing employer/title | Covered conceptually | Extraction warnings/unresolved handling; human review required |
| Conflicting official evidence | Logic present | Contradiction states supported; no adjudicated live case executed |
| Duplicate/dependent sources | Partially covered | Aggregation/lineage logic exists; confirmed lineage unavailable |
| Unavailable/insufficient evidence | Covered | Abstention/unresolved pathways implemented |
| Unresolved decisions | Covered | Decision policy/UI/reporting emphasize unresolved |

## Failures/blockers
- No new application integration tests added for proposed 2,980-record staging loader (not implemented).
- End-to-end live-source verification not executed in this pass.
