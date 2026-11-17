# Automated Validation Mode Report
**Date:** 2026-11-14  
**Mode:** Automated evidence collection, automated source/lineage analysis, uncertainty-aware decision-making (no manual case-by-case human review required for execution)

## 1. Research objective preserved
- Title: *Beyond Fake-Job Classification: Lineage-Aware Evidence for Vacancy Authorization Verification*.
- Focus remains vacancy authorization verification (not generic fake-job classification).
- Separate outputs retained:
  - **Employer identity:** verified / contradicted / unresolved
  - **Vacancy authorization:** supported / contradicted / unresolved
  - **Fraud outcome:** confirmed_fraudulent / confirmed_legitimate / unresolved
- **Rule:** Missing or unavailable evidence never automatically implies fraud.

## 2. Manual review dependency removed from execution (artifacts preserved)
- Normal automated pipeline/execution does not require manual review or adjudication.
- Historical human-review worksheets and annotation files preserved as research artifacts (not deleted, not overwritten), e.g. `final_completion_package/05_annotations/worksheets/*`, `DatasetCollection/processed/stage5b_*`, `data/annotations/*`.
- No artificial human annotations generated; no automated decisions presented as human ground truth.

## 3. Automated official-source verification pipeline
- Implemented capability (code): public-source retrieval and evidence comparison via `src/ingestion/url_fetcher.py` and `src/evidence/collector.py` (permitted public sources only; no CAPTCHA/auth bypass, no unsafe redirects/private targets).
- Automated state mapping applied to collected artifacts (780 Stage 4E records): `independently_supported`, `independently_contradicted`, `independently_unresolved`, `inaccessible`, `not_comparable`, `snapshot_match_only` with provenance/timestamps/status where available.
- Results (artifact-based, conservative): `snapshot_match_only=763`, `independently_unresolved=16`, `inaccessible=1`, `independently_supported=0`, `independently_contradicted=0`.
- Missing listings treated as unresolved/inaccessible evidence, **not** proof of fraud.
- Outputs: `final_completion_package/03_stage4_verification/*`, `final_completion_package/automated_mode/descriptive_real_data_analysis.json`.

## 4. Automated lineage detection (all 687 candidates processed)
- Processed: **21 original + 459 Stage 4F + 207 Stripe pairs = 687**.
- Methods: automated scoring from existing similarity/signal/metadata fields (URL/identifier cues, title/description/location similarity, source/publication context where present). Implemented conservative categorization:
  - **Confirmed by direct machine-verifiable provenance:** 0 (none evidenced in candidate records)
  - **Likely dependent:** 430
  - **Possible dependency:** 153
  - **Unknown relationship:** 104
- **Policy:** similarity-based relationships are **not** confirmed lineage; unknown relationships are **not** assumed independent. Independent source families estimated conservatively (see summary).
- Outputs: `final_completion_package/automated_mode/automated_lineage_analysis.csv`, `automated_lineage_summary.json`.

## 5. Three-way evaluation
- Preserved approaches: **A. Text-only**, **B. Ordinary evidence aggregation**, **C. Lineage-aware evidence aggregation** (identical records/consistent rules).
- Original synthetic benchmark preserved unchanged: `research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl` (60 records). Prior controlled run results retained in `final_completion_package/06_stage6_evaluation/`.
- **Extended synthetic benchmark (separately versioned, all synthetic/labeled, not human-reviewed):** `research-data/phase2_v1/synthetic/synthetic_benchmark_extended_v1.jsonl` (+ manifest), 30 records covering copied/dependent evidence, contradictory evidence, unavailable sources, unknown lineage, and independent support.
- Extended controlled three-way run: `final_completion_package/automated_mode/extended_synthetic_three_way/` (metrics, confusion matrices, per-case predictions). **Synthetic labels are not real-world ground truth.**

## 6. Real-world descriptive analysis (no ground-truth performance metrics)
- Reported descriptive system outputs only (not accuracy/precision/recall/F1/false assurance vs ground truth): retrieval success rate proxies, official-source match rate proxies, evidence availability rate, snapshot-only match rate, contradiction evidence count, unresolved/inaccessible rates, duplicate evidence rate (URL proxy), candidate lineage rate/involvement, automated state/decision distributions, abstention rate, conservative evidence-independence estimates.
- Outputs: `final_completion_package/automated_mode/descriptive_real_data_analysis.json`, `descriptive_metrics.csv`.
- All labeled as **descriptive machine-generated outputs, not ground-truth performance metrics**.

## 7. Application integration
- Streamlit app (`app.py`) updated to clearly label outputs as **automated, machine-generated evidence assessments (not independently adjudicated conclusions)**.
- Supports pasted advertisement, public URL, and poster image (existing OCR capability when available), automated evidence retrieval/ledger, three aggregation approaches in a controlled synthetic research-comparison demo, and separate identity/authorization/fraud outcome presentation with unresolved-decision explanation.
- Smoke test passed: `final_completion_package/07_application/streamlit_smoke_test.json`.

## 8. Testing
- Automated suite: **73 passed, 2 warnings** (`pytest -q`), including `tests/test_automated_mode.py` covering missing/unavailable evidence, contradictions, duplicates/copied/dependent consolidation, unknown lineage, independent sources, unsafe URLs, abstention/invalid handling aspects, and checks that automated lineage outputs contain no fabricated human labels/confirmation and that extended synthetic data is labeled/separate.
- No human annotations fabricated.

## 9. Limitations / claims
- **Engineering/prototype/synthetic experiment/descriptive automated analysis:** completed to the extent technically executable in this mode.
- **Real-world ground-truth evaluation unavailable:** no adjudicated labels/confirmed lineage; do not claim hypothesis proven or human-verified lineage/authorization.
- Live retrieval results depend on public source availability/network access and site policies; inaccessible/missing sources remain unresolved, not fraud.
