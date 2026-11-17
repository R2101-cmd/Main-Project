"""Run the reproducible vacancy-authorization comparison and save research artifacts."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.aggregation.rules import lineage_aware, naive
from src.evaluation.metrics import classification_metrics, selective_metrics
from src.evaluation.runner import run
from src.ml.text_classifier import TextBaseline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/annotations/job_ad_independent_review_v1.jsonl")
    parser.add_argument("--output-dir", default="artifacts/experiments/research_v1")
    args = parser.parse_args()
    data_path = Path(args.data)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    aggregate = run(data_path)
    test = [record for record in records if record.get("partition") == "test"]
    train = [record for record in records if record.get("partition") == "train"]

    text_model = None
    if len({record.get("authorization_label") for record in train}) >= 2:
        text_model = TextBaseline.train([record["text"] for record in train], [record["authorization_label"] for record in train], seed=42)

    predictions = []
    for record in test:
        evidence = record.get("evidence", [])
        naive_result = naive(evidence)
        lineage_result = lineage_aware(evidence, {item.get("lineage_group") for item in evidence if item.get("lineage_group")})
        text_prediction = text_model.predict(record["text"])["label"] if text_model else None
        predictions.append({
            "id": record["id"],
            "vacancy_group": record["vacancy_group"],
            "reference_label": record["authorization_label"],
            "e4_naive_prediction": naive_result.state,
            "e5_lineage_aware_prediction": lineage_result.state,
            "e4_effective_sources": naive_result.effective_sources,
            "e5_effective_sources": lineage_result.effective_sources,
            "source_consolidated": naive_result.effective_sources != lineage_result.effective_sources,
            "prediction_changed": naive_result.state != lineage_result.state,
            "e4_false_assurance": naive_result.state == "supported" and record["authorization_label"] != "supported",
            "e5_false_assurance": lineage_result.state == "supported" and record["authorization_label"] != "supported",
            "text_prediction": text_prediction,
            "evidence_sufficient": bool(evidence),
            "evidence_ids": [item.get("id") for item in evidence],
            "lineage_groups": sorted({item.get("lineage_group") for item in evidence if item.get("lineage_group")}),
        })

    e4_changes = {"agree": 0, "e4_wrong_e5_correct": 0, "e4_correct_e5_wrong": 0, "both_wrong": 0, "e5_definitive_to_unresolved": 0, "e5_unresolved_to_definitive": 0}
    for item in predictions:
        e4, e5, ref = item["e4_naive_prediction"], item["e5_lineage_aware_prediction"], item["reference_label"]
        if e4 == e5:
            e4_changes["agree"] += 1
        elif e4 != ref and e5 == ref:
            e4_changes["e4_wrong_e5_correct"] += 1
        elif e4 == ref and e5 != ref:
            e4_changes["e4_correct_e5_wrong"] += 1
        else:
            e4_changes["both_wrong"] += 1
        if e4 != "unresolved" and e5 == "unresolved":
            e4_changes["e5_definitive_to_unresolved"] += 1
        if e4 == "unresolved" and e5 != "unresolved":
            e4_changes["e5_unresolved_to_definitive"] += 1

    split_manifest = [{"id": r["id"], "vacancy_group": r["vacancy_group"], "partition": r["partition"], "lineage_groups": sorted({item.get("lineage_group") for item in r.get("evidence", []) if item.get("lineage_group")})} for r in records]
    config = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": 42,
        "dataset": str(data_path),
        "methods": {"E1": "TF-IDF word unigrams/bigrams + LogisticRegression", "E2": "not run: structured training features not present in JSONL", "E3": "not run: employer-context reference labels not available", "E4": "naive evidence aggregation", "E5": "lineage-aware evidence aggregation"},
        "ground_truth_status": "single-reviewer provisional; human confirmation and adjudication pending",
    }
    aggregate["research_validity"] = "provisional_not_independent_ground_truth"
    aggregate["case_comparison"] = e4_changes
    aggregate["methods_available"] = ["E1", "E4", "E5"]
    aggregate["methods_not_run"] = {"E2": "structured metadata baseline not implemented for this benchmark format", "E3": "employer-context labels/features not independently available"}
    aggregate["false_assurance"] = {"E4_count": sum(item["e4_false_assurance"] for item in predictions), "E5_count": sum(item["e5_false_assurance"] for item in predictions), "denominator_non_supported": sum(item["reference_label"] != "supported" for item in predictions)}

    (output_dir / "aggregate_metrics.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    (output_dir / "predictions.jsonl").write_text("\n".join(json.dumps(item, separators=(",", ":")) for item in predictions) + "\n", encoding="utf-8")
    (output_dir / "split_manifest.json").write_text(json.dumps(split_manifest, indent=2), encoding="utf-8")
    (output_dir / "experiment_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "records": len(records), "test_records": len(test), "case_comparison": e4_changes, "research_validity": aggregate["research_validity"]}, indent=2))


if __name__ == "__main__":
    main()
