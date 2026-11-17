# TrustHire — Beyond Fake-Job Classification

A reproducible TrustHire research prototype for assessing vacancy authorization with explicit evidence provenance and source-lineage correction. Employer identity, vacancy authorization, textual risk, retrieval failure, and uncertainty are kept as separate concepts.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\initialize_database.py
python -m pytest -q
```

Optional interface: `streamlit run app.py`. The Streamlit workspace provides:

- pasted-text, public-URL, and recruitment-poster intake;
- structured extraction with warnings kept visible;
- evidence availability metrics and an evidence-state chart;
- separate ordinary and lineage-aware aggregation summaries, kept distinct from the command-line research evaluation;
- expandable evidence and extracted-field views.

The live workspace does not expose synthetic reference labels or a benchmark case picker. Synthetic A/B/C evaluation remains a separate CLI workflow. Live evidence receives `unknown`/`not_assessed` lineage metadata unless a relationship already has the explicit adjudication required by the lineage schema. The final live decision requires at least two qualifying independent source groups; without that evidence it remains unresolved.

Employer authority is configured in `config/employer_sources_v1.json`. The current version has one scoped, verified mapping for Stripe's employer-owned `stripe.com/careers/` pages, documented from Stripe's public role pages. It does not infer that a third-party ATS domain is authorized. Add mappings only when the employer-domain or employer-controlled ATS relationship is documented; include the employer ID/name, relationship type, `verification_status`, provenance and `last_verified_at`. Unverified and incomplete mappings are ignored. User-entered links never change this configuration.

Freshness uses source `datePosted`/`dateModified` and `validThrough` as separate fields. The default 180-day currentness window is a conservative configured policy, not an empirically calibrated threshold. A recent retrieval timestamp alone does not make an old posting current.

Start the interface on Windows PowerShell with:

```powershell
streamlit run app.py
```

Run the automated UI smoke workflow with:

```powershell
python scripts\smoke_test_streamlit.py
```

Outputs are **automated, machine-generated evidence assessments** based on available public evidence and configured rules; they are **not independently adjudicated conclusions**. The interface does not authorize collection or alter original research artifacts. Automated validation mode can run without manual case-by-case human review; historical human-review artifacts (if present) are preserved for research traceability. Backend evaluation remains command-line/script-based.

Run the reviewed pilot evaluation with:

```powershell
python -m src.evaluation.runner --data data/annotations/pilot.jsonl --output artifacts/experiments/pilot_results.json
```

Run the provisional research comparison with:

```powershell
python scripts\build_independent_review.py
python scripts\run_research_evaluation.py
python scripts\render_research_report.py
python -m pytest -q
```

This workflow emits aggregate metrics, predictions, a group-aware split manifest, configuration, and a research report under `artifacts/experiments/research_v1/` and `docs/research_evaluation_report_v1.md`. The current review set is explicitly provisional and single-reviewer; it is not final independent ground truth.

Run the pre-collection gate with:

```powershell
python scripts\validate_collection_readiness.py
```

The template in `config/collection_config_v1.json` is intentionally not authorized: dates, reviewers, privacy/retention decisions, and approval must be completed by the research team. The command only validates readiness and writes a report; it does not collect records or labels.

Validate the packaged research CSV in a read-only staging pass with:

```powershell
python scripts\validate_staging_package.py integration_review\schema_test\disposable_staging_import.csv --cohort stripe_greenhouse_780
```

The staging adapter preserves source-family, source-instance, retrieval-event, URL, timestamp, hash, and lineage fields. Naukri rows are excluded by default, candidate lineage is never promoted to confirmed lineage, and no authorization or fraud labels are assigned.

## Importing a public job-posting CSV

Place the original CSV at `data/raw/fake_job_postings.csv` or pass another path. The importer preserves the original file, writes normalized raw records to `data/processed/`, preserves any source `fraudulent` label separately, and assigns authorization as `unresolved` until vacancy-specific evidence is reviewed.

```powershell
python scripts\import_job_dataset.py
python scripts\import_job_dataset.py --csv_path data\raw\your_file.csv --output data\processed\your_file.jsonl --report data\processed\your_file_report.json
```

Do not place unreviewed imported records in `data/annotations/`; that directory is reserved for reviewed evidence and authorization labels.

The repository contains a raw public job-posting dataset, but no real vacancy-authorization-labelled dataset. Imported fraud labels are source labels only. Synthetic examples are for demonstrations and tests only; they are excluded from research metrics. Add reviewed authorization records to `data/annotations/` before training or reporting authorization results.

### Optional recruitment-poster OCR

Poster OCR is optional and requires Pillow, pytesseract, and the Tesseract OCR engine installed separately. The Streamlit verifier accepts PNG, JPG/JPEG, and WEBP posters and stores the original bytes and the extracted text as separate timestamped SQLite source records. If the OCR engine is unavailable or fails, the system records an extraction limitation and leaves vacancy fields unresolved; it does not fabricate text.

## Research question

Does lineage-aware aggregation of external evidence improve assessment of individual vacancy authorization over text-only and ordinary employer-context baselines, especially when advertisements are copied or evidence is incomplete?

## Architecture

`src/ingestion` safely fetches and extracts content; `src/database` persists traceable records; `src/evidence` models claim-level observations; `src/lineage` finds and reviews possible copies; `src/aggregation` compares naive and dependency-aware evidence; `src/decision` applies abstention rules; `src/ml` provides an optional TF-IDF/logistic-regression baseline; `src/evaluation` validates data and computes metrics.

See `docs/` for the specification, annotation guide, methodology, protocol, dataset card, limitations, and paper outline.

See [the accuracy improvement status](docs/accuracy_improvement_status.md) for completed engineering changes, corpus scope, and work that still requires independent human review.

## Limitations

No external source is treated as authoritative automatically, no missing careers listing is treated as fraud, and no model is considered validated without a defensible labelled dataset. Retrieval is best-effort and respects public HTTP/HTTPS access only.
