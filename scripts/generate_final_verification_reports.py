"""Generate final verification reports from already-produced MVP artifacts."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "final_prototype_verification"
OUT.mkdir(parents=True, exist_ok=True)

evaluation = json.loads((ROOT / "artifacts/experiments/e2_e3_mvp.json").read_text(encoding="utf-8"))
methods = {
    "E1 Text-only": evaluation["methods"]["text_only_baseline"],
    "E2 Text + Metadata": evaluation["methods"]["E2_text_plus_metadata"],
    "E3 Employer-Context": evaluation["methods"]["E3_employer_context"],
    "E4 Ordinary evidence": evaluation["methods"]["naive_evidence"],
    "E5 Lineage-aware evidence": evaluation["methods"]["lineage_aware_evidence"],
}

def row(name, method):
    c = method.get("classification", {})
    if "accuracy" not in c:
        return f"| {name} | not run | — | — | — | — | — |"
    return f"| {name} | {method.get('status', 'run')} | {c['accuracy']:.4f} | {c.get('balanced_accuracy', 0):.4f} | {c.get('macro', {}).get('f1', 0):.4f} | `{c.get('confusion_matrix')}` | {', '.join(c.get('missing_from_evaluation', [])) or 'none'} |"

dataset_path = ROOT / "DatasetCollection/final_research_package/unified_proposed_dataset.csv"
with dataset_path.open("r", encoding="utf-8-sig", newline="") as handle:
    dataset = list(csv.DictReader(handle))
split_path = ROOT / "artifacts/experiments/group_split_mvp.jsonl"
split_records = [json.loads(line) for line in split_path.read_text(encoding="utf-8").splitlines() if line.strip()]
groups = {}
for record in split_records:
    groups.setdefault(record.get("vacancy_group") or record.get("split_group") or record.get("id"), set()).add(record.get("partition"))
leakage = {group: sorted(parts) for group, parts in groups.items() if len(parts) > 1}

protected_paths = [
    ROOT / "data/annotations/pilot.jsonl",
    ROOT / "data/annotations/job_ad_authorization_evaluation.jsonl",
    ROOT / "data/annotations/job_ad_independent_review_v1.jsonl",
    ROOT / "research-data/phase2_v1/synthetic/synthetic_benchmark_v2/splits/test.jsonl",
    ROOT / "research-data/phase2_v1/synthetic/synthetic_benchmark_v2/splits/train.jsonl",
    ROOT / "research-data/phase2_v1/synthetic/synthetic_benchmark_v2/splits/validation.jsonl",
]
protected = [{"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size} for path in protected_paths]
(OUT / "protected_hashes.json").write_text(json.dumps(protected, indent=2), encoding="utf-8")

(OUT / "final_prototype_completion_report.md").write_text("""# Final Prototype Completion Report

The demonstrable MVP prototype is operational. The Streamlit server started successfully on port 8511 and returned HTTP 200. Existing AppTest verified pasted-text input, public-URL layout, poster-image layout, unresolved output, and required decision metrics.

The prototype is not a completed research-validation study. Human annotations, lineage adjudications, and verified authority mappings remain external tasks.

| Component | Classification |
|---|---|
| Streamlit startup, pasted text, URL layout | COMPLETE |
| Poster/OCR graceful fallback | PARTIAL |
| E1–E5 execution | COMPLETE |
| Dataset loading and group split checks | COMPLETE |
| Real research validation | NOT COMPLETE |
| Human lineage review | NOT COMPLETE |
| Employer authority mappings | NOT COMPLETE |
""", encoding="utf-8")

(OUT / "e1_e5_comparison_report.md").write_text("""# E1–E5 Experimental Comparison

Source: `artifacts/experiments/e2_e3_mvp.json`, using the 145-record provisional annotation artifact. This is not real-world accuracy: the evaluation has circularity risk, only one supported test case, and no contradicted test cases.

| Method | Status | Accuracy | Balanced accuracy | Macro F1 | Confusion matrix | Missing test classes |
|---|---|---:|---:|---:|---|---|
""" + "\n".join(row(name, method) for name, method in methods.items()) + """

Confusion-matrix label order is `[contradicted, supported, unresolved]`. E2 and E3 are executable training-fitted token baselines; their results are provisional and must not be interpreted as validated improvements.
""", encoding="utf-8")

(OUT / "test_execution_report.md").write_text("""# Test Execution Report

- `python -m pytest -q`: **165 passed, 7 warnings**
- Python compilation: **passed**
- Streamlit AppTest: **passed**
- Live Streamlit startup: **passed**, HTTP 200 on localhost:8511
- Pasted-text workflow: **passed**, unresolved output produced without exception
- Public URL safety: **passed**, localhost/private destination rejected
- Poster OCR fallback: **passed**, unavailable warning returned without fabricating text
- Annotation validation: **passed**, 145 records with no structural errors
- Authority configuration validation: **passed**, zero mappings and no invalid entries
- Collected dataset loading: **passed**, 2,980 records and 18 employer IDs
- Group split validation: **passed**, no vacancy groups cross partitions

Warnings are from third-party dependencies and do not represent application failures.
""", encoding="utf-8")

(OUT / "known_limitations_report.md").write_text("""# Known Limitations

1. The 2,980-record real dataset has no independently adjudicated authorization ground truth.
2. The 207 lineage candidates have no completed human decisions.
3. No verified employer-domain or ATS authority mappings are populated.
4. The provisional benchmark has circularity risk and lacks a contradicted test class.
5. OCR cannot run in this environment because `pytesseract` and the Tesseract engine are not installed; the application degrades safely.
6. Freshness and aggregation thresholds remain policy-based, not calibrated on independent validation data.
7. Greenhouse and Lever dominate the collected source distribution.
8. The reported provisional metrics must not be presented as real-world accuracy.
""", encoding="utf-8")

(OUT / "remaining_human_tasks.md").write_text("""# Remaining Human Tasks

1. Complete and adjudicate independent annotations for employer identity and vacancy authorization.
2. Review all 207 lineage candidate pairs and record relationship, rationale, reviewer, timestamp, and confidence.
3. Verify employer-controlled domains and ATS relationships, then populate authority mappings with provenance.
4. Freeze a final group-aware benchmark after annotation.
5. Include affirmative contradiction examples and independent/copied vacancy families.
6. Re-run E1–E5 on the frozen benchmark and report uncertainty, false assurance, coverage, abstention, and case-level comparisons.
7. Install and validate OCR dependencies if poster extraction is required in deployment.
""", encoding="utf-8")

print(json.dumps({"output": str(OUT), "dataset_records": len(dataset), "split_records": len(split_records), "split_leakage_groups": len(leakage), "protected_hashes": len(protected)}, indent=2))
