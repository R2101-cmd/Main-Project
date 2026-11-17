"""Controlled A/B/C evaluation for the frozen synthetic benchmark v2 split."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
from collections import Counter
from pathlib import Path
from typing import Any

import sklearn

from src.aggregation.rules import lineage_aware, naive
from src.datasets.benchmark_split_v2 import PARTITIONS, SOURCE_FILE_HASH_BASELINE, SPLIT_SEED, _read, validate_split
from src.ml.text_classifier import TextBaseline

CLASSES = ("supported", "contradicted", "unresolved")
MODEL_SEED = 20261116
BOOTSTRAP_SEED = 20261117
BOOTSTRAP_REPLICATES = 10000
Z_95 = 1.959963984540054


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wilson(successes: int, total: int) -> dict[str, float | None]:
    if total == 0:
        return {"lower": None, "upper": None}
    p = successes / total
    denominator = 1 + Z_95 * Z_95 / total
    center = (p + Z_95 * Z_95 / (2 * total)) / denominator
    margin = Z_95 * math.sqrt((p * (1 - p) + Z_95 * Z_95 / (4 * total)) / total) / denominator
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def calculate_metrics(actual: list[str], predicted: list[str]) -> dict[str, Any]:
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted lengths differ")
    if any(label not in CLASSES for label in actual + predicted):
        raise ValueError("unknown authorization class")
    n = len(actual)
    matrix = {truth: {prediction: 0 for prediction in CLASSES} for truth in CLASSES}
    for truth, prediction in zip(actual, predicted):
        matrix[truth][prediction] += 1
    per_class: dict[str, dict[str, float | int]] = {}
    for label in CLASSES:
        tp = matrix[label][label]
        fp = sum(matrix[truth][label] for truth in CLASSES if truth != label)
        fn = sum(matrix[label][prediction] for prediction in CLASSES if prediction != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": sum(matrix[label].values())}
    correct = sum(a == p for a, p in zip(actual, predicted))
    fa_denominator = sum(label != "supported" for label in actual)
    fa_count = sum(a != "supported" and p == "supported" for a, p in zip(actual, predicted))
    unresolved_count = predicted.count("unresolved")
    covered_count = n - unresolved_count
    covered_correct = sum(a == p for a, p in zip(actual, predicted) if p != "unresolved")
    precision_macro = sum(per_class[label]["precision"] for label in CLASSES) / len(CLASSES)
    recall_macro = sum(per_class[label]["recall"] for label in CLASSES) / len(CLASSES)
    f1_macro = sum(per_class[label]["f1"] for label in CLASSES) / len(CLASSES)
    return {
        "n": n,
        "class_distribution": dict(sorted(Counter(actual).items())),
        "correct_count": correct,
        "accuracy": correct / n if n else None,
        "accuracy_95_wilson_ci": _wilson(correct, n),
        "macro_precision": precision_macro,
        "macro_recall": recall_macro,
        "macro_f1": f1_macro,
        "per_class": per_class,
        "confusion_matrix": matrix,
        "unresolved_prediction_count": unresolved_count,
        "unresolved_prediction_rate": unresolved_count / n if n else None,
        "covered_count": covered_count,
        "coverage": covered_count / n if n else None,
        "covered_case_correct_count": covered_correct,
        "covered_case_accuracy": covered_correct / covered_count if covered_count else None,
        "false_assurance_count": fa_count,
        "false_assurance_denominator": fa_denominator,
        "false_assurance_rate": fa_count / fa_denominator if fa_denominator else None,
        "false_assurance_95_wilson_ci": _wilson(fa_count, fa_denominator),
    }


def _paired_bootstrap_delta(a: list[str], b: list[str], actual: list[str], *, metric: str, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    n = len(actual)
    deltas = []
    for _ in range(BOOTSTRAP_REPLICATES):
        indices = [rng.randrange(n) for _ in range(n)]
        ys = [actual[i] for i in indices]
        aa = [a[i] for i in indices]
        bb = [b[i] for i in indices]
        if metric == "accuracy":
            value_a = sum(x == y for x, y in zip(ys, aa)) / n
            value_b = sum(x == y for x, y in zip(ys, bb)) / n
        elif metric == "macro_f1":
            value_a = calculate_metrics(ys, aa)["macro_f1"]
            value_b = calculate_metrics(ys, bb)["macro_f1"]
        else:
            raise ValueError(f"unsupported bootstrap metric: {metric}")
        deltas.append(value_a - value_b)
    deltas.sort()
    return {
        "estimate_c_minus_b": (calculate_metrics(actual, a)[metric] - calculate_metrics(actual, b)[metric]),
        "ci_method": "paired percentile bootstrap over test cases",
        "confidence_level": 0.95,
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": seed,
        "ci_lower": deltas[int(0.025 * (BOOTSTRAP_REPLICATES - 1))],
        "ci_upper": deltas[int(0.975 * (BOOTSTRAP_REPLICATES - 1))],
    }


def _exact_mcnemar(correct_b: list[bool], correct_c: list[bool]) -> dict[str, Any]:
    c_only = sum(c and not b for b, c in zip(correct_b, correct_c))
    b_only = sum(b and not c for b, c in zip(correct_b, correct_c))
    discordant = c_only + b_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = min(c_only, b_only)
        p_value = min(1.0, 2 * sum(math.comb(discordant, i) for i in range(tail + 1)) / (2**discordant))
    return {
        "test": "exact two-sided McNemar test",
        "c_correct_b_incorrect": c_only,
        "b_correct_c_incorrect": b_only,
        "discordant_pairs": discordant,
        "p_value": p_value,
        "interpretation_limit": "Small synthetic test set; this paired test does not establish real-world superiority.",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def predict_test_records(train_inputs: list[dict[str, Any]], train_labels: list[dict[str, Any]], test_inputs: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Fit A on train text/labels and apply A/B/C to test model inputs only."""
    if len(train_inputs) != len(train_labels):
        raise ValueError("train inputs and labels are misaligned")
    train_texts = [row["advertisement"].get("text") or "" for row in train_inputs]
    train_y = [row["expected_label"] for row in train_labels]
    text_model = TextBaseline.train(train_texts, train_y, seed=MODEL_SEED)
    predictions: dict[str, list[str]] = {"A_text_only": [], "B_ordinary_aggregation": [], "C_lineage_aware_aggregation": []}
    for record in test_inputs:
        # A sees only text; B and C see only the same record's evidence list.
        text = record["advertisement"].get("text") or ""
        evidence = record.get("evidence") or []
        predictions["A_text_only"].append(text_model.predict(text)["label"])
        predictions["B_ordinary_aggregation"].append(naive(evidence).state)
        dependent_groups = {
            item.get("lineage_group") or item.get("lineage_group_id")
            for item in evidence
            if item.get("source_relationship") == "copied_derived"
            and item.get("lineage_review_status") == "adjudicated"
            and (item.get("lineage_group") or item.get("lineage_group_id"))
        }
        predictions["C_lineage_aware_aggregation"].append(lineage_aware(evidence, dependent_groups).state)
    return predictions


