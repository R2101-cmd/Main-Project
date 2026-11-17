"""Read-only loader for the versioned research staging CSVs."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from typing import Any
from src.evidence.representation import COLLECTION_STATE_MAP, convert_collection_evidence

REQUIRED_COLUMNS = {
    "case_id", "employer_id", "job_title", "job_description", "location",
    "application_url", "advertisement_url", "platform_type", "cohort_id",
    "source_family_id", "source_instance_id", "retrieval_event_id",
    "source_url", "official_employer_url", "canonical_vacancy_id",
    "retrieved_at", "response_hash", "evidence_state", "source_independence",
    "lineage_candidate_id", "confirmed_lineage_id",
}
ALLOWED_EVIDENCE_STATES = {"supported", "contradicted", "unverified", "unavailable", "unresolved", "snapshot_match_only", "independently_supported", "independently_contradicted", "independently_unresolved", "not_comparable", "inaccessible"}
ALLOWED_INDEPENDENCE = {"independent", "dependent", "unknown", "not_available"}


@dataclass(frozen=True)
class StagingLoad:
    path: str
    rows: tuple[dict[str, Any], ...]
    summary: dict[str, Any]


def _value(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def _is_naukri(row: dict[str, Any]) -> bool:
    haystack = " ".join(str(row.get(key) or "") for key in ("platform_type", "source_family_id", "source_url", "advertisement_url", "application_url"))
    return "naukri" in haystack.lower()


def _valid_http_url(value: str | None) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_evidence_state(value: str | None) -> str:
    mapped = COLLECTION_STATE_MAP.get(value or "")
    if mapped in ALLOWED_EVIDENCE_STATES:
        return mapped
    if value in ALLOWED_EVIDENCE_STATES:
        return value or "unresolved"
    return "unresolved"


def _normalize_independence(value: str | None) -> str:
    if value in ALLOWED_INDEPENDENCE:
        return value or "unknown"
    if value and ("separate_employer_controlled" in value or value == "independent"):
        return "independent"
    return "unknown"


def load_staging_csv(path: str | Path, *, cohort: str | None = None, include_naukri: bool = False) -> StagingLoad:
    """Load staging rows without writing, labeling, or importing them."""
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_COLUMNS - columns)
        if missing_columns:
            raise ValueError(f"staging CSV is missing required columns: {', '.join(missing_columns)}")
        raw_rows = [dict(row) for row in reader]

    errors: list[str] = []
    seen_cases: set[str] = set()
    seen_events: set[str] = set()
    normalized: list[dict[str, Any]] = []
    excluded_naukri = excluded_cohort = 0
    for index, raw in enumerate(raw_rows, start=2):
        row = {key: _value(value) for key, value in raw.items()}
        case_id = row.get("case_id")
        if not case_id:
            errors.append(f"row {index}: missing case_id")
            continue
        if case_id in seen_cases:
            errors.append(f"row {index}: duplicate case_id {case_id}")
            continue
        seen_cases.add(case_id)
        event_id = row.get("retrieval_event_id")
        if event_id and event_id in seen_events:
            errors.append(f"row {index}: duplicate retrieval_event_id {event_id}")
        if event_id:
            seen_events.add(event_id)
        if not row.get("evidence_state"):
            errors.append(f"row {index}: missing evidence_state")
        if not row.get("source_independence"):
            errors.append(f"row {index}: missing source_independence")
        for field in ("source_url", "official_employer_url", "application_url", "advertisement_url"):
            if not _valid_http_url(row.get(field)):
                errors.append(f"row {index}: invalid {field}")
        if cohort and row.get("cohort_id") != cohort:
            excluded_cohort += 1
            continue
        if not include_naukri and _is_naukri(row):
            excluded_naukri += 1
            continue
        normalized.append({
            "case_id": case_id, "cohort_id": row.get("cohort_id"), "employer_id": row.get("employer_id"),
            "title": row.get("job_title"), "description": row.get("job_description"), "location": row.get("location"),
            "evidence_state": _normalize_evidence_state(row.get("evidence_state")),
            "source_independence": _normalize_independence(row.get("source_independence")),
            "lineage": {"candidate_id": row.get("lineage_candidate_id"), "confirmed_id": row.get("confirmed_lineage_id"), "status": "confirmed" if row.get("confirmed_lineage_id") else ("candidate" if row.get("lineage_candidate_id") else "none")},
            "provenance": {key: row.get(key) for key in ("source_family_id", "source_instance_id", "retrieval_event_id", "source_url", "official_employer_url", "canonical_vacancy_id", "retrieved_at", "response_hash")},
            "live_evidence_conversion": convert_collection_evidence(row),
            "raw": raw,
        })
    if errors:
        raise ValueError("invalid staging CSV: " + "; ".join(errors[:10]))
    summary = {
        "input_rows": len(raw_rows), "loaded_rows": len(normalized), "excluded_naukri": excluded_naukri, "excluded_cohort": excluded_cohort,
        "cohorts": dict(Counter(row["cohort_id"] for row in normalized)), "employers": dict(Counter(row["employer_id"] for row in normalized)),
        "source_families": dict(Counter(row["provenance"]["source_family_id"] for row in normalized)), "evidence_states": dict(Counter(row["evidence_state"] for row in normalized)),
        "candidate_lineage_rows": sum(row["lineage"]["status"] == "candidate" for row in normalized), "confirmed_lineage_rows": sum(row["lineage"]["status"] == "confirmed" for row in normalized),
        "read_only": True, "supervised_labels_assigned": False,
    }
    return StagingLoad(str(source), tuple(normalized), summary)
