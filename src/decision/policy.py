def assess(*, employer_identity: str, vacancy_evidence_state: str, evidence_available: int, retrieval_failures: int = 0) -> dict:
    if vacancy_evidence_state == "contradicted":
        action = "affirmative contradiction identified"
        reason = "Evidence specifically contradicts authorization of this vacancy."
    elif vacancy_evidence_state == "supported" and evidence_available > 0:
        action = "evidence-supported assessment"
        reason = "At least one relevant supporting observation is available; this does not guarantee legitimacy."
    elif evidence_available == 0 or retrieval_failures > 0:
        action = "insufficient evidence; abstain"
        reason = "No sufficient role-specific evidence is available, or retrieval failed. Missing evidence is not proof of fraud."
    else:
        action = "authorization unresolved"
        reason = "The available evidence does not support a definitive authorization finding."
    return {"employer_identity": employer_identity, "vacancy_authorization": vacancy_evidence_state, "action": action, "reason": reason}
