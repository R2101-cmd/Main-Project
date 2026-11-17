"""Leakage-safe partitions for synthetic benchmark v2; no evaluation is run here."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SPLIT_SEED = 20261115
PARTITIONS = ("train", "validation", "test")
RATIOS = (0.60, 0.20, 0.20)
LABELS = {"supported", "contradicted", "unresolved"}
SOURCE_FILE_HASH_BASELINE = {
    "model_inputs.jsonl": "a9e99795c5cec94044ab3cfd8ce7d8d57eae82e9ac70cb849831d645b75ea61a",
    "expected_labels.jsonl": "87918ac4044bd169610f632b791397149133561132e4aa27b04dec44d47dc306",
    "scenario_metadata.jsonl": "3dcc9be267fdb84268db08928ccdd8abf6e5999797e1e241f8756ce5267cd32a",
    "manifest.json": "828bcdae3038c6a0de4cc183cea7fe563be9af811223e90dde48d799cbb5dfed",
}
FORBIDDEN_INPUT_FIELDS = {
    "input_key", "case_id", "expected_label", "authorization_label", "scenario",
    "scenario_name", "scenario_slot", "vacancy_group", "vacancy_group_id",
    "evaluation_note", "annotation_rationale", "partition", "split",
}
TOP_LEVEL_GROUP_FIELDS = (
    "vacancy_group", "vacancy_group_id", "canonical_vacancy_id",
    "confirmed_lineage_id", "confirmed_lineage_group_id", "lineage_group", "lineage_group_id",
)
EVIDENCE_GROUP_FIELDS = ("lineage_group", "lineage_group_id", "confirmed_lineage_id", "confirmed_lineage_group_id", "source_url")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict[str, Any]]:
    return [json.loads(row) for row in path.read_text(encoding="utf-8").splitlines() if row.strip()]


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class _UnionFind:
    def __init__(self, values: list[str]):
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def _record_groups(model: dict[str, Any], scenario: dict[str, Any]) -> set[str]:
    groups: set[str] = set()
    for field in TOP_LEVEL_GROUP_FIELDS:
        value = model.get(field, scenario.get(field))
        if isinstance(value, str) and value.strip():
            groups.add("group:" + value.strip())
    vacancy_group = scenario.get("vacancy_group")
    if isinstance(vacancy_group, str) and vacancy_group.strip():
        groups.add("vacancy:" + vacancy_group.strip())
    for evidence in model.get("evidence", []):
        for field in EVIDENCE_GROUP_FIELDS:
            value = evidence.get(field)
            if isinstance(value, str) and value.strip():
                prefix = "source:" if field == "source_url" else "lineage:"
                groups.add(prefix + value.strip())
    return groups


def _components(inputs: list[dict[str, Any]], scenarios_by_key: dict[str, dict[str, Any]]) -> list[list[str]]:
    keys = [row["input_key"] for row in inputs]
    uf = _UnionFind(keys)
    owner: dict[str, str] = {}
    for row in inputs:
        key = row["input_key"]
        metadata = scenarios_by_key[key]
        for group in _record_groups(row, metadata):
            if group in owner:
                uf.union(key, owner[group])
            else:
                owner[group] = key
    result: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        result[uf.find(key)].append(key)
    return [sorted(component) for component in result.values()]


def _quotas(size: int) -> dict[str, int]:
    raw = [size * ratio for ratio in RATIOS]
    base = [int(value) for value in raw]
    remainder = size - sum(base)
    order = sorted(range(len(raw)), key=lambda i: (raw[i] - base[i], -i), reverse=True)
    for index in order[:remainder]:
        base[index] += 1
    return dict(zip(PARTITIONS, base))


def _partition_groups(components: list[list[str]], label_by_key: dict[str, str], scenario_by_key: dict[str, str], seed: int) -> dict[str, str]:
    strata: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
    for component in components:
        labels = {label_by_key[key] for key in component}
        scenarios = {scenario_by_key[key] for key in component}
        if len(labels) != 1:
            raise ValueError(f"linked vacancy/lineage component has conflicting expected classes: {component}")
        if len(scenarios) != 1:
            raise ValueError(f"linked group spans scenario families; cannot stratify safely: {component}")
        strata[(next(iter(labels)), next(iter(scenarios)))].append(component)
    rng = random.Random(seed)
    assignment: dict[str, str] = {}
    for stratum in sorted(strata):
        groups = strata[stratum]
        rng.shuffle(groups)
        quotas = _quotas(sum(len(group) for group in groups))
        current = {partition: 0 for partition in PARTITIONS}
        for group in groups:
            size = len(group)
            candidates = [partition for partition in PARTITIONS if current[partition] < quotas[partition]]
            if not candidates:
                candidates = list(PARTITIONS)
            chosen = max(candidates, key=lambda partition: (quotas[partition] - current[partition], -PARTITIONS.index(partition)))
            for key in group:
                assignment[key] = chosen
            current[chosen] += size
    return assignment


def create_split(source_dir: Path, output_dir: Path, seed: int = SPLIT_SEED) -> dict[str, Any]:
    input_path = source_dir / "model_inputs.jsonl"
    label_path = source_dir / "expected_labels.jsonl"
    scenario_path = source_dir / "scenario_metadata.jsonl"
    benchmark_manifest_path = source_dir / "manifest.json"
    inputs, labels, scenario_rows = _read(input_path), _read(label_path), _read(scenario_path)
    source_manifest = json.loads(benchmark_manifest_path.read_text(encoding="utf-8"))
    observed_source_hashes = {path.name: _sha(path) for path in (input_path, label_path, scenario_path, benchmark_manifest_path)}
    if observed_source_hashes != SOURCE_FILE_HASH_BASELINE:
        raise ValueError("source benchmark v2 hashes differ from the reviewed baseline; refusing to split altered inputs")
    for filename in ("model_inputs.jsonl", "expected_labels.jsonl", "scenario_metadata.jsonl"):
        if source_manifest.get("files_sha256", {}).get(filename) != observed_source_hashes[filename]:
            raise ValueError(f"source benchmark manifest hash mismatch: {filename}")
    input_by_key = {row.get("input_key"): row for row in inputs}
    label_by_key_row = {row.get("input_key"): row for row in labels}
    scenario_by_key_row = {row.get("input_key"): row for row in scenario_rows}
    if None in input_by_key or len(input_by_key) != len(inputs):
        raise ValueError("model inputs have missing or duplicate input keys")
    keys = set(input_by_key)
    if keys != set(label_by_key_row) or keys != set(scenario_by_key_row):
        raise ValueError("input, label, and scenario keys do not map exactly one-to-one")
    if any(row.get("expected_label") not in LABELS for row in labels):
        raise ValueError("invalid expected class in label mapping")
    scenario_by_key = {key: row for key, row in scenario_by_key_row.items()}
    label_by_key = {key: row["expected_label"] for key, row in label_by_key_row.items()}
    scenario_name_by_key = {key: row["scenario"] for key, row in scenario_by_key.items()}
    components = _components(inputs, scenario_by_key)
    assignment = _partition_groups(components, label_by_key, scenario_name_by_key, seed)
    if set(assignment) != keys:
        raise ValueError("partition assignment omitted cases")
    output_dir.mkdir(parents=True, exist_ok=True)
    part_inputs: dict[str, list[dict[str, Any]]] = {part: [] for part in PARTITIONS}
    part_labels: dict[str, list[dict[str, Any]]] = {part: [] for part in PARTITIONS}
    part_scenarios: dict[str, list[dict[str, Any]]] = {part: [] for part in PARTITIONS}
    # Stable input order within each partition; only this evaluation-only mapping carries join IDs.
    for part in PARTITIONS:
        selected = sorted((key for key in keys if assignment[key] == part))
        for ordinal, key in enumerate(selected):
            model_row = dict(input_by_key[key])
            model_row.pop("input_key", None)
            part_inputs[part].append(model_row)
            part_labels[part].append({"record_ordinal": ordinal, **label_by_key_row[key]})
            part_scenarios[part].append({"record_ordinal": ordinal, **scenario_by_key_row[key]})
        _write(output_dir / f"{part}.jsonl", part_inputs[part])
        _write(output_dir / f"{part}_labels.jsonl", part_labels[part])
        _write(output_dir / f"{part}_scenarios.jsonl", part_scenarios[part])
    partition_by_key = assignment
    class_distribution = {
        part: dict(sorted(Counter(row["expected_label"] for row in part_labels[part]).items()))
        for part in PARTITIONS
    }
    scenario_distribution = {
        part: dict(sorted(Counter(row["scenario"] for row in part_scenarios[part]).items()))
        for part in PARTITIONS
    }
    group_partition_sets: dict[str, set[str]] = defaultdict(set)
    for component in components:
        for key in component:
            for group in _record_groups(input_by_key[key], scenario_by_key[key]):
                group_partition_sets[group].add(partition_by_key[key])
    crossing = sorted(group for group, parts in group_partition_sets.items() if len(parts) > 1)
    if crossing:
        raise ValueError(f"leakage groups cross partitions: {crossing[:5]}")
    source_hashes = observed_source_hashes
    manifest = {
        "name": "synthetic_benchmark_v2_group_split_v1",
        "seed": seed,
        "ratios": dict(zip(PARTITIONS, RATIOS)),
        "records_total": len(inputs),
        "partition_counts": {part: len(part_inputs[part]) for part in PARTITIONS},
        "class_distribution": class_distribution,
        "scenario_distribution": scenario_distribution,
        "scenario_families_overlap": {
            part: sorted(set(scenario_distribution[part])) for part in PARTITIONS
        },
        "scenario_family_intersection_across_all_partitions": sorted(set.intersection(*(set(scenario_distribution[p]) for p in PARTITIONS))),
        "scenario_overlap_interpretation": "All scenario families occur in all partitions; test results can measure held-out cases within known scenario families, not generalization to unseen families.",
        "component_count": len(components),
        "largest_component_size": max(map(len, components), default=0),
        "group_leakage_count": len(crossing),
        "classes_present_in_every_partition": all(set(class_distribution[part]) == LABELS for part in PARTITIONS),
        "model_inputs_exclude_input_keys_and_evaluation_metadata": True,
        "evaluation_mappings_are_separate": True,
        "benchmark_source_hashes_sha256": source_hashes,
        "source_benchmark_seed": source_manifest.get("seed"),
        "evaluation_performed": False,
    }
    (output_dir / "split_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "split_methodology.md").write_text(methodology(manifest), encoding="utf-8")
    return manifest


def methodology(manifest: dict[str, Any]) -> str:
    return f"""# Synthetic benchmark v2 split methodology

