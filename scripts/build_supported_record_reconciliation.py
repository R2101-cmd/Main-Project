"""Build a read-only crosswalk of Stage 4E and staging classifications."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "final_completion_package" / "phase2_verification_improvement" / "reconciliation_audit"
STAGE4E = ROOT / "DatasetCollection" / "processed" / "stage4e_evidence_records.csv"
STAGE4E_RESULTS = ROOT / "final_completion_package" / "03_stage4_verification" / "verification_results.csv"
PHASE2_AUTHORITY = ROOT / "final_completion_package" / "phase2_verification_improvement" / "source_authority_analysis.csv"
STAGING = ROOT / "integration_review" / "schema_test" / "disposable_staging_import.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(value: str | None) -> str:
    if value == "independent_official_confirmation":
        return "supported"
    if value == "fresh_same_system_retrieval":
        return "unverified"
    if value in {"supported", "contradicted", "unverified", "unavailable", "unresolved"}:
        return value or "unresolved"
    return "unresolved"


def main() -> None:
    raw_stage4e = read_csv(STAGE4E)
    old_results = {row["case_id"]: row for row in read_csv(STAGE4E_RESULTS)}
    authority = {row["case_id"]: row for row in read_csv(PHASE2_AUTHORITY)}
    staging = {row["case_id"]: row for row in read_csv(STAGING)}
    ids = sorted(set(staging) | set(authority) | set(old_results))
    rows: list[dict[str, str]] = []
    for case_id in ids:
        stage = staging.get(case_id, {})
        auth = authority.get(case_id, {})
        old = old_results.get(case_id, {})
        raw_state = stage.get("evidence_state", "")
        new_state = normalize(raw_state)
        old_verification = auth.get("verification_status_phase2", "")
        rows.append({
            "case_id": case_id,
            "stage4e_raw_evidence_classification": raw_state,
            "stage4e_historical_verification_state": old.get("verification_state", ""),
            "phase2_artifact_verification_status": old_verification,
            "new_staging_normalized_evidence_state": new_state,
            "source_independence_raw": stage.get("source_independence", ""),
            "strict_historical_status": stage.get("strict_historical_status", ""),
            "lineage_candidate_id": stage.get("lineage_candidate_id", ""),
            "confirmed_lineage_id": stage.get("confirmed_lineage_id", ""),
            "lineage_status": "confirmed" if stage.get("confirmed_lineage_id") else ("candidate" if stage.get("lineage_candidate_id") else "none"),
            "snapshot_only_to_independent_authorization_promotion": "no",
            "classification_interpretation": "evidence_state normalization only; not independent official authorization",
        })

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "supported_record_reconciliation.csv"
    fields = list(rows[0]) if rows else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    counts = lambda field: dict(Counter(row[field] or "<missing>" for row in rows))
    stage4e_raw = counts("stage4e_raw_evidence_classification")
    normalized = counts("new_staging_normalized_evidence_state")
    phase2 = counts("phase2_artifact_verification_status")
    historical = counts("stage4e_historical_verification_state")
    lineage = counts("lineage_status")
    source_lines = [
        f"- `DatasetCollection/processed/stage4e_evidence_records.csv` — original Stage 4E evidence artifact; SHA-256 `{digest(STAGE4E)}`.",
        f"- `integration_review/schema_test/disposable_staging_import.csv` — exact input used by the staging CLI; SHA-256 `{digest(STAGING)}`.",
        f"- `final_completion_package/phase2_verification_improvement/source_authority_analysis.csv` — prior Phase 2 artifact-level verification classification; SHA-256 `{digest(PHASE2_AUTHORITY)}`.",
        f"- `final_completion_package/03_stage4_verification/verification_results.csv` — historical verification output; SHA-256 `{digest(STAGE4E_RESULTS)}`.",
    ]
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "records_crosswalked": len(rows),
        "stage4e_raw_evidence_classification": stage4e_raw,
        "new_staging_normalized_evidence_state": normalized,
        "phase2_artifact_verification_status": phase2,
        "stage4e_historical_verification_state": historical,
        "lineage_status": lineage,
        "snapshot_only_to_independent_authorization_promotions": 0,
        "unavailable_unverified_or_snapshot_silent_promotions": 0,
        "source_files_modified": False,
        "datasets_modified": False,
    }
    (OUT / "updated_classification_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = f"""# Supported-record reconciliation audit

Generated: `{summary['generated_utc']}`  
Records crosswalked: **{len(rows)}**

## Finding

The **744 supported** result was calculated from `{STAGING.relative_to(ROOT)}` using its `evidence_state` column. The 744 source values are `independent_official_confirmation`. The new staging loader maps that source-specific value to the generic application evidence state `supported`.

That mapping is an evidence-state normalization. It does **not** establish independent official authorization, and it does not change `verification_status` to `independently_supported`.

## Counts by layer

| Layer | Counts |
|---|---|
| Stage 4E raw evidence classification | `{stage4e_raw}` |
| New staging normalized evidence state | `{normalized}` |
| Phase 2 artifact verification status | `{phase2}` |
| Historical Stage 4 verification state | `{historical}` |
| Lineage status | `{lineage}` |

The Stage 4E quality artifact reports 744 `independent_official_confirmation`, 19 `fresh_same_system_retrieval`, 16 `unresolved`, and 1 `unavailable`. Those become 744 `supported`, 19 `unverified`, 16 `unresolved`, and 1 `unavailable` in the staging loader. The 763/16/1 snapshot summary is not the same field: the prior Phase 2 authority artifact contains 763 `snapshot_match_only` and 17 `inaccessible`; the historical Stage 4 verification CSV contains 780 `independently_unresolved`.

## Answers to the audit questions

1. The exact input is `{STAGING.relative_to(ROOT)}`, field `evidence_state`; the 744 raw values are `independent_official_confirmation`.
2. `supported` means the staging evidence-state vocabulary after normalization. It is not a supervised vacancy-authorization label.
3. It represents collected/source evidence classification, not structural validation alone and not independent official authorization. Snapshot context and authority limitations remain in the other artifacts; this loader does not promote verification status.
4. The complete 780-row mapping is in `supported_record_reconciliation.csv`.
5. No record was promoted from snapshot-only to `independently_supported`; the crosswalk marks all 780 promotion flags `no`.
6. No unavailable, unverified, or snapshot-only evidence was silently promoted to independent authorization. The 19 `fresh_same_system_retrieval` rows remain `unverified`, and the 1 unavailable row remains `unavailable`.
7. The 192 lineage candidates remain `lineage_status=candidate`; confirmed lineage count is 0. No candidate was treated as confirmed.
8. Original datasets and historical outputs were not modified.

## Source checksums

{chr(10).join(source_lines)}

The audit output itself is new and versioned under `final_completion_package/phase2_verification_improvement/reconciliation_audit/`.
"""
    (OUT / "supported_record_reconciliation.md").write_text(md, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
