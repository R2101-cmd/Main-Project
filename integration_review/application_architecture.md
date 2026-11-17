# TrustHire application architecture review

Audit time: 2026-11-13T07:43:53.493660+00:00. Inspection only; no application files were changed.

## Current architecture

`app.py` is a Streamlit single-review workflow. It imports `Repository` and `DEFAULT_DATABASE`, but normal verification is held in Streamlit session state; the SQLite repository is used when a poster image is submitted to persist an advertisement and source record.

Input flow:

1. `_render_input_panel()` accepts pasted text, a public URL, or a poster image.
2. `_assess_input()` extracts fields with `src.ingestion.content_extractor.extract_text` or OCR, discovers explicit/specific public URLs, and calls `collect_vacancy_evidence`.
3. `naive()` and `lineage_aware()` create separate aggregate assessments.
4. `assess()` produces a conservative vacancy-authorization action.
5. `_render_assessment()` displays evidence, comparisons, availability, and unresolved warnings.

Relevant modules:

- `src/ingestion/content_extractor.py`: HTML/JSON-LD/meta extraction.
- `src/ingestion/url_fetcher.py`: public URL validation and retrieval.
- `src/evidence/collector.py`: evidence observations and field comparison.
- `src/aggregation/rules.py`: naive and lineage-aware aggregation.
- `src/decision/policy.py`: supported/contradicted/unresolved decision policy.
- `src/database/repository.py` and `src/database/schema.sql`: SQLite persistence.
- `src/lineage/similarity.py`: candidate similarity only.
- `src/evaluation/runner.py`: JSONL evaluation workflow requiring reviewed authorization labels and partitions.

No application-level loader for `final_research_package/unified_proposed_dataset.csv` was found. No Streamlit page for browsing the 2,980-record package was found. The existing application is therefore not a drop-in batch dataset viewer.

## Current behaviour that is safe

The UI preserves unavailable evidence as unresolved, explicitly warns that retrieval failure is not fraud, separates naive from lineage-aware aggregation, and states that a verified employer does not by itself authorize a vacancy. Poster input is already supported through OCR.

## Current behaviour that is incomplete for the final package

The workflow does not persist or display `cohort_id`, `source_family_id`, `source_instance_id`, response hashes, canonical vacancy IDs, evidence independence, publication/update dates, or the separate employer-identity/authorization/fraud labels from the proposed package. `lineage_aware()` only consolidates explicitly supplied lineage groups and the UI does not load candidate/confirmed lineage tables from CSV.
