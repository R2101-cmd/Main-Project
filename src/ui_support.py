"""Pure helpers for presenting backend review records in the Streamlit UI.

These helpers deliberately format only values present in the evidence records. They
do not infer legitimacy, confidence, or missing source facts.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


AVAILABLE_RETRIEVAL_STATUSES = {"available", "available_at_observation"}
RELEVANT_EVIDENCE_STATES = {"supported", "contradicted", "unverified"}


def safe_value(value: Any, fallback: str = "Not available") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def retrieval_label(item: dict[str, Any]) -> str:
    status = str(item.get("retrieval_status") or "unknown").lower()
    evidence_state = str(item.get("evidence_state") or "unavailable").lower()
    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    if status in AVAILABLE_RETRIEVAL_STATUSES:
        if evidence_state == "unavailable":
            extraction_status = str(details.get("extraction_status") or "").lower()
            if extraction_status in {"no_usable_content", "empty", "failed"}:
                return "Retrieved, no usable content"
            return "Retrieved, no relevant evidence"
        if evidence_state == "unverified" and details.get("vacancy_match") is False:
            return "Retrieved, no relevant evidence"
        return "Retrieved successfully"
    if status in {"failed", "unavailable"}:
        return "Retrieval failed or unavailable"
    return status.replace("_", " ").title()


def _details(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("details")
    return value if isinstance(value, dict) else {}


def evidence_stats(evidence: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = [item for item in evidence if isinstance(item, dict)]
    states = {state: sum(str(item.get("evidence_state") or "unavailable") == state for item in items) for state in ("supported", "contradicted", "unverified", "unavailable")}
    retrieved = sum(str(item.get("retrieval_status") or "") in AVAILABLE_RETRIEVAL_STATUSES for item in items)
    retrieval_failures = sum(str(item.get("retrieval_status") or "") not in AVAILABLE_RETRIEVAL_STATUSES for item in items)
    relevant = sum(
        str(item.get("evidence_state") or "") in RELEVANT_EVIDENCE_STATES
        and str(item.get("retrieval_status") or "") in AVAILABLE_RETRIEVAL_STATUSES
        for item in items
    )
    return {
        "total_source_records": len(items),
        "successfully_retrieved": retrieved,
        "relevant_evidence_sources": relevant,
        "supporting_items": states["supported"],
        "contradicting_items": states["contradicted"],
        "unverified_items": states["unverified"],
        "unavailable_items": states["unavailable"],
        "retrieval_failures": retrieval_failures,
        "availability_denominator": len(items),
        "availability_coverage": retrieved / len(items) if items else 0.0,
    }


def _field_list(details: dict[str, Any], key: str) -> list[str]:
    value = details.get(key)
    if isinstance(value, dict):
        return [str(field) for field, matched in value.items() if matched is True]
    if isinstance(value, (list, tuple, set)):
        return [str(field) for field in value if field]
    return []


def evidence_ledger_rows(evidence: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        details = _details(item)
        matched = _field_list(details, "matched_fields")
        contradicted = _field_list(details, "contradicted_fields")
        rows.append(
            {
                "Source": safe_value(item.get("source_url")),
                "Source type": safe_value(item.get("source_type")),
                "Source family": safe_value(item.get("source_family"), "Unknown"),
                "Retrieval status": retrieval_label(item),
                "Evidence status": safe_value(item.get("evidence_state"), "Unknown").title(),
                "Matched fields": ", ".join(matched) or "None recorded",
                "Contradicted fields": ", ".join(contradicted) or "None recorded",
                "Source timestamp": safe_value(item.get("observed_at")),
                "Lineage group": safe_value(item.get("lineage_group") or details.get("lineage_group"), "Unknown lineage"),
                "Relationship": safe_value(item.get("source_relationship"), "unknown"),
                "Lineage review": safe_value(item.get("lineage_review_status"), "not_assessed"),
                "Evidence rationale": safe_value(item.get("rationale"), "No rationale recorded."),
            }
        )
    return rows


def _comparison_state(field: str, matched: Any, evidence_state: str, advertised: Any, observed: Any, contradicted_fields: set[str]) -> str:
    if matched is True:
        return "Matched"
    if field in contradicted_fields or (evidence_state == "contradicted" and field == "title"):
        return "Contradicted"
    if advertised in (None, "") or observed in (None, ""):
        return "Not comparable"
    return "Unknown"


def comparison_rows(advertisement: Any, evidence: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ad_values = advertisement.to_dict() if hasattr(advertisement, "to_dict") else advertisement if isinstance(advertisement, dict) else {}
    rows = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        details = _details(item)
        matches = details.get("field_matches") if isinstance(details.get("field_matches"), dict) else {}
        field_comparisons = details.get("field_comparisons") if isinstance(details.get("field_comparisons"), dict) else {}
        advertised_values = details.get("advertised_values") if isinstance(details.get("advertised_values"), dict) else ad_values
        observed_values = details.get("evidence_values") if isinstance(details.get("evidence_values"), dict) else {}
        contradicted_fields = set(_field_list(details, "contradicted_fields"))
        display_fields = {
            "job_title": "Job title", "employer_identity": "Employer identity", "job_description": "Job description",
            "job_id": "Requisition/job ID", "location": "Location", "employment_type": "Employment type",
            "salary": "Salary", "application_url": "Application URL", "posting_date": "Posting date",
            "recruiter_contact": "Recruiter/contact",
        }
        for key, label in display_fields.items():
            comparison = field_comparisons.get(key) if isinstance(field_comparisons.get(key), dict) else {}
            legacy_key = {"job_title": "title", "employer_identity": "employer"}.get(key, key)
            advertised = comparison.get("advertised", advertised_values.get(legacy_key, ad_values.get(key)))
            observed = comparison.get("observed", observed_values.get(legacy_key, observed_values.get(key)))
            if not comparison and key not in matches and advertised in (None, "") and observed in (None, ""):
                continue
            raw_state = str(comparison.get("status") or "").lower()
            if comparison.get("matched") is True or raw_state in {"exact_match", "similar_match"}:
                state = "Matched"
            elif key in set(_field_list(details, "contradicted_fields_all")) or legacy_key in set(_field_list(details, "contradicted_fields")) or (str(item.get("evidence_state") or "") == "contradicted" and key in {"job_title", "job_id", "application_url", "employer_identity"}):
                state = "Contradicted"
            elif raw_state in {"conflict", "mismatch"}:
                state = "Conflict"
            elif raw_state in {"missing_in_source", "missing_in_advertisement", "not_comparable"} or advertised in (None, "") or observed in (None, ""):
                state = "Not comparable"
            else:
                state = "Unknown"
            rows.append(
                {
                    "Source": safe_value(item.get("source_url")),
                    "Field": label,
                    "State": state,
                    "Advertised value": safe_value(advertised, "Not extracted"),
                    "Observed value": safe_value(observed, "Not found in source"),
                    "Rationale": safe_value(comparison.get("note") or item.get("rationale"), "No rationale recorded."),
                }
            )
    return rows


def aggregation_summary(evidence: Iterable[dict[str, Any]], naive_result: Any, lineage_result: Any) -> dict[str, Any]:
    items = [item for item in evidence if isinstance(item, dict)]
    groups = sorted({str(item.get("lineage_group")) for item in items if item.get("lineage_group")})
    consolidated = max(0, int(getattr(naive_result, "effective_sources", 0)) - int(getattr(lineage_result, "effective_sources", 0)))
    return {
        "naive_effective_sources": int(getattr(naive_result, "effective_sources", 0)),
        "lineage_effective_sources": int(getattr(lineage_result, "effective_sources", 0)),
        "consolidated_records": consolidated,
        "lineage_groups": groups,
        "lineage_review_note": "No reviewed lineage groups were supplied; unknown relationships were kept separate." if not groups else "Reviewed lineage groups supplied by the backend.",
    }
