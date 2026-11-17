"""Read-only validation for the Phase 2 research-data tables.

The validator reports errors and review flags; it never writes, relabels, merges,
or changes any input file. Missing collection tables are reported as pre-collection
empty inputs rather than being filled with placeholder records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


AUTHORIZATION_LABELS = {"supported", "contradicted", "unresolved"}
IDENTITY_LABELS = {"verified", "contradicted", "unresolved"}
EVIDENCE_STATES = {"supported", "contradicted", "unverified", "unavailable"}
RELATIONSHIPS = {"original", "independent", "copied_derived", "unknown"}
PARTITIONS = {"train", "validation", "test"}
PLACEHOLDER_RE = re.compile(r"placeholder|pending|unknown|to[_ -]?assign|codex|reviewer[_ -]?id", re.I)


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], [f"not created yet: {path.as_posix()}"]
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.as_posix()}:{line_number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path.as_posix()}:{line_number}: record must be an object")
            continue
        records.append(value)
    return records, errors


def strict_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def duplicate_values(records: list[dict[str, Any]], field: str) -> list[str]:
    seen: dict[str, int] = defaultdict(int)
    for record in records:
        value = record.get(field)
        if value:
            seen[str(value)] += 1
    return sorted(value for value, count in seen.items() if count > 1)


def validate(advertisements: list[dict[str, Any]], evidence: list[dict[str, Any]], annotations: list[dict[str, Any]], lineages: list[dict[str, Any]], adjudications: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    flags: list[str] = []
    ad_by_id: dict[str, dict[str, Any]] = {}
    evidence_by_id: dict[str, dict[str, Any]] = {}
    annotation_by_id: dict[str, dict[str, Any]] = {}

    for index, record in enumerate(advertisements):
        identifier = record.get("advertisement_id")
        if not identifier:
            errors.append(f"advertisement {index}: missing advertisement_id")
        elif identifier in ad_by_id:
            errors.append(f"duplicate advertisement_id: {identifier}")
        else:
            ad_by_id[identifier] = record
        if not record.get("vacancy_group_id"):
            errors.append(f"advertisement {identifier or index}: missing vacancy_group_id")
        if not strict_datetime(record.get("observed_at")):
            errors.append(f"advertisement {identifier or index}: observed_at must be timezone-aware ISO-8601")
        if not isinstance(record.get("missing_data_notes"), list):
            errors.append(f"advertisement {identifier or index}: missing_data_notes must be a list")
        partition = record.get("evaluation_partition")
        if partition is not None and partition not in PARTITIONS:
            errors.append(f"advertisement {identifier or index}: invalid evaluation_partition")

    for index, item in enumerate(evidence):
        identifier = item.get("evidence_id")
        if not identifier:
            errors.append(f"evidence {index}: missing evidence_id")
        elif identifier in evidence_by_id:
            errors.append(f"duplicate evidence_id: {identifier}")
        else:
            evidence_by_id[identifier] = item
        ad_id = item.get("advertisement_id")
        ad = ad_by_id.get(ad_id)
        if ad is None:
            errors.append(f"evidence {identifier or index}: references unknown advertisement_id {ad_id}")
        elif item.get("vacancy_group_id") != ad.get("vacancy_group_id"):
            errors.append(f"evidence {identifier or index}: vacancy_group_id does not match advertisement")
        if item.get("evidence_status") not in EVIDENCE_STATES:
            errors.append(f"evidence {identifier or index}: invalid evidence_status")
        if item.get("retrieval_status") == "available" and not strict_datetime(item.get("retrieved_at")):
            errors.append(f"evidence {identifier or index}: available evidence requires timezone-aware retrieved_at")
        if item.get("retrieval_status") in {"failed", "blocked", "unavailable", "empty"} and not item.get("rationale"):
            errors.append(f"evidence {identifier or index}: unavailable retrieval requires a rationale")
        if not isinstance(item.get("matched_fields"), list) or not isinstance(item.get("contradicted_fields"), list):
            errors.append(f"evidence {identifier or index}: matched_fields and contradicted_fields must be lists")
        if item.get("source_relationship") == "copied_derived" and not item.get("lineage_group_id"):
            errors.append(f"evidence {identifier or index}: copied_derived evidence requires lineage_group_id")
        if item.get("source_relationship") == "unknown" and item.get("lineage_review_status") in {"reviewed", "adjudicated"}:
            flags.append(f"evidence {identifier or index}: unknown relationship is marked as reviewed; inspect rationale")

    source_keys: set[tuple[str, str]] = set()
    for item in evidence:
        key = (str(item.get("advertisement_id")), str(item.get("source_url")))
        if key in source_keys and item.get("source_url"):
            flags.append(f"possible duplicate evidence source for advertisement {key[0]}: {key[1]}")
        source_keys.add(key)

    for index, annotation in enumerate(annotations):
        identifier = annotation.get("annotation_id")
        if not identifier:
            errors.append(f"annotation {index}: missing annotation_id")
        elif identifier in annotation_by_id:
            errors.append(f"duplicate annotation_id: {identifier}")
        else:
            annotation_by_id[identifier] = annotation
        ad = ad_by_id.get(annotation.get("advertisement_id"))
        if ad is None:
            errors.append(f"annotation {identifier or index}: references unknown advertisement_id")
        elif annotation.get("vacancy_group_id") != ad.get("vacancy_group_id"):
            errors.append(f"annotation {identifier or index}: vacancy_group_id does not match advertisement")
        if annotation.get("employer_identity_label") not in IDENTITY_LABELS:
            errors.append(f"annotation {identifier or index}: invalid employer_identity_label")
        if annotation.get("vacancy_authorization_label") not in AUTHORIZATION_LABELS:
            errors.append(f"annotation {identifier or index}: invalid vacancy_authorization_label")
        reviewer = str(annotation.get("reviewer_id") or "")
        if not reviewer or PLACEHOLDER_RE.search(reviewer):
            errors.append(f"annotation {identifier or index}: reviewer_id is missing or appears to be a placeholder")
        if not strict_datetime(annotation.get("annotated_at")):
            errors.append(f"annotation {identifier or index}: annotated_at must be timezone-aware ISO-8601")
        for evidence_id in annotation.get("evidence_ids", []):
            if evidence_id not in evidence_by_id:
                errors.append(f"annotation {identifier or index}: unknown evidence_id {evidence_id}")

    for index, review in enumerate(lineages):
        identifier = review.get("lineage_review_id") or index
        ids = review.get("advertisement_ids")
        if not isinstance(ids, list) or len(ids) < 2 or len(set(ids)) != len(ids):
            errors.append(f"lineage review {identifier}: requires at least two distinct advertisement_ids")
        else:
            missing = [ad_id for ad_id in ids if ad_id not in ad_by_id]
            if missing:
                errors.append(f"lineage review {identifier}: unknown advertisements {missing}")
            groups = {ad_by_id[ad_id].get("vacancy_group_id") for ad_id in ids if ad_id in ad_by_id}
            if len(groups) > 1:
                errors.append(f"lineage review {identifier}: advertisements have different vacancy_group_id values")
        if review.get("relationship") not in RELATIONSHIPS:
            errors.append(f"lineage review {identifier}: invalid relationship")
        if not strict_datetime(review.get("reviewed_at")):
            errors.append(f"lineage review {identifier}: reviewed_at must be timezone-aware ISO-8601")
        reviewer = str(review.get("reviewer_id") or "")
        if not reviewer or PLACEHOLDER_RE.search(reviewer):
            errors.append(f"lineage review {identifier}: reviewer_id is missing or appears to be a placeholder")

    for index, adjudication in enumerate(adjudications):
        identifier = adjudication.get("adjudication_id") or index
        refs = adjudication.get("original_annotation_ids")
        if not isinstance(refs, list) or len(refs) < 2 or len(set(refs)) != len(refs):
            errors.append(f"adjudication {identifier}: requires at least two distinct original_annotation_ids")
        else:
            missing = [ref for ref in refs if ref not in annotation_by_id]
            if missing:
                errors.append(f"adjudication {identifier}: unknown annotations {missing}")
        fingerprints = adjudication.get("original_annotation_fingerprints")
        if not isinstance(fingerprints, dict) or any(not re.fullmatch(r"[a-f0-9]{64}", str(fingerprints.get(ref, ""))) for ref in refs or []):
            errors.append(f"adjudication {identifier}: original annotation fingerprints are incomplete or invalid")
        if adjudication.get("vacancy_authorization_label") not in AUTHORIZATION_LABELS:
            errors.append(f"adjudication {identifier}: invalid vacancy_authorization_label")
        if not strict_datetime(adjudication.get("adjudicated_at")):
            errors.append(f"adjudication {identifier}: adjudicated_at must be timezone-aware ISO-8601")

    partition_groups: dict[str, set[str]] = defaultdict(set)
    for record in advertisements:
        if record.get("evaluation_partition"):
            partition_groups[record.get("vacancy_group_id")].add(record["evaluation_partition"])
    for group, partitions in partition_groups.items():
        if len(partitions) > 1:
            errors.append(f"vacancy group crosses evaluation partitions: {group}")
    lineage_partitions: dict[str, set[str]] = defaultdict(set)
    for item in evidence:
        ad = ad_by_id.get(item.get("advertisement_id"))
        if ad and item.get("lineage_group_id") and ad.get("evaluation_partition"):
            lineage_partitions[item["lineage_group_id"]].add(ad["evaluation_partition"])
    for group, partitions in lineage_partitions.items():
        if len(partitions) > 1:
            errors.append(f"lineage group crosses evaluation partitions: {group}")

    return {
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "review_flags": flags,
        "counts": {
            "advertisements": len(advertisements),
            "evidence": len(evidence),
            "annotations": len(annotations),
            "lineage_reviews": len(lineages),
            "adjudications": len(adjudications),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Phase 2 records without writing files.")
    parser.add_argument("--root", default="research-data/phase2_v1")
    args = parser.parse_args()
    root = Path(args.root)
    paths = {
        "advertisements": root / "advertisements_v1.jsonl",
        "evidence": root / "evidence_v1.jsonl",
        "annotations": root / "independent_annotations_v1.jsonl",
        "lineages": root / "lineage_reviews_v1.jsonl",
        "adjudications": root / "adjudications_v1.jsonl",
    }
    loaded = {}
    load_errors: list[str] = []
    for name, path in paths.items():
        loaded[name], errors = load_jsonl(path)
        load_errors.extend(errors)
    result = validate(loaded["advertisements"], loaded["evidence"], loaded["annotations"], loaded["lineages"], loaded["adjudications"])
    result["pre_collection"] = not any(loaded.values())
    result["input_errors"] = load_errors
    if result["pre_collection"]:
        result["status"] = "empty_precollection_workflow"
    elif load_errors:
        result["status"] = "invalid_inputs"
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
