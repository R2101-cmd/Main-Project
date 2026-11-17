# Application integration report

**Date:** 2026-11-14

## Current state (inspected)
- **Identity preserved:** `app.py` implements “TrustHire — Authorization Evidence Workspace” with tagline intent aligned to “Verify the vacancy, not just the employer.”
- **Inputs:** pasted text, public URL, poster image upload (OCR path present; depends on OCR deps/engine availability).
- **Processing present:** input validation, safe public URL fetch (`src/ingestion/url_fetcher.py`), extraction (`content_extractor.py`, `image_extractor.py`), evidence collection/comparison (`src/evidence/collector.py`), naive vs lineage-aware aggregation display (`src/aggregation/rules.py`, UI support), decision/abstention (`src/decision/policy.py`), SQLite repository/storage hooks.
- **Outputs/UI:** extracted fields, warnings/retrieval notes, evidence ledger and field comparison, source states/availability, naive vs lineage-aware summaries, unresolved/abstention messaging, conservative framing (no automatic fraud from missing evidence). Employer identity intentionally unresolved in current workflow unless source-domain relationship supported.

## Integration gaps (not fully completed in this pass)
- No batch loader/UI integration for `DatasetCollection/final_research_package/unified_proposed_dataset.csv` or staging schema adapter.
- No end-to-end connection to adjudicated human labels/confirmed lineage (none available).
- No separate research-mode dataset selector hardened for cohort boundaries in UI (Naukri separation must be enforced at data-loading level).
- Poster/PDF/OCR and full research comparison across all stored cases not exhaustively validated beyond existing tests.

## Security/behavior constraints preserved
- Public-source, best-effort retrieval; unavailable/inaccessible evidence handled as unresolved/unavailable (not fraud). Existing safety checks in fetcher retained; no bypass behavior added.

## Recommendation
Use application as a **demonstration/prototype evidence workspace** on permitted inputs; do not claim integrated, adjudicated-benchmark-driven production/research evaluation until dataset adapter, cohort filters, and human-confirmed labels/lineage are implemented and tested.
