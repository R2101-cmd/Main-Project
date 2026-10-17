from dataclasses import dataclass

@dataclass(frozen=True)
class AggregateAssessment:
    state: str
    supporting_sources: int
    contradicting_sources: int
    effective_sources: int
    explanation: str

def naive(evidence: list[dict]) -> AggregateAssessment:
    supported = sum(e.get("evidence_state") == "supported" for e in evidence)
    contradicted = sum(e.get("evidence_state") == "contradicted" for e in evidence)
    state = "contradicted" if contradicted else "supported" if supported else "unresolved"
    return AggregateAssessment(state, supported, contradicted, len(evidence), "Each evidence appearance is counted independently.")

def lineage_aware(evidence: list[dict], dependent_group_keys: set[str] | None = None) -> AggregateAssessment:
    dependent_group_keys = dependent_group_keys or set()
    seen: set[str] = set()
    effective = []
    for item in evidence:
        key = item.get("lineage_group") or item.get("source_url") or item.get("id")
        if key in dependent_group_keys and key in seen:
            continue
        seen.add(key)
        effective.append(item)
    result = naive(effective)
    return AggregateAssessment(result.state, result.supporting_sources, result.contradicting_sources, len(effective), "Dependent copies are consolidated by lineage group; unknown relationships are not treated as independent confirmation.")