This package partitions the existing synthetic benchmark without changing its source files. The fixed split seed is `{manifest['seed']}` and target proportions are 60% train, 20% validation, and 20% test. Assignment is deterministic and stratified by the evaluation-only expected class and scenario family, after creating connected components from vacancy identifiers and shared evidence/lineage identifiers. A connected component is assigned wholly to one partition. A component spanning expected classes or scenario families causes generation to stop rather than split related records.

## Field mapping used

- Source model records use `input_key`; it is removed from partition model inputs.
- Evaluation label rows use `input_key`, `case_id`, and `expected_label`.
- Scenario rows use `input_key`, `case_id`, `vacancy_group`, `scenario`, and `scenario_slot`.
- Nested evidence has `lineage_group`, `source_relationship`, `lineage_review_status`, and source URLs. Shared lineage groups and exact repeated source URLs are included in connected-group construction.
- Per-partition evaluation mappings use `record_ordinal` to join rows by file order. Those mappings are not part of the model input files.

## Split counts and scenario overlap

Train: {manifest['partition_counts']['train']} records, classes {manifest['class_distribution']['train']}.

Validation: {manifest['partition_counts']['validation']} records, classes {manifest['class_distribution']['validation']}.

Test: {manifest['partition_counts']['test']} records, classes {manifest['class_distribution']['test']}.

