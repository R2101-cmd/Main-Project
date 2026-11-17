# Phase 2 Test Report

**Date:** 2026-11-14  
**Scope:** Phase 2 official-source verification improvements (`src/evidence/collector.py`, `src/ingestion/content_extractor.py`) and related regression coverage.

## Tests added (Phase 2)
`tests/test_phase2_verification.py`:
- exact job ID match (authoritative source)
- wrong job ID conflict
- similar job titles without strong identity (title similarity alone not sufficient for support)
- different locations recorded in field comparison
- employer mismatch prevents support
- description similarity captured
- third-party source not authoritative
- verified ATS relationship can support (authorized domain)
- unverified ATS relationship not authoritative
- snapshot-only match distinct from independent evidence
- independent official evidence preserves provenance
- missing evidence recorded as inaccessible/unavailable (not fraud)
- inaccessible official website recorded
- contradictory evidence on authoritative source

## Targeted regression tests
- `tests/test_evidence_collection.py`: **9 passed** (backward-compatible behaviors preserved)
- `tests/test_extraction.py`, `tests/test_core.py`, `tests/test_ui_support.py`: included in full suite (passed)

## Full test suite
- Command: `python -m pytest -q`
- Result: **87 passed, 2 warnings in 2.81s** (exit code 0)
- Warnings: existing sklearn confusion-matrix warning in `tests/test_runner.py` (unrelated to Phase 2 changes)
- Log: `pytest_full.txt`

## Data protection verification
- Protected checksums recorded before/after: `protected_checksums_before.csv`, `protected_checksums_after.csv`
- Comparison result: **UNCHANGED** for all listed protected datasets/artifacts
- No original datasets, historical annotations, or previous Stage 4 outputs modified; no fabricated evidence/labels created.
