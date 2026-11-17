from collections import Counter, defaultdict
import json
from pathlib import Path

from src.datasets.benchmark_split_v2 import (
    PARTITIONS,
    SOURCE_FILE_HASH_BASELINE,
    SPLIT_SEED,
    _read,
    create_split,
    validate_split,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research-data" / "phase2_v1" / "synthetic" / "synthetic_benchmark_v2"


def _files_hashes(path):
    import hashlib
    return {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(path.iterdir()) if file.is_file()}


def test_split_is_complete_group_safe_and_stratified(tmp_path):
    output = tmp_path / "splits"
    manifest = create_split(SOURCE, output, SPLIT_SEED)
    assert validate_split(SOURCE, output) == []
    assert manifest["partition_counts"] == {"train": 180, "validation": 60, "test": 60}
    assert manifest["class_distribution"] == {
        "train": {"contradicted": 60, "supported": 60, "unresolved": 60},
        "validation": {"contradicted": 20, "supported": 20, "unresolved": 20},
        "test": {"contradicted": 20, "supported": 20, "unresolved": 20},
    }
    assert manifest["component_count"] == 300
    assert manifest["largest_component_size"] == 1
    assert manifest["group_leakage_count"] == 0
    assert manifest["classes_present_in_every_partition"] is True
    assert manifest["scenario_family_intersection_across_all_partitions"] == sorted(json.loads((SOURCE / "manifest.json").read_text()) ["scenario_counts"])


def test_model_inputs_exclude_evaluation_keys_and_metadata(tmp_path):
    output = tmp_path / "splits"
    create_split(SOURCE, output, SPLIT_SEED)
    for part in PARTITIONS:
        inputs = _read(output / f"{part}.jsonl")
        labels = _read(output / f"{part}_labels.jsonl")
        scenarios = _read(output / f"{part}_scenarios.jsonl")
        assert len(inputs) == len(labels) == len(scenarios)
        assert all("input_key" not in row and "case_id" not in row and "scenario" not in row for row in inputs)
        assert all("expected_label" not in row for row in inputs)
        assert all("case_id" in row and "expected_label" in row and "input_key" in row for row in labels)
        assert all("scenario" in row and "vacancy_group" in row for row in scenarios)


def test_scenario_families_overlap_across_splits_and_limit_generalization_claim(tmp_path):
    manifest = create_split(SOURCE, tmp_path / "splits", SPLIT_SEED)
    all_families = set(json.loads((SOURCE / "manifest.json").read_text()) ["scenario_counts"])
    assert manifest["scenario_family_intersection_across_all_partitions"] == sorted(all_families)
    assert "not generalization to unseen families" in manifest["scenario_overlap_interpretation"]


def test_split_reproducible_and_original_v2_hashes_unchanged(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    before = {name: __import__("hashlib").sha256((SOURCE / name).read_bytes()).hexdigest() for name in SOURCE_FILE_HASH_BASELINE}
    assert before == SOURCE_FILE_HASH_BASELINE
    create_split(SOURCE, first, SPLIT_SEED)
    create_split(SOURCE, second, SPLIT_SEED)
    assert _files_hashes(first) == _files_hashes(second)
    after = {name: __import__("hashlib").sha256((SOURCE / name).read_bytes()).hexdigest() for name in SOURCE_FILE_HASH_BASELINE}
    assert after == before


def test_every_vacancy_and_lineage_group_stays_in_one_partition(tmp_path):
    output = tmp_path / "splits"
    create_split(SOURCE, output, SPLIT_SEED)
    owners = defaultdict(set)
    for part in PARTITIONS:
        scenarios = _read(output / f"{part}_scenarios.jsonl")
        for row in scenarios:
            owners["vacancy:" + row["vacancy_group"]].add(part)
        labels = {row["record_ordinal"]: row for row in _read(output / f"{part}_labels.jsonl")}
        inputs = _read(output / f"{part}.jsonl")
        for ordinal, record in enumerate(inputs):
            for evidence in record.get("evidence", []):
                group = evidence.get("lineage_group") or evidence.get("lineage_group_id") or evidence.get("confirmed_lineage_id")
                if group:
                    owners["lineage:" + group].add(part)
    assert all(len(partitions) == 1 for partitions in owners.values())