def run_evaluation(source_dir: Path, split_dir: Path, output_dir: Path) -> dict[str, Any]:
    split_errors = validate_split(source_dir, split_dir)
    if split_errors:
        raise ValueError("split validation failed: " + "; ".join(split_errors[:8]))

    # Training labels are the only labels read before the test predictions are frozen.
    train_inputs = _read(split_dir / "train.jsonl")
    train_labels = _read(split_dir / "train_labels.jsonl")
    test_inputs = _read(split_dir / "test.jsonl")
    # Predict each test record using model inputs only; no test label or scenario file is read here.
    predictions = predict_test_records(train_inputs, train_labels, test_inputs)

    # Test labels and scenario metadata are loaded only after all three prediction vectors are fixed.
    test_labels = _read(split_dir / "test_labels.jsonl")
    test_scenarios = _read(split_dir / "test_scenarios.jsonl")
    if len(test_inputs) != len(test_labels) or len(test_inputs) != len(test_scenarios):
        raise ValueError("test input and evaluation-only mappings are misaligned")
    actual = [row["expected_label"] for row in test_labels]
    if any(len(values) != len(actual) for values in predictions.values()):
        raise ValueError("approaches did not predict the same test cases")
    metrics = {method: calculate_metrics(actual, values) for method, values in predictions.items()}

    case_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    for ordinal, (record, label_row) in enumerate(zip(test_inputs, test_labels)):
        expected = actual[ordinal]
        row: dict[str, Any] = {"partition_record_ordinal": ordinal, "expected_authorization_label": expected}
        for method, short in (("A_text_only", "A"), ("B_ordinary_aggregation", "B"), ("C_lineage_aware_aggregation", "C")):
            prediction = predictions[method][ordinal]
            row[f"{short}_prediction"] = prediction
            row[f"{short}_correct"] = prediction == expected
            row[f"{short}_false_assurance"] = expected != "supported" and prediction == "supported"
        case_rows.append(row)
        a, b, c = (predictions[name][ordinal] for name in ("A_text_only", "B_ordinary_aggregation", "C_lineage_aware_aggregation"))
        b_correct, c_correct = b == expected, c == expected
        evidence = record.get("evidence", [])
        comparison_rows.append({
            "partition_record_ordinal": ordinal,
            "expected_authorization_label": expected,
            "A_prediction": a,
            "B_prediction": b,
            "C_prediction": c,
            "B_C_comparison": "both_correct" if b_correct and c_correct else "C_correct_B_incorrect" if c_correct else "B_correct_C_incorrect" if b_correct else "both_incorrect",
            "A_differs_from_B": a != b,
            "A_differs_from_C": a != c,
            "evidence_state_counts": json.dumps(dict(sorted(Counter(e.get("evidence_state", "missing") for e in evidence).items())), sort_keys=True),
            "lineage_relationship_counts": json.dumps(dict(sorted(Counter(e.get("source_relationship", "missing") for e in evidence).items())), sort_keys=True),
            "lineage_review_status_counts": json.dumps(dict(sorted(Counter(e.get("lineage_review_status", "missing") for e in evidence).items())), sort_keys=True),
            "verification_status_counts": json.dumps(dict(sorted(Counter(e.get("verification_status", "missing") for e in evidence).items())), sort_keys=True),
        })

    scenario_rows: list[dict[str, Any]] = []
    for scenario in sorted({row["scenario"] for row in test_scenarios}):
        indices = [i for i, row in enumerate(test_scenarios) if row["scenario"] == scenario]
        scenario_actual = [actual[i] for i in indices]
        for method, method_predictions in predictions.items():
            scenario_metrics = calculate_metrics(scenario_actual, [method_predictions[i] for i in indices])
            scenario_rows.append({
                "scenario_family": scenario,
                "approach": method,
                "n": scenario_metrics["n"],
                "expected_class_distribution": json.dumps(scenario_metrics["class_distribution"], sort_keys=True),
                "accuracy": scenario_metrics["accuracy"],
                "macro_precision": scenario_metrics["macro_precision"],
                "macro_recall": scenario_metrics["macro_recall"],
                "macro_f1": scenario_metrics["macro_f1"],
                "false_assurance_count": scenario_metrics["false_assurance_count"],
                "false_assurance_denominator": scenario_metrics["false_assurance_denominator"],
                "unresolved_prediction_rate": scenario_metrics["unresolved_prediction_rate"],
                "coverage": scenario_metrics["coverage"],
            })

    actual_by_method = predictions
    b_correct = [p == y for p, y in zip(actual_by_method["B_ordinary_aggregation"], actual)]
    c_correct = [p == y for p, y in zip(actual_by_method["C_lineage_aware_aggregation"], actual)]
    statistical = {
        "paired_B_vs_C": _exact_mcnemar(b_correct, c_correct),
        "delta_accuracy_C_minus_B": _paired_bootstrap_delta(actual_by_method["C_lineage_aware_aggregation"], actual_by_method["B_ordinary_aggregation"], actual, metric="accuracy", seed=BOOTSTRAP_SEED),
        "delta_macro_f1_C_minus_B": _paired_bootstrap_delta(actual_by_method["C_lineage_aware_aggregation"], actual_by_method["B_ordinary_aggregation"], actual, metric="macro_f1", seed=BOOTSTRAP_SEED + 1),
        "paired_case_count": len(actual),
    }
    confusion = {method: value["confusion_matrix"] for method, value in metrics.items()}
    source_hashes = {name: _sha(source_dir / name) for name in SOURCE_FILE_HASH_BASELINE}
    split_hashes = {path.name: _sha(path) for path in sorted(split_dir.iterdir()) if path.is_file()}
    manifest = {
        "name": "synthetic_benchmark_v2_controlled_abc_evaluation",
        "benchmark_source_hashes_sha256": source_hashes,
        "split_package_hashes_sha256": split_hashes,
        "split_seed": SPLIT_SEED,
        "model_seed": MODEL_SEED,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "train_records": len(train_inputs),
        "test_records": len(test_inputs),
        "test_expected_class_distribution": dict(sorted(Counter(actual).items())),
        "approaches_used_identical_test_cases": True,
        "scenario_metadata_exposed_to_predictors": False,
        "test_labels_used_for_training_or_tuning": False,
        "validation_partition_used_for_tuning": False,
        "approaches": {
            "A_text_only": "Existing TextBaseline: TF-IDF word unigram/bigram with scikit-learn logistic regression; fit on train advertisement.text and train expected labels only; prediction uses advertisement.text only.",
            "B_ordinary_aggregation": "Production src.aggregation.rules.naive over each test record's evidence; appearance-level aggregation without lineage deduplication.",
            "C_lineage_aware_aggregation": "Production src.aggregation.rules.lineage_aware over the same evidence, passing adjudicated copied_derived group keys; unknown or missing lineage is excluded by production rules.",
        },
        "software": {"python": platform.python_version(), "scikit_learn": sklearn.__version__},
        "test_partition_has_15_known_scenario_families": len({row["scenario"] for row in test_scenarios}) == 15,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _json(output_dir / "metrics_summary.json", {"test": metrics, "test_class_distribution": dict(sorted(Counter(actual).items())), "test_n": len(actual)})
    metric_rows = []
    for method, value in metrics.items():
        metric_rows.append({
            "approach": method, "n": value["n"], "accuracy_count": value["correct_count"], "accuracy": value["accuracy"], "accuracy_percent": 100 * value["accuracy"],
            "macro_precision": value["macro_precision"], "macro_precision_percent": 100 * value["macro_precision"],
            "macro_recall": value["macro_recall"], "macro_recall_percent": 100 * value["macro_recall"],
            "macro_f1": value["macro_f1"], "macro_f1_percent": 100 * value["macro_f1"],
            "false_assurance_count": value["false_assurance_count"], "false_assurance_denominator": value["false_assurance_denominator"], "false_assurance_rate": value["false_assurance_rate"], "false_assurance_percent": 100 * value["false_assurance_rate"] if value["false_assurance_rate"] is not None else None,
            "unresolved_prediction_count": value["unresolved_prediction_count"], "unresolved_prediction_rate": value["unresolved_prediction_rate"], "unresolved_prediction_percent": 100 * value["unresolved_prediction_rate"],
            "covered_count": value["covered_count"], "coverage": value["coverage"], "coverage_percent": 100 * value["coverage"],
            "covered_case_accuracy": value["covered_case_accuracy"], "covered_case_accuracy_percent": 100 * value["covered_case_accuracy"] if value["covered_case_accuracy"] is not None else None,
        })
    _write_csv(output_dir / "metrics_summary.csv", metric_rows)
    _json(output_dir / "confusion_matrices.json", confusion)
    _write_csv(output_dir / "case_level_predictions.csv", case_rows)
    _write_csv(output_dir / "case_level_comparison.csv", comparison_rows)
    _write_csv(output_dir / "scenario_level_results.csv", scenario_rows)
    _json(output_dir / "statistical_comparison.json", statistical)
    _json(output_dir / "evaluation_manifest.json", manifest)
    (output_dir / "evaluation_methodology.md").write_text(methodology_text(manifest, metrics, statistical), encoding="utf-8")
    (output_dir / "limitations.md").write_text(limitations_text(manifest), encoding="utf-8")
    return {"metrics": metrics, "statistical_comparison": statistical, "manifest": manifest}


def methodology_text(manifest: dict[str, Any], metrics: dict[str, Any], statistical: dict[str, Any]) -> str:
    return f"""# Synthetic benchmark v2 A/B/C evaluation methodology

## Target and data use

The target is `vacancy_authorization_label`, with `supported`, `contradicted`, and `unresolved` outcomes. This controlled synthetic experiment evaluates the 60-case frozen test partition only. The benchmark inputs, expected labels, scenario metadata, and group-safe split remain separate. All three approaches receive the same test records. No case ID, scenario, expected label, or scenario metadata is passed to a predictor.

Training uses only the 180 train-partition texts and labels. A uses the existing `TextBaseline` (TF-IDF word unigrams/bigrams and logistic regression) with model seed {manifest['model_seed']}; inference uses only the advertisement text. B calls production `naive()` on the evidence list. C calls production `lineage_aware()` on that same evidence, passing only explicitly adjudicated copied-derived group keys. No thresholds or aggregation rules were tuned. Validation data was not used for configuration. Test labels and scenario metadata were read only after all test predictions were fixed.

## Metrics

Accuracy includes all test cases, including unresolved predictions. Macro precision, recall, and F1 average the three classes with zero assigned to undefined class metrics. Coverage is the fraction predicted supported or contradicted; unresolved predictions count as abstentions. False assurance is a prediction of supported on an expected contradicted or unresolved case. Its denominator is all expected non-supported test cases, including unresolved. Accuracy and false-assurance intervals use 95% Wilson intervals. B versus C uses exact two-sided McNemar on paired correctness and paired percentile bootstrap intervals for C-minus-B accuracy and macro-F1 ({BOOTSTRAP_REPLICATES} resamples; fixed seeds recorded in the manifest).

## Test-set scope and observed comparison

The test set has {manifest['test_records']} cases and expected class distribution {manifest['test_expected_class_distribution']}. It includes 15 scenario families, each represented in every split (4 test cases per family). It therefore measures held-out cases within known families; it is not an unseen-scenario generalization test.

Observed test accuracy: A {metrics['A_text_only']['accuracy']:.3f}, B {metrics['B_ordinary_aggregation']['accuracy']:.3f}, C {metrics['C_lineage_aware_aggregation']['accuracy']:.3f}. Paired B-versus-C exact McNemar p={statistical['paired_B_vs_C']['p_value']:.4f}; this small synthetic set does not justify broad superiority claims.

The benchmark's outcomes are synthetic scenario-construction labels, not independently adjudicated real-world ground truth. These values are controlled experimental results only.
"""


def limitations_text(manifest: dict[str, Any]) -> str:
    return f"""# Limitations

- All {manifest['test_records']} test cases and their expected labels are synthetic; metrics are not real-world accuracy or evidence of operational performance.
- The test set contains all 15 scenario families seen in train and validation. No unseen-scenario generalization is tested.
- There are only four test examples per scenario family and 20 per expected class; confidence intervals and per-family metrics are imprecise.
- Text-only classification is a small TF-IDF/logistic-regression baseline trained on 180 synthetic examples. It is not a validated production language model.
- The scenario construction explicitly encodes evidence states and lineage. Results depend on those authored scenarios and do not establish that real official sources, ATS control, or lineage can be identified with the same reliability.
- B and C are deterministic production aggregation functions. Their behavior reflects current rules, including conservative exclusion of unverified lineage and aggregation's contradiction precedence.
- The paired significance test has low power at this sample size. A non-significant result is not evidence of equivalence.
- No real advertisement records, evidence rows, annotations, or historical evaluation outputs were used as labels or modified.
"""

