# Reproducibility notes

## Environment/setup
- Python project (`requirements.txt`): beautifulsoup4, numpy, pandas, pytest, scikit-learn, streamlit, requests, Pillow, pytesseract.
- Typical setup: `python -m venv .venv`, activate, `pip install -r requirements.txt`, `python scripts/initialize_database.py`.

## Re-run checks/experiments
- Tests: `python -m pytest -q` (observed 65 passed, 2 warnings on 2026-11-14).
- Existing provisional research evaluation artifacts: `scripts/run_research_evaluation.py`, `scripts/build_independent_review.py`, `scripts/render_research_report.py` (outputs under `artifacts/experiments/research_v1/` and docs; run recorded exit code 1 in this pass but produced summary/warnings — inspect outputs).
- Collection readiness template validation: `python scripts/validate_collection_readiness.py`.

## This execution’s generated outputs
- Deterministic-from-existing-artifacts generators: `scripts/finalize_execution.py`, `scripts/finish_package.py` → `final_completion_package/`.
- Protected-source checksums recorded in `final_completion_package/01_repository_audit/protected_file_checksums_before.csv`.
- Original source datasets/annotations/stage outputs were not overwritten; proposed package remains in place.

## To achieve defensible real-data evaluation
1. Complete independent official-source live verification with provenance and authority checks.
2. Perform multi-reviewer human adjudication (or explicitly provisional single-reviewer) on a frozen case set; record rationales and disagreements.
3. Confirm/reject lineage candidates and define source families/groups; freeze dataset/splits by employer and lineage group.
4. Re-run three-approach comparison with pre-specified metrics (including false assurance numerator/denominator) on identical adjudicated cases.
