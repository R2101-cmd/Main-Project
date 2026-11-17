VALID_EVIDENCE = {"supported", "contradicted", "unverified", "unavailable"}
VALID_RELATIONSHIPS = {"original", "independent", "copied_derived", "unknown"}
VALID_PARTITIONS = {"train", "validation", "test"}

def validate_records(records: list[dict]) -> list[str]:
    errors = []
    for index, record in enumerate(records):
        if not record.get("id"):
            errors.append(f"record {index}: missing id")
        if record.get("evidence_state") not in VALID_EVIDENCE:
            errors.append(f"record {index}: invalid evidence_state")
    return errors

def detect_lineage_leakage(records: list[dict]) -> list[str]:
    groups: dict[str, set[str]] = {}
    for record in records:
        partition = record.get("partition")
        lineage_groups = record.get("lineage_groups")
        if lineage_groups is None:
            lineage_groups = [record.get("lineage_group")]
        for group in lineage_groups:
            if group and partition:
                groups.setdefault(group, set()).add(partition)
    return [group for group, partitions in groups.items() if len(partitions) > 1]


def validate_evaluation_record(record: dict) -> list[str]:
    errors = []
    if not record.get("id"):
        errors.append("missing id")
    if record.get("partition") not in VALID_PARTITIONS:
        errors.append("invalid or missing partition")
    if not record.get("vacancy_group"):
        errors.append("missing vacancy_group")
    if record.get("authorization_label") not in {"supported", "contradicted", "unresolved"}:
        errors.append("invalid or missing authorization_label")
    if not isinstance(record.get("evidence", []), list):
        errors.append("evidence must be a list")
    for index, evidence in enumerate(record.get("evidence", [])):
        if evidence.get("evidence_state") not in VALID_EVIDENCE:
            errors.append(f"evidence {index}: invalid evidence_state")
        if not evidence.get("id"):
            errors.append(f"evidence {index}: missing id")
    return errors


def validate_evaluation_records(records: list[dict]) -> list[str]:
    errors = []
    seen = set()
    for index, record in enumerate(records):
        record_errors = validate_evaluation_record(record)
        errors.extend(f"record {index}: {error}" for error in record_errors)
        if record.get("id") in seen:
            errors.append(f"record {index}: duplicate id {record.get('id')}")
        seen.add(record.get("id"))
    lineage_rows = []
    for record in records:
        groups = {item.get("lineage_group") for item in record.get("evidence", []) if item.get("lineage_group")}
        lineage_rows.extend({"lineage_group": group, "partition": record.get("partition")} for group in groups)
    errors.extend(f"lineage group crosses partitions: {group}" for group in detect_lineage_leakage(records + lineage_rows))
    return errors


def validate_split_manifest(manifest: list[dict]) -> list[str]:
    """Validate a persisted group-aware split manifest."""
    errors = []
    seen_ids: set[str] = set()
    for index, row in enumerate(manifest):
        record_id = row.get("id")
        if not record_id:
            errors.append(f"manifest row {index}: missing id")
        elif record_id in seen_ids:
            errors.append(f"manifest row {index}: duplicate id {record_id}")
        seen_ids.add(record_id)
        if not row.get("vacancy_group"):
            errors.append(f"manifest row {index}: missing vacancy_group")
        if row.get("partition") not in VALID_PARTITIONS:
            errors.append(f"manifest row {index}: invalid partition")
    errors.extend(f"manifest group crosses partitions: {group}" for group in detect_lineage_leakage(manifest))
    return errors


def frozen_test_id_differences(current_manifest: list[dict], frozen_manifest: list[dict]) -> dict[str, list[str]]:
    """Return test-ID, partition, and group changes against a frozen manifest."""
    current = {row.get("id") for row in current_manifest if row.get("partition") == "test"}
    frozen = {row.get("id") for row in frozen_manifest if row.get("partition") == "test"}
    current_by_id = {row.get("id"): row for row in current_manifest}
    frozen_by_id = {row.get("id"): row for row in frozen_manifest}
    common = current & frozen
    return {
        "added": sorted(current - frozen),
        "removed": sorted(frozen - current),
        "group_changed": sorted(record_id for record_id in common if current_by_id[record_id].get("vacancy_group") != frozen_by_id[record_id].get("vacancy_group")),
        "partition_changed": sorted(record_id for record_id in common if current_by_id[record_id].get("partition") != frozen_by_id[record_id].get("partition")),
    }
