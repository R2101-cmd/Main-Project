"""Explicit conversion from collection vocabulary to live evidence vocabulary.

Collection records are descriptive research artifacts. They are never promoted
to live authorization support merely because they say ``independent`` or because
their source hostname looks official. Promotion requires explicit, current
authority and adjudicated lineage supplied by a later review step.
"""
from __future__ import annotations

from typing import Any


COLLECTION_STATE_MAP = {
    "independent_official_confirmation": "snapshot_match_only",
    "fresh_same_system_retrieval": "unverified",
    "snapshot_match_only": "snapshot_match_only",
    "supported": "unverified",
    "contradicted": "unverified",
    "unresolved": "unresolved",
    "unavailable": "unavailable",
    "inaccessible": "unavailable",
}


def convert_collection_evidence(
    record: dict[str, Any],
    *,
    current_authorization_established: bool = False,
    authority_verified: bool = False,
    adjudicated_lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert one stored collection row conservatively and losslessly.

    The optional promotion flags are deliberately explicit. They default to
    false, and no lineage status is inferred from collection source metadata.
    """
    original_state = str(record.get("evidence_state") or record.get("evidence_classification") or "unresolved")
    live_state = COLLECTION_STATE_MAP.get(original_state, "unresolved")
    can_support = current_authorization_established and authority_verified and live_state not in {"snapshot_match_only", "unavailable", "unresolved"}
    verification_status = "independently_supported" if can_support else "independently_unresolved"
    source_relationship = "unknown"
    lineage_review_status = "not_assessed"
    lineage_group = None
    if adjudicated_lineage and adjudicated_lineage.get("review_status") == "adjudicated" and adjudicated_lineage.get("relationship") in {"independent", "copied_derived"}:
        source_relationship = adjudicated_lineage["relationship"]
        lineage_review_status = "adjudicated"
        lineage_group = adjudicated_lineage.get("vacancy_group_id") or adjudicated_lineage.get("lineage_group_id")
    if can_support and source_relationship == "independent":
        live_state = "supported"
    return {
        "case_id": record.get("case_id") or record.get("id"),
        "source_url": record.get("source_url") or record.get("official_employer_url") or record.get("original_source_url"),
        "evidence_state": live_state,
        "verification_status": verification_status,
        "source_relationship": source_relationship,
        "lineage_review_status": lineage_review_status,
        "lineage_group": lineage_group,
        "retrieval_status": "available" if record.get("retrieval_timestamp") or record.get("retrieved_at") else "unavailable",
        "details": {
            "original_collection_state": original_state,
            "original_classification": record.get("evidence_classification"),
            "original_employer_identity_evidence": record.get("employer_identity_evidence"),
            "original_vacancy_authorization_evidence": record.get("vacancy_authorization_evidence"),
            "source_independence_claim": record.get("source_independence") or record.get("source_independence_status"),
            "retrieval_independence_claim": record.get("retrieval_independence") or record.get("retrieval_independence_status"),
            "snapshot_reference": record.get("response_hash") or record.get("official_response_hash"),
            "retrieved_at": record.get("retrieval_timestamp") or record.get("retrieved_at"),
            "source_published_at": record.get("publication_date"),
            "source_modified_at": record.get("updated_date") or record.get("update_date"),
            "conversion_note": "Collection metadata was preserved; live support and adjudicated lineage were not inferred.",
        },
    }
