VALID_EVIDENCE = {"supported", "contradicted", "unverified", "unavailable"}
VALID_RELATIONSHIPS = {"original", "independent", "copied_derived", "unknown"}

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
        group = record.get("lineage_group")
        partition = record.get("partition")
        if group and partition:
            groups.setdefault(group, set()).add(partition)
    return [group for group, partitions in groups.items() if len(partitions) > 1]
