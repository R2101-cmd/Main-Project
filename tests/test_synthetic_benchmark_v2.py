import json
from collections import Counter
from pathlib import Path

from src.datasets.synthetic_benchmark_v2 import (
    SEED,
    build_package,
    load_jsonl,
    package_hashes,
    validate_package,
)


def test_v2_balanced_unique_and_mapped_without_label_leakage(tmp_path):
    build_package(tmp_path, SEED)
    assert validate_package(tmp_path) == []
    inputs = load_jsonl(tmp_path / "model_inputs.jsonl")
    labels = load_jsonl(tmp_path / "expected_labels.jsonl")
    scenarios = load_jsonl(tmp_path / "scenario_metadata.jsonl")
    assert len(inputs) == 300
    assert len({row["input_key"] for row in inputs}) == 300
    assert Counter(row["expected_label"] for row in labels) == {"supported": 100, "contradicted": 100, "unresolved": 100}
    assert len({row["case_id"] for row in labels}) == 300
    assert {row["input_key"] for row in inputs} == {row["input_key"] for row in labels} == {row["input_key"] for row in scenarios}
    for item in inputs:
        assert not {"case_id", "scenario", "expected_label", "authorization_label"}.intersection(item)
        assert item["synthetic"] is True
        assert item["advertisement"]["text"]


def test_v2_scenario_coverage_and_lineage_vocab(tmp_path):
    build_package(tmp_path, SEED)
    inputs = load_jsonl(tmp_path / "model_inputs.jsonl")
    scenarios = load_jsonl(tmp_path / "scenario_metadata.jsonl")
    counts = Counter(row["scenario"] for row in scenarios)
    assert len(counts) == 15
    assert set(counts.values()) == {20}
    assert {"supported_claim_unknown_lineage", "supported_claim_missing_lineage", "stale_or_unavailable_sources", "copied_claims_with_official_rejection"}.issubset(counts)
    allowed_states = {"supported", "contradicted", "unverified", "unavailable"}
    allowed_relationships = {"original", "independent", "copied_derived", "unknown"}
    for record in inputs:
        for evidence in record["evidence"]:
            assert evidence["evidence_state"] in allowed_states
            assert evidence.get("source_relationship") in allowed_relationships | {None}


def test_v2_reproducible_files_and_tamper_detection(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    build_package(first, SEED)
    build_package(second, SEED)
    assert package_hashes(first) == package_hashes(second)
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == SEED
    assert manifest["evaluation_performed"] is False
    with (first / "model_inputs.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    assert any("hash mismatch" in error for error in validate_package(first))
