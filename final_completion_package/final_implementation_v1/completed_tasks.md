# Completed tasks and verification map

| Requirement | Implementation | Evidence |
|---|---|---|
| Verified official-source mappings connected to live collection | `src/evidence/authority_config.py`, `config/employer_sources_v1.json`, `schemas/employer_sources_v1.schema.json`, `app.py`, `src/evidence/collector.py` | `tests/test_live_reliability.py`; `tests/test_phase2_verification.py` |
| No hostname-only or arbitrary user-supplied authority | Explicit verified relationship/provenance; ATS tenant path required | Authority loader and ATS tests; hostname resemblance regression |
| Separate employer identity and vacancy authorization | Collector explanation fields and distinct app metrics; final policy gates vacancy authorization separately | Phase 2 and decision policy tests; Streamlit smoke |
| Live lineage metadata, candidate-only similarity | `src/evidence/collector.py` | Live lineage regression; prior aggregation verification suite |
| Preserve ordinary and lineage-aware aggregation definitions | `src/aggregation/rules.py` was not edited in this implementation | `tests/test_aggregation_verification.py`, `tests/test_automated_mode.py`, full suite |
| Field comparisons affect final evidence status | `src/evidence/collector.py`, `src/ui_support.py` | Phase 2 and live reliability tests |
| Separate posting, modification, validity and retrieval dates | `src/ingestion/content_extractor.py`, `src/evidence/collector.py` | Extraction and stale/future/invalid/missing date regressions |
| Conservative final decision and unresolved conflicts | `src/decision/policy.py`, `app.py` | Decision policy regressions; conflicting aggregation regression |
| No fraud inference from authorization status | `src/decision/policy.py`, `app.py` | Tests assert fraud outcome remains unresolved |
| Remove synthetic reference-label selector from user UI | `app.py` | AppTest smoke asserts no selector and exercises result workflow |
| Public retrieval hardening | `src/ingestion/url_fetcher.py` | URL edge case, redirect and pinned-IP tests |
| Preserve protected research artifacts | Baseline and final hashes in this directory | `integrity_comparison.csv`: all 69 protected files unchanged |
| Record broader historical/raw-file status | Current-only supplemental hash inventories | Five synthetic artifacts and 3,841 raw scraper files have no pre-implementation hashes in the repository; see `data_integrity_report.md` |
| Document historical metrics without reusing them as current results | `research_methodology_consistency.md` | Stage 7B package hash preservation; no Stage 7B rerun |
