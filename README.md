# Beyond Fake-Job Classification

A reproducible research prototype for assessing vacancy authorization with explicit evidence provenance and source-lineage correction. Employer identity, vacancy authorization, textual risk, retrieval failure, and uncertainty are kept as separate concepts.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\initialize_database.py
pytest -q
```

Optional interface: `streamlit run app.py`. The Streamlit interface contains vacancy verification only. Backend evaluation is command-line only.

Run the reviewed pilot evaluation with:

```powershell
python -m src.evaluation.runner --data data/annotations/pilot.jsonl --output artifacts/experiments/pilot_results.json
```

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

## Limitations

No external source is treated as authoritative automatically, no missing careers listing is treated as fraud, and no model is considered validated without a defensible labelled dataset. Retrieval is best-effort and respects public HTTP/HTTPS access only.
