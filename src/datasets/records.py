import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

VALID_AUTHORIZATION = {"supported", "contradicted", "unresolved"}
VALID_IDENTITY = {"verified", "contradicted", "unresolved"}
VALID_FRAUD = {"confirmed_fraudulent", "confirmed_legitimate", "unresolved"}


def load_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if source.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    if source.suffix.lower() == ".json":
        data = json.loads(source.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError("supported dataset formats are CSV, JSON, and JSONL")


def validate_record(record: dict[str, Any]) -> list[str]:
    errors = []
    if not record.get("record_id") and not record.get("id") and not record.get("job_id"):
        errors.append("missing stable record identifier")
    if "authorization_label" in record and record["authorization_label"] not in VALID_AUTHORIZATION:
        errors.append("invalid authorization_label")
    if "employer_identity" in record and record["employer_identity"] not in VALID_IDENTITY:
        errors.append("invalid employer_identity")
    if "fraud_outcome" in record and record["fraud_outcome"] not in VALID_FRAUD:
        errors.append("invalid fraud_outcome")
    return errors


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    validation_errors = [error for record in records for error in validate_record(record)]
    auth = Counter(record.get("authorization_label") for record in records if record.get("authorization_label"))
    identity = Counter(record.get("employer_identity") for record in records if record.get("employer_identity"))
    fraud = Counter(record.get("fraud_outcome") for record in records if record.get("fraud_outcome"))
    reviewed = sum(record.get("annotation_status") not in {None, "unreviewed_import"} and record.get("authorization_label") != "unresolved" for record in records)
    return {"total": len(records), "reviewed_cases": reviewed, "authorization_distribution": dict(auth), "employer_identity_distribution": dict(identity), "fraud_outcome_distribution": dict(fraud), "records_with_evidence": sum(bool(record.get("evidence")) for record in records), "validation_error_count": len(validation_errors), "validation_errors": validation_errors[:20]}


def export_jsonl(records: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + ("\n" if records else "")
