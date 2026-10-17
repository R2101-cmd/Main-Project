import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.aggregation.rules import lineage_aware, naive
from src.evaluation.metrics import classification_metrics, selective_metrics
from src.ml.text_classifier import TextBaseline
from src.datasets.records import VALID_AUTHORIZATION


def load_jsonl(path: str | Path) -> list[dict]:
    records = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        raise ValueError("dataset is empty")
    return records


def check_group_leakage(records: list[dict]) -> list[str]:
    groups: dict[str, set[str]] = {}
    for record in records:
        groups.setdefault(record["vacancy_group"], set()).add(record["partition"])
    return [group for group, partitions in groups.items() if len(partitions) > 1]


def run(path: str | Path) -> dict:
    records = load_jsonl(path)
    if any(record.get("annotation_status") == "unreviewed_import" for record in records):
        raise ValueError("unreviewed raw imports cannot be used as authorization ground truth")
    invalid_labels = [record.get("id", record.get("record_id")) for record in records if record.get("authorization_label") not in VALID_AUTHORIZATION]
    if invalid_labels:
        raise ValueError(f"invalid or missing authorization labels in {len(invalid_labels)} records")
    leakage = check_group_leakage(records)
    if leakage:
        raise ValueError(f"lineage/vacancy groups cross partitions: {leakage}")
    test = [record for record in records if record["partition"] == "test"]
    fingerprint = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    test_groups = {record.get("vacancy_group", record.get("split_group", record.get("record_id"))) for record in test}
    test_classes = {record["authorization_label"] for record in test}
    warnings = []
    if len(test) < 10 or len(test_groups) < 5:
        warnings.append("Test set is too small for a reliable generalization claim.")
    if len(test_classes) < 2:
        warnings.append("Test set contains fewer than two authorization classes.")
    results: dict = {"dataset": str(path), "dataset_fingerprint": fingerprint, "evaluated_at": datetime.now(timezone.utc).isoformat(), "n": len(records), "independent_vacancy_groups": len({record.get("vacancy_group", record.get("split_group", record.get("record_id"))) for record in records}), "test_records": len(test), "test_independent_vacancy_groups": len(test_groups), "partition_sizes": {partition: sum(record.get("partition") == partition for record in records) for partition in {record.get("partition") for record in records}}, "leakage_groups": leakage, "evaluation_status": "exploratory_insufficient" if warnings else "eligible_for_report", "warnings": warnings, "methods": {}, "task_availability": {"employer_identity": "ground truth unavailable unless reviewed labels are supplied", "vacancy_authorization": "reviewed labels available", "fraud_outcome": "ground truth unavailable unless defensible reviewed labels are supplied"}}
    all_evidence = [item for record in records for item in record.get("evidence", [])]
    all_naive = [naive(record.get("evidence", [])) for record in records]
    all_lineage = [lineage_aware(record.get("evidence", []), {item.get("lineage_group") for item in record.get("evidence", []) if item.get("lineage_group")}) for record in records]
    results["evidence_summary"] = {"records_with_evidence": sum(bool(record.get("evidence")) for record in records), "coverage": sum(bool(record.get("evidence")) for record in records) / len(records), "available_sources": sum(item.get("retrieval_status") in {"available", "available_at_observation"} for item in all_evidence), "unavailable_sources": sum(item.get("retrieval_status") not in {"available", "available_at_observation"} for item in all_evidence), "supported_records": sum(result.state == "supported" for result in all_lineage), "unresolved_records": sum(result.state == "unresolved" for result in all_lineage), "naive_source_appearances": sum(result.effective_sources for result in all_naive), "lineage_effective_sources": sum(result.effective_sources for result in all_lineage), "sources_consolidated": sum(n.effective_sources - l.effective_sources for n, l in zip(all_naive, all_lineage))}
    actual = [record["authorization_label"] for record in test]
    naive_predictions, lineage_predictions, naive_abstain, lineage_abstain = [], [], [], []
    for record in test:
        observations = record.get("evidence", [])
        n = naive(observations)
        l = lineage_aware(observations, {item.get("lineage_group") for item in observations if item.get("lineage_group")})
        naive_predictions.append(n.state)
        lineage_predictions.append(l.state)
        naive_abstain.append(n.state == "unresolved")
        lineage_abstain.append(l.state == "unresolved")
    known_authorization_labels = ["supported", "contradicted", "unresolved"]
    results["methods"]["naive_evidence"] = {"classification": classification_metrics(actual, naive_predictions, known_labels=known_authorization_labels), "selective": selective_metrics(actual, naive_predictions, naive_abstain), "effective_sources": sum(naive(record.get("evidence", [])).effective_sources for record in test)}
    results["methods"]["lineage_aware_evidence"] = {"classification": classification_metrics(actual, lineage_predictions, known_labels=known_authorization_labels), "selective": selective_metrics(actual, lineage_predictions, lineage_abstain), "effective_sources": sum(lineage_aware(record.get("evidence", []), {item.get("lineage_group") for item in record.get("evidence", []) if item.get("lineage_group")}).effective_sources for record in test)}

    train = [record for record in records if record["partition"] == "train"]
    if not test or any("text" not in record or "authorization_label" not in record for record in train + test):
        results["methods"]["text_only_baseline"] = {"status": "not_run", "reason": "reviewed text and authorization labels are required"}
    elif len({record["authorization_label"] for record in train}) < 2:
        results["methods"]["text_only_baseline"] = {"status": "not_run", "reason": "training partition contains fewer than two authorization classes"}
    else:
        model = TextBaseline.train([record["text"] for record in train], [record["authorization_label"] for record in train])
        predictions = [model.predict(record["text"])["label"] for record in test]
        results["methods"]["text_only_baseline"] = {"status": "run", "classification": classification_metrics(actual, predictions, known_labels=known_authorization_labels)}
    return results


def save_results(result: dict, output: str | Path) -> None:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/annotations/pilot.jsonl")
    parser.add_argument("--output", default="artifacts/experiments/pilot_results.json")
    args = parser.parse_args()
    output = run(args.data)
    save_results(output, args.output)
    print(json.dumps(output, indent=2))
