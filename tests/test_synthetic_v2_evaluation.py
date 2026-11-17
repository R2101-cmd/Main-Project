import csv
import hashlib
import json
from pathlib import Path

from src.evaluation.synthetic_v2 import calculate_metrics, predict_test_records, run_evaluation
from src.datasets.benchmark_split_v2 import SOURCE_FILE_HASH_BASELINE, _read

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research-data" / "phase2_v1" / "synthetic" / "synthetic_benchmark_v2"
SPLITS = SOURCE / "splits"


def _hashes(directory):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.iterdir()) if path.is_file()}


def test_metrics_keep_unresolved_cases_and_use_full_non_supported_denominator():
    actual = ["supported", "contradicted", "unresolved"]
    predicted = ["supported", "supported", "unresolved"]
    result = calculate_metrics(actual, predicted)
    assert result["n"] == 3
    assert result["correct_count"] == 2
    assert result["accuracy"] == 2 / 3
    assert result["unresolved_prediction_count"] == 1
    assert result["coverage"] == 2 / 3
    assert result["false_assurance_count"] == 1
    assert result["false_assurance_denominator"] == 2
    assert result["false_assurance_rate"] == 0.5
    assert result["confusion_matrix"]["unresolved"]["unresolved"] == 1


def test_evaluation_uses_identical_60_test_cases_and_separates_metadata(tmp_path):
    out = tmp_path / "eval"
    result = run_evaluation(SOURCE, SPLITS, out)
    rows = list(csv.DictReader((out / "case_level_predictions.csv").open(encoding="utf-8", newline="")))
    scenarios = list(csv.DictReader((out / "scenario_level_results.csv").open(encoding="utf-8", newline="")))
    manifest = json.loads((out / "evaluation_manifest.json").read_text(encoding="utf-8"))
    assert len(rows) == 60
    assert [int(row["partition_record_ordinal"]) for row in rows] == list(range(60))
    assert {"expected_authorization_label", "A_prediction", "B_prediction", "C_prediction"}.issubset(rows[0])
    assert "scenario_family" not in rows[0]
    assert len(scenarios) == 45  # 15 test scenario families times 3 approaches
    assert manifest["approaches_used_identical_test_cases"] is True
    assert manifest["scenario_metadata_exposed_to_predictors"] is False
    assert manifest["test_labels_used_for_training_or_tuning"] is False
    assert manifest["validation_partition_used_for_tuning"] is False
    assert all(metrics["n"] == 60 for metrics in result["metrics"].values())


def test_evaluation_is_deterministic_and_does_not_modify_sources(tmp_path):
    before = {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in SOURCE_FILE_HASH_BASELINE}
    split_before = _hashes(SPLITS)
    first, second = tmp_path / "first", tmp_path / "second"
    run_evaluation(SOURCE, SPLITS, first)
    run_evaluation(SOURCE, SPLITS, second)
    assert _hashes(first) == _hashes(second)
    after = {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in SOURCE_FILE_HASH_BASELINE}
    assert before == after == SOURCE_FILE_HASH_BASELINE
    assert _hashes(SPLITS) == split_before


def test_predictions_ignore_evaluation_only_test_fields(tmp_path):
    train_inputs = _read(SPLITS / "train.jsonl")
    train_labels = _read(SPLITS / "train_labels.jsonl")
    test_inputs = _read(SPLITS / "test.jsonl")[:5]
    plain = predict_test_records(train_inputs, train_labels, test_inputs)
    contaminated = []
    for row in test_inputs:
        altered = dict(row)
        altered["expected_label"] = "supported" if row["advertisement"]["text"] else "contradicted"
        altered["scenario"] = "evaluation_only_should_not_be_read"
        contaminated.append(altered)
    assert predict_test_records(train_inputs, train_labels, contaminated) == plain

