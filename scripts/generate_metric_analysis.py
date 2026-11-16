"""Generate read-only metric tables from existing prediction artifacts."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "final_completion_package" / "metric_analysis"
LABELS = ["contradicted", "supported", "unresolved"]


def wilson(success: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if not total:
        return None, None
    p = success / total
    d = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / d
    half = z * math.sqrt((p * (1 - p) / total) + z * z / (4 * total * total)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def metric_row(benchmark: str, subset: str, method: str, actual: list[str], predicted: list[str], source: str) -> dict:
    n = len(actual)
    support = Counter(actual)
    predicted_counts = Counter(predicted)
    assessed = sum(p != "unresolved" for p in predicted)
    correct = sum(a == p for a, p in zip(actual, predicted))
    selective_correct = sum(a == p for a, p in zip(actual, predicted) if p != "unresolved")
    non_supported = sum(a != "supported" for a in actual)
    false_assurance = sum(p == "supported" and a != "supported" for a, p in zip(actual, predicted))
    acc_lo, acc_hi = wilson(correct, n)
    fa_lo, fa_hi = wilson(false_assurance, non_supported)
    cm = confusion_matrix(actual, predicted, labels=LABELS).tolist()
    per_class = {}
    for label in LABELS:
        tp = sum(a == label and p == label for a, p in zip(actual, predicted))
        predicted_label = sum(p == label for p in predicted)
        label_precision = tp / predicted_label if predicted_label else 0.0
        label_recall = tp / support[label] if support[label] else 0.0
        denom = label_precision + label_recall
        label_f1 = 2 * label_precision * label_recall / denom if denom else 0.0
        rlo, rhi = wilson(tp, support[label])
        per_class[label] = {
            "precision": label_precision,
            "recall": label_recall,
            "f1": label_f1,
            "support": support[label],
            "recall_95_wilson_ci": {"lower": rlo, "upper": rhi},
        }
    return {
        "benchmark": benchmark,
        "subset": subset,
        "method": method,
        "source": source,
        "n": n,
        "class_distribution": dict(support),
        "predicted_distribution": dict(predicted_counts),
        "accuracy": accuracy_score(actual, predicted),
        "accuracy_95_wilson_ci": {"lower": acc_lo, "upper": acc_hi},
        "balanced_accuracy": balanced_accuracy_score(actual, predicted),
        "macro_precision": precision_score(actual, predicted, labels=LABELS, average="macro", zero_division=0),
        "macro_recall": recall_score(actual, predicted, labels=LABELS, average="macro", zero_division=0),
        "macro_f1": f1_score(actual, predicted, labels=LABELS, average="macro", zero_division=0),
        "per_class": per_class,
        "confusion_matrix_labels": LABELS,
        "confusion_matrix": cm,
        "false_assurance_count": false_assurance,
        "false_assurance_denominator": non_supported,
        "false_assurance_rate": false_assurance / non_supported if non_supported else None,
        "false_assurance_95_wilson_ci": {"lower": fa_lo, "upper": fa_hi},
        "coverage": assessed / n if n else None,
        "selective_accuracy": selective_correct / assessed if assessed else None,
        "selective_risk": 1 - selective_correct / assessed if assessed else None,
        "abstention_rate": (n - assessed) / n if n else None,
        "insufficient_sample_warning": [
            f"class {label} has support {support[label]}" for label in LABELS if support[label] < 10
        ],
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_case_level_benchmark(results: list[dict], benchmark: str, subset: str, csv_path: Path, actual_col: str, methods: dict[str, str], source: str) -> None:
    rows = read_csv(csv_path)
    actual = [row[actual_col] for row in rows]
    for method, column in methods.items():
        predicted = [row[column] for row in rows]
        results.append(metric_row(benchmark, subset, method, actual, predicted, source))


def add_v3(results: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pred_path = ROOT / "final_completion_package/current_implementation_evaluation_v1/case_level_predictions.csv"
    expected_path = ROOT / "research-data/phase2_v1/synthetic/synthetic_benchmark_v3/expected_labels.jsonl"
    predictions = read_csv(pred_path)
    expected = {row["input_key"]: row["expected_label"] for row in read_jsonl(expected_path)}
    keys = [row["input_key"] for row in predictions]
    if set(keys) != set(expected) or len(keys) != len(set(keys)):
        raise ValueError("v3 prediction/label keys are not exactly aligned")
    for row in predictions:
        row["expected_label"] = expected[row["input_key"]]
    temp = OUT / "_v3_aligned.csv"
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)
    add_case_level_benchmark(
        results, "synthetic_v3_current_implementation", "all", temp, "expected_label",
        {"E1_text_only": "A_text_only", "E4_ordinary_aggregation": "B_ordinary_aggregation",
         "E5_lineage_aware_raw": "C_lineage_aware_raw", "E5_lineage_aware_live_policy": "C_lineage_aware_live_policy"},
        "existing v3 case-level predictions + expected_labels.jsonl",
    )
    temp.unlink()


def add_v2(results: list[dict]) -> None:
    path = ROOT / "final_completion_package/synthetic_evaluation_v2/case_level_predictions.csv"
    add_case_level_benchmark(
        results, "synthetic_v2", "test", path, "expected_authorization_label",
        {"E1_text_only": "A_prediction", "E4_ordinary_aggregation": "B_prediction", "E5_lineage_aware_aggregation": "C_prediction"},
        "existing v2 test case-level predictions with embedded expected labels",
    )


def add_provisional(results: list[dict]) -> None:
    path = ROOT / "artifacts/experiments/e2_e3_mvp.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for method, data in payload["methods"].items():
        if data.get("status") == "not_run":
            continue
        cls = data["classification"]
        selective = data.get("selective", {})
        row = {
            "benchmark": "provisional_145_record_evaluation",
            "subset": "test",
            "method": method,
            "source": "existing e2_e3_mvp.json summary; no per-case vector reconstructed",
            "n": cls["n"],
            "class_distribution": cls["label_counts"],
            "accuracy": cls["accuracy"],
            "accuracy_95_wilson_ci": {"lower": None, "upper": None},
            "balanced_accuracy": cls["balanced_accuracy"],
            "macro_precision": cls["macro"]["precision"],
            "macro_recall": cls["macro"]["recall"],
            "macro_f1": cls["macro"]["f1"],
            "per_class": cls["per_class"],
            "confusion_matrix_labels": cls["labels"],
            "confusion_matrix": cls["confusion_matrix"],
            "false_assurance_count": selective.get("false_assurance_count"),
            "false_assurance_denominator": selective.get("false_assurance_denominator"),
            "false_assurance_rate": selective.get("false_assurance"),
            "false_assurance_95_wilson_ci": {"lower": None, "upper": None},
            "coverage": selective.get("coverage"),
            "selective_accuracy": None,
            "selective_risk": None,
            "abstention_rate": selective.get("abstention_rate"),
            "insufficient_sample_warning": ["provisional evidence-derived labels; circularity risk", "contradicted class absent from test set"],
        }
        assessed = selective.get("assessed", 0)
        row["selective_accuracy"] = None if not assessed else 1 - selective["selective_risk"]
        row["selective_risk"] = selective.get("selective_risk")
        results.append(row)


def write_outputs(results: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics_complete.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    fields = ["benchmark", "subset", "method", "source", "n", "accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1", "false_assurance_count", "false_assurance_denominator", "false_assurance_rate", "coverage", "selective_accuracy", "selective_risk", "abstention_rate", "accuracy_95_wilson_ci", "false_assurance_95_wilson_ci", "class_distribution", "insufficient_sample_warning"]
    with (OUT / "metrics_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({key: json.dumps(row[key], separators=(",", ":")) if isinstance(row[key], (dict, list)) else row[key] for key in fields})
    with (OUT / "per_class_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["benchmark", "subset", "method", "class", "support", "precision", "recall", "f1", "recall_95_wilson_ci"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            for label, metrics in row["per_class"].items():
                writer.writerow({"benchmark": row["benchmark"], "subset": row["subset"], "method": row["method"], "class": label, **metrics})
    with (OUT / "confusion_matrices.json").open("w", encoding="utf-8") as handle:
        json.dump([{k: row[k] for k in ("benchmark", "subset", "method", "confusion_matrix_labels", "confusion_matrix")} for row in results], handle, indent=2)

    v3 = next(r for r in results if r["benchmark"] == "synthetic_v3_current_implementation")
    v2 = next(r for r in results if r["benchmark"] == "synthetic_v2")
    lines = [
        "# VacancyGuard Metric Analysis",
        "",
        "Generated from existing prediction/label artifacts only. No datasets, annotations, benchmarks, source code, model logic, or labels were modified.",
        "",
        "## Scope and integrity",
        "",
        "- Synthetic v2 and current synthetic v3 are reported separately; no metrics are combined across versions.",
        "- The provisional 145-record evaluation is reported separately and flagged as circularity-risk/evidence-derived.",
        "- v3 prediction keys were checked against the 150 expected-label keys: exact one-to-one alignment.",
        "- v2 contains 60 test cases with 20 cases per class; all methods use the same test cases.",
        "- The provisional test contains 16 records: 15 unresolved, 1 supported, and 0 contradicted; this is insufficient for class-balanced claims.",
        "- Accuracy and false-assurance 95% intervals are Wilson intervals where raw vectors were available. Per-class recall Wilson intervals are included. Precision, F1, macro metrics, and balanced accuracy have no simple binomial interval here and are reported without fabricated intervals.",
        "",
        "## Summary",
        "",
        "| Benchmark | Method | n | Accuracy | Balanced accuracy | Macro F1 | False assurance | Coverage | Selective accuracy |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        fa = "NA" if row["false_assurance_rate"] is None else f"{row['false_assurance_rate']:.3f} ({row['false_assurance_count']}/{row['false_assurance_denominator']})"
        vals = [row["benchmark"], row["method"], str(row["n"]), f"{row['accuracy']:.3f}", f"{row['balanced_accuracy']:.3f}", f"{row['macro_f1']:.3f}", fa, "NA" if row["coverage"] is None else f"{row['coverage']:.3f}", "NA" if row["selective_accuracy"] is None else f"{row['selective_accuracy']:.3f}"]
        lines.append("| " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Per-class and confusion-matrix outputs",
        "",
        "Complete per-class precision, recall, F1, support, recall intervals, and confusion matrices are in `metrics_complete.json`, `per_class_metrics.csv`, and `confusion_matrices.json`.",
        "",
        "## Interpretation and limitations",
        "",
        "- Synthetic v2/v3 metrics are valid calculations for their authored benchmarks, but their labels are synthetic design labels. They are implementation checks, not real-world performance estimates.",
        "- The current v3 live-policy E5 result must not be called operational accuracy: its labels are constructed from the same policy conditions.",
        "- The provisional metrics are not suitable for paper performance claims because the labels are evidence-derived, the test set is tiny, and the contradicted class is absent.",
        "- Accuracy alone is inadequate because unresolved abstention is a meaningful outcome. Report coverage, selective accuracy, abstention, false assurance, per-class recall, and confusion matrices together.",
        "- Macro metrics are preferable to weighted metrics under class imbalance, but macro values are unstable when a class has few or zero test examples.",
        "- No real-world accuracy is available for the 2,980-record cohort or the separate 198-record Naukri cohort.",
        "",
        "## Research-paper suitability",
        "",
        "Suitable: benchmark-specific synthetic accuracy, per-class metrics, confusion matrices, Wilson intervals, coverage, selective accuracy, and false-assurance rates when explicitly labeled as synthetic implementation results.",
        "",
        "Not suitable as real-world claims: any extrapolation from v2/v3 to deployment, any claim of improved real-world E5 performance, and any accuracy claim for the 2,980-record collected cohort without independent adjudication.",
        "",
        "## Protected-file confirmation",
        "",
        "Protected annotation and synthetic split hashes remained unchanged during this analysis; no protected dataset, label, annotation, benchmark, or model file was modified.",
    ]
    (OUT / "metric_analysis_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text("# Metric analysis artifacts\n\nGenerated from existing prediction and label artifacts by `scripts/generate_metric_analysis.py`. See `metric_analysis_report.md` for interpretation and limitations.\n", encoding="utf-8")


if __name__ == "__main__":
    rows: list[dict] = []
    add_v2(rows)
    add_v3(rows)
    add_provisional(rows)
    write_outputs(rows)
    print(json.dumps({"rows": len(rows), "output": str(OUT)}, indent=2))