All {len(manifest['scenario_family_intersection_across_all_partitions'])} scenario families occur in every partition. Thus the test partition evaluates held-out cases drawn from known scenario families. It cannot support a claim of generalization to unseen scenario families.

## Leakage and limits

The source contains {manifest['component_count']} connected components; largest size is {manifest['largest_component_size']}. No vacancy or evidence/lineage group crosses partitions. The inputs omit expected labels, case IDs, scenario names, scenario slots, and evaluation-only vacancy grouping fields. Evidence lineage and evidence-state fields remain in inputs because they are part of the information available to an evidence aggregation approach. This is a synthetic split only; it does not establish real-world accuracy or generalization. No A/B/C evaluation or accuracy metric was run while creating this split.
"""


def validate_split(source_dir: Path, split_dir: Path) -> list[str]:
    errors: list[str] = []
    try:
        source_inputs = _read(source_dir / "model_inputs.jsonl")
        source_labels = _read(source_dir / "expected_labels.jsonl")
        source_scenarios = _read(source_dir / "scenario_metadata.jsonl")
        manifest = json.loads((split_dir / "split_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load split package: {exc}"]
    source_keys = {row.get("input_key") for row in source_inputs}
    if len(source_keys) != len(source_inputs) or source_keys != {row.get("input_key") for row in source_labels} or source_keys != {row.get("input_key") for row in source_scenarios}:
        return ["source benchmark mappings are incomplete or duplicated"]
    source_hashes = manifest.get("benchmark_source_hashes_sha256", {})
    for filename in ("model_inputs.jsonl", "expected_labels.jsonl", "scenario_metadata.jsonl", "manifest.json"):
        if source_hashes.get(filename) != _sha(source_dir / filename):
            errors.append(f"source benchmark hash changed or mismatched: {filename}")
        if SOURCE_FILE_HASH_BASELINE.get(filename) != _sha(source_dir / filename):
            errors.append(f"source benchmark v2 differs from reviewed original hash: {filename}")
    label_by_key = {row["input_key"]: row for row in source_labels}
    scenario_by_key = {row["input_key"]: row for row in source_scenarios}
    source_input_by_key = {row["input_key"]: row for row in source_inputs}
    partition_keys: dict[str, list[str]] = {}
    partition_components: dict[str, list[dict[str, Any]]] = {}
    expected_case_ids = {row["case_id"] for row in source_labels}
    scenario_names = {row["scenario"] for row in source_scenarios}
    groups_to_partitions: dict[str, set[str]] = defaultdict(set)
    for part in PARTITIONS:
        try:
            model = _read(split_dir / f"{part}.jsonl")
            labels = _read(split_dir / f"{part}_labels.jsonl")
            scenarios = _read(split_dir / f"{part}_scenarios.jsonl")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot read {part} artifacts: {exc}")
            continue
        if not (len(model) == len(labels) == len(scenarios)):
            errors.append(f"{part}: model and evaluation mapping lengths differ")
            continue
        keys = []
        for ordinal, (model_row, label_row, scenario_row) in enumerate(zip(model, labels, scenarios)):
            if label_row.get("record_ordinal") != ordinal or scenario_row.get("record_ordinal") != ordinal:
                errors.append(f"{part}: invalid record ordinal at {ordinal}")
            key = label_row.get("input_key")
            keys.append(key)
            if key not in source_input_by_key:
                errors.append(f"{part}: unknown input mapping key")
                continue
            if model_row != {k: v for k, v in source_input_by_key[key].items() if k != "input_key"}:
                errors.append(f"{part}: model input differs from source or retains altered fields")
            if label_row.get("expected_label") != label_by_key[key].get("expected_label") or label_row.get("case_id") != label_by_key[key].get("case_id"):
                errors.append(f"{part}: label mapping mismatch")
            if {k: v for k, v in scenario_row.items() if k != "record_ordinal"} != scenario_by_key[key]:
                errors.append(f"{part}: scenario mapping mismatch")
            if FORBIDDEN_INPUT_FIELDS.intersection(model_row):
                errors.append(f"{part}: model row has evaluation-only fields")
            serialized = json.dumps(model_row, ensure_ascii=False).casefold()
            if any(case_id.casefold() in serialized for case_id in expected_case_ids):
                errors.append(f"{part}: model row exposes a case ID")
            if any(name.casefold() in serialized for name in scenario_names):
                errors.append(f"{part}: model row exposes a scenario name")
        partition_keys[part] = keys
        partition_components[part] = model
        if not set(row["expected_label"] for row in labels) == LABELS:
            errors.append(f"{part}: not all expected classes are present")
        class_counts = dict(sorted(Counter(row["expected_label"] for row in labels).items()))
        if manifest.get("class_distribution", {}).get(part) != class_counts:
            errors.append(f"{part}: manifest class distribution mismatch")
        scenario_counts = dict(sorted(Counter(row["scenario"] for row in scenarios).items()))
        if manifest.get("scenario_distribution", {}).get(part) != scenario_counts:
            errors.append(f"{part}: manifest scenario distribution mismatch")
        for key in keys:
            for group in _record_groups(source_input_by_key[key], scenario_by_key[key]):
                groups_to_partitions[group].add(part)
    all_partitioned = [key for keys in partition_keys.values() for key in keys]
    if len(all_partitioned) != len(source_keys) or set(all_partitioned) != source_keys or len(set(all_partitioned)) != len(all_partitioned):
        errors.append("cases are missing, duplicated, or not assigned exactly once")
    crossing = sorted(group for group, parts in groups_to_partitions.items() if len(parts) > 1)
    if crossing:
        errors.append(f"vacancy/evidence lineage groups cross partitions: {crossing[:5]}")
    if manifest.get("group_leakage_count") != len(crossing):
        errors.append("manifest group leakage count mismatch")
    if manifest.get("partition_counts") != {part: len(partition_keys.get(part, [])) for part in PARTITIONS}:
        errors.append("manifest partition counts mismatch")
    if expected_case_ids.intersection(row.get("input_key") for rows in partition_components.values() for row in rows):
        errors.append("a model input contains a case ID in its input_key field")
    return errors

