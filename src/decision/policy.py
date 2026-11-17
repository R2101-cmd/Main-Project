MIN_INDEPENDENT_SOURCES_FOR_DECISION = 2


def qualifying_independent_source_count(evidence: list[dict]) -> int:
    """Count distinct adjudicated independent source groups, excluding copies."""
    groups = set()
    for item in evidence:
        if (item.get("source_relationship") != "independent"
                or item.get("lineage_review_status") != "adjudicated"
                or item.get("verification_status") not in {"independently_supported", "independently_contradicted"}):
            continue
        key = item.get("lineage_group") or item.get("lineage_group_id") or item.get("source_url") or item.get("evidence_id") or item.get("id")
        if key:
            groups.add(str(key))
    return len(groups)


def assess(*, employer_identity: str, vacancy_evidence_state: str, evidence_available: int, retrieval_failures: int = 0,
           vacancy_correspondence: bool | None = None, source_authoritative: bool | None = None,
           freshness_status: str = "unknown", independent_evidence_count: int | None = None,
           supporting_evidence_count: int | None = None, contradicting_evidence_count: int | None = None,
           material_conflicts: list[str] | None = None) -> dict:
    """Apply a conservative final live decision policy over a B/C result.

    The research aggregators remain unchanged. Live authorization needs at least
    two qualifying independent groups, current authoritative sources and a
    vacancy correspondence result. Fraud is always a separate unresolved outcome.
    """
    independent_count = evidence_available if independent_evidence_count is None else independent_evidence_count
    support_count = supporting_evidence_count
    contradiction_count = contradicting_evidence_count
    conflicts = list(material_conflicts or [])
    mixed = support_count is not None and contradiction_count is not None and support_count > 0 and contradiction_count > 0
    enough = independent_count >= MIN_INDEPENDENT_SOURCES_FOR_DECISION
    base_gates_met = vacancy_correspondence is not False and source_authoritative is not False and freshness_status not in {"stale", "unresolved", "unknown"}
    support_gates_met = base_gates_met and not conflicts

    if mixed:
        action = "conflicting evidence; authorization unresolved"
        state = "unresolved"
        reason = "Qualifying evidence includes both support and contradiction; the system does not choose one side."
    elif vacancy_evidence_state == "contradicted" and evidence_available > 0 and enough and base_gates_met and bool(conflicts):
        action = "affirmative contradiction identified"
        state = "contradicted"
        reason = "Evidence specifically contradicts authorization of this vacancy."
    elif vacancy_evidence_state == "supported" and evidence_available > 0 and enough and support_gates_met:
        action = "evidence-supported assessment"
        state = "supported"
        reason = "At least one relevant supporting observation is available; this does not guarantee legitimacy."
    elif evidence_available == 0 or retrieval_failures > 0:
        action = "insufficient evidence; abstain"
        state = "unresolved"
        reason = "No sufficient role-specific evidence is available, or retrieval failed. Missing evidence is not proof of fraud."
    else:
        action = "authorization unresolved"
        state = "unresolved"
        if not enough:
            reason = f"Only {independent_count} qualifying independent source group(s) are available; at least {MIN_INDEPENDENT_SOURCES_FOR_DECISION} are required by the conservative live policy."
        elif not support_gates_met:
            reason = "Authority, freshness, vacancy correspondence or field-conflict checks are incomplete. The result remains unresolved."
        else:
            reason = "The available evidence does not support a definitive authorization finding."
    return {"employer_identity": employer_identity, "vacancy_authorization": state, "aggregation_state": vacancy_evidence_state,
            "fraud_outcome": "unresolved", "action": action, "reason": reason,
            "independent_evidence_count": independent_count, "minimum_independent_sources": MIN_INDEPENDENT_SOURCES_FOR_DECISION,
            "source_authoritative": source_authoritative, "vacancy_correspondence": vacancy_correspondence,
            "freshness_status": freshness_status, "material_conflicts": conflicts}
