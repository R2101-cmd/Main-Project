# TrustHire Professional Assessment UI Cleanup

## Latest redesign pass

The assessment screen is now a compact, applicant-facing SaaS-style experience. Poster users see a structured extracted-details preview and can expand **Edit extracted details**; raw OCR is not shown in the default flow. The assessment view presents one prominent status card, three separate status values, icon-led vacancy information cards, and only meaningful evidence summaries. Technical material remains under one collapsed **Advanced diagnostics** expander.

## Scope

Presentation-only cleanup. Evidence collection, authority configuration, lineage aggregation, decision policy, fraud logic, OCR algorithms, datasets, annotations, labels, benchmark files, and research methodology were not changed.

## Files modified in this cleanup

- `app.py`
- `artifacts/ui_cleanup_report.md`

## Before and after

### Assessment result

Before: the page showed a large decision block, repeated metrics, separate public-signal and lineage-signal cards, duplicated warnings, source counters, and charts.

After: one assessment result block presents the overall status, employer identity, vacancy authorization, fraud outcome, and one plain-language explanation. Unresolved is explicitly described as insufficient evidence, never as fraud.

### OCR and extracted details

Before: OCR text and technical extraction information could remain visible alongside repeated field views.

After: one structured extracted-details preview appears before poster assessment, with corrections available under **Edit extracted details**. After submission, the user sees a concise vacancy-details summary. Raw OCR and diagnostics remain available only in Advanced diagnostics.

### Evidence and research details

Before: evidence ledger, source comparison, aggregation state, charts, counters, and technical details were visible in the main assessment layout, including empty sections.

After: only meaningful evidence findings are shown in the main view. Evidence ledger, source comparison, lineage aggregation, OCR diagnostics, retrieval details, and extraction details are kept under one collapsed Advanced diagnostics section. Empty tables and empty comparison sections are omitted.

## Input-mode verification descriptions

- Pasted text: clean vacancy input form; assessment result shows the three separate statuses and unresolved explanation when evidence is insufficient.
- Public URL: same streamlined assessment layout; retrieval failures are expressed as an incomplete check rather than contradiction or fraud.
- Poster image: extraction step shows structured extracted-details cards and an optional edit form; after correction and assessment, only the concise vacancy summary is shown by default, with diagnostics available on demand.

## Regression results

- Streamlit smoke test: passed.
- Pasted-text workflow: passed without exception.
- Public URL mode: rendered successfully.
- Poster mode: rendered successfully.
- Assessment output: contains employer identity, vacancy authorization, and fraud outcome separately.
- Content check: no raw OCR, Tesseract path, PSM, confidence, retrieval counters, or old signal cards visible in the default pasted-text assessment view.
- Full automated suite: **166 passed, 7 warnings**.

## Integrity confirmation

No datasets, annotations, ground-truth labels, benchmark files, evidence collection code, authority configuration, lineage aggregation, decision policy, or OCR extraction implementation were modified in this UI cleanup.
