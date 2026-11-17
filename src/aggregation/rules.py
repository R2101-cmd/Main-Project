from dataclasses import dataclass

@dataclass(frozen=True)
class AggregateAssessment:
    state: str
    supporting_sources: int
    contradicting_sources: int
    effective_sources: int
    explanation: str

def naive(evidence: list[dict]) -> AggregateAssessment:
    """Ordinary appearance-level aggregation of explicitly verified evidence.

    This intentionally does not deduplicate source appearances. Lineage-aware
    aggregation applies the additional dependence rules below. A positive or
    negative aggregate state is usable only when the verification status
    independently confirms that same state; missing, unknown or inconsistent
    status metadata is insufficient evidence.
    """
    expected_status = {
        "supported": "independently_supported",
        "contradicted": "independently_contradicted",
    }
    usable = [
        e for e in evidence
        if e.get("evidence_state") in expected_status
        and e.get("verification_status") == expected_status[e["evidence_state"]]
    ]
    supported = sum(e.get("evidence_state") == "supported" for e in usable)
    contradicted = sum(e.get("evidence_state") == "contradicted" for e in usable)
    state = "contradicted" if contradicted else "supported" if supported else "unresolved"
    return AggregateAssessment(state, supported, contradicted, len(usable), "Counts only comparable support or contradiction evidence; snapshots, unresolved and unavailable items do not authorize a vacancy.")

def lineage_aware(evidence: list[dict], dependent_group_keys: set[str] | None = None) -> AggregateAssessment:
    """Consolidate known dependent groups and abstain on explicitly unknown lineage.

    This is conservative: omitted evidence can reduce support, but cannot turn
    an unresolved set into a positive or negative authorization decision.
    """
    dependent_group_keys = dependent_group_keys or set()
    seen: set[str] = set()
    effective = []
    for item in evidence:
        # A source is eligible only when lineage independence is explicit.
        # Missing/null/blank metadata, candidates, and explicit unknowns abstain.
        relationship = str(item.get("source_relationship") or "").strip().lower()
        status = str(item.get("lineage_status") or "").strip().lower()
        review = str(item.get("lineage_review_status") or "").strip().lower()
        confirmed_independent = relationship == "independent" and review == "adjudicated"
        confirmed_dependent = relationship == "copied_derived" and review == "adjudicated"
        if not (confirmed_independent or confirmed_dependent):
            continue
        key = item.get("lineage_group") or item.get("lineage_group_id") or item.get("source_url") or item.get("id")
        if confirmed_dependent and key in seen:
            continue
        if key in dependent_group_keys and key in seen:
            continue
        seen.add(key)
        effective.append(item)
    result = naive(effective)
    return AggregateAssessment(result.state, result.supporting_sources, result.contradicting_sources, result.effective_sources, "Dependent copies are consolidated; unknown relationships are not treated as independent confirmation and are excluded from the effective source count.")
