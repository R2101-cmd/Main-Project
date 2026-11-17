# Repository audit

**Execution date:** 2026-11-14  
**Scope:** Read-only inspection plus creation of versioned execution outputs under `final_completion_package/` and two helper scripts.

## Inspected areas
- Root: `README.md`, `app.py`, `requirements.txt`, `.gitignore`, `.streamlit/`, `job_ad_dataset_project_ready.xlsx`
- Source/app: `src/` (aggregation, annotation, collection_readiness, database/schema, datasets, decision, evaluation, evidence, ingestion, lineage, ml, report, ui_support)
- Data: `data/raw/`, `data/processed/`, `data/annotations/`, `data/recruitment_verification.sqlite3`, `data/collection/`
- Collection/research workspace: `DatasetCollection/` (backups, exports, final_research_package, processed, raw stage responses, reports, review_templates, scripts, stage2_outputs)
- Review/integration: `integration_review/` (schema/architecture/compatibility/readiness/risk/proposed plan and staging/provenance audits)
- Research protocol: `research-data/phase2_v1/` (manifests, schemas, protocols, queue, empty core label files, synthetic benchmark)
- Config/schemas: `config/collection_config_v1.json`, `schemas/*.json`
- Docs: `docs/*.md` (specs, protocols, methodology, lineage, metrics, readiness/audit/evaluation reports, limitations, paper outline)
- Scripts/tests/artifacts: `scripts/`, `tests/`, `artifacts/experiments/`

## Key existing outputs found
- **Stage 3 / 780 cohort artifacts:** `DatasetCollection/processed/table_A_advertisements.csv`, `table_B_ground_truth.csv`, `table_C_evidence_records.csv`, `table_B_human_review_preparation.csv`, stage2 outputs and reports.
- **Stage 4 evidence/provenance:** `DatasetCollection/processed/stage4e_evidence_records.csv`, stage4a–4e reports/logs/field comparisons, raw response folders (stage4b/d/e).
- **Stage 4F expansion:** `DatasetCollection/processed/stage4f_expansion_records.csv`, `stage4f_lineage_candidates.csv`, source registry/checkpoint, raw `stage4f_responses/` by employer/source, reports showing 2,200 records collected (interrupted/finalized from checkpoint per log).
- **Stage 5 preparation:** reviewer worksheets, lineage pair review (`stage5b_lineage_pair_review.csv`, 207 pairs), Stage 5A–5C reports indicating no submitted human labels/adjudication and no confirmed lineage.
- **Proposed package:** `DatasetCollection/final_research_package/` with unified 2,980, stripe 780, expansion 2,200, naukri 198 separate, manifests/validation/audits/data dictionary/readiness summaries.
- **Annotations/eval:** `data/annotations/pilot.jsonl` (4), `job_ad_authorization_evaluation.jsonl` (144), `job_ad_independent_review_v1.jsonl` (30) — provisional/single-reviewer context per files/docs; `artifacts/experiments/research_v1*` present.
- **Synthetic benchmark:** `research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl` (60, 20/20/20, seed 20261022) with manifest/schema.

## Architecture summary
- Streamlit UI (`app.py`) for evidence review; safe public retrieval and extraction in `src/ingestion`; evidence modeling/collection in `src/evidence`; lineage candidate signals in `src/lineage`; naive and lineage-aware aggregation in `src/aggregation`; abstention/decision policy in `src/decision`; TF-IDF/LogReg baseline in `src/ml`; SQLite persistence in `src/database`; evaluation/validation/runner in `src/evaluation`; dataset import and readiness tooling in `src/datasets` and scripts.

## Working tree note
`git status` shows pre-existing modified and untracked files unrelated to this execution pass (including prior work in app/src/docs/data/DatasetCollection/integration_review/research-data/scripts/tests). This pass added `final_completion_package/` outputs and helper scripts `scripts/finalize_execution.py`, `scripts/finish_package.py` and generated reports from existing artifacts; it did **not** overwrite original datasets/annotations/stage outputs.
