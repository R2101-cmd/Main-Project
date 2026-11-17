"""Create and validate human annotation/lineage review work queues.

This script never invents labels. Blank or pending decisions remain pending.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.lineage.similarity import compare, candidate_relationship


def _rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_lineage_queue(source: Path, output: Path, threshold: float = .72) -> dict:
    rows = _rows(source)
    pairs = []
    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            if left.get("employer_id") != right.get("employer_id"):
                continue
            sim = compare(left.get("job_description", ""), right.get("job_description", ""), left.get("contact_details"), right.get("contact_details"), left.get("application_url"), right.get("application_url"))
            relation, note = candidate_relationship(sim, threshold)
            if relation != "independent":
                pairs.append({"lineage_relationship_id": f"candidate-{len(pairs)+1:04d}", "case_id_left": left.get("case_id"), "case_id_right": right.get("case_id"), "vacancy_group_id": "", "similarity": round(sim.score, 6), "shared_contact": sim.shared_contact, "shared_application_url": sim.shared_application_url, "suggested_relationship": relation, "signals": note, "relationship": "", "reviewer_id": "", "reviewed_at": "", "rationale": "", "review_status": "candidate"})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pairs[0]) if pairs else ["lineage_relationship_id", "case_id_left", "case_id_right", "relationship", "reviewer_id", "reviewed_at", "rationale", "review_status"])
        writer.writeheader(); writer.writerows(pairs)
    return {"source_records": len(rows), "candidate_pairs": len(pairs), "output": str(output), "human_review_required": True}


def validate_annotations(path: Path) -> dict:
    errors = []
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    allowed = {"supported", "contradicted", "unresolved"}
    for index, record in enumerate(records, 1):
        for key in ("id", "vacancy_group", "partition", "authorization_label"):
            if not record.get(key): errors.append(f"row {index}: missing {key}")
        if record.get("authorization_label") not in allowed: errors.append(f"row {index}: invalid authorization_label")
        if record.get("partition") not in {"train", "validation", "test"}: errors.append(f"row {index}: invalid partition")
    groups = {}
    for record in records: groups.setdefault(record.get("vacancy_group"), set()).add(record.get("partition"))
    errors.extend(f"group {group}: crosses partitions" for group, parts in groups.items() if len(parts) > 1)
    return {"records": len(records), "errors": errors, "valid": not errors, "validated_at": datetime.now(timezone.utc).isoformat()}


def prepare_existing_lineage_review(source: Path, output: Path) -> dict:
    """Convert an existing candidate table into a human-editable review queue."""
    rows = _rows(source)
    prepared = []
    for row in rows:
        case_ids = [value for value in (row.get("related_case_ids") or "").split(";") if value]
        if not case_ids:
            case_ids = [value for value in (row.get("case_id_1"), row.get("case_id_2")) if value]
        prepared.append({
            "lineage_relationship_id": row.get("lineage_group_id") or row.get("pair_id") or f"candidate-{len(prepared)+1:04d}",
            "case_ids": ";".join(case_ids),
            "signals": row.get("lineage_signals") or f"similarity={row.get('similarity_score', '')}; title_similarity={row.get('title_similarity', '')}; description_similarity={row.get('description_similarity', '')}; location_similarity={row.get('location_similarity', '')}",
            "suggested_relationship": row.get("suggested_relationship", "candidate; manual review required"),
            "relationship": "",
            "reviewer_id": "",
            "reviewed_at": "",
            "rationale": "",
            "confidence": "not_assigned",
            "review_status": "candidate",
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(prepared[0]) if prepared else ["lineage_relationship_id", "case_ids", "relationship", "reviewer_id", "reviewed_at", "rationale", "review_status"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(prepared)
    return {"candidate_rows": len(prepared), "output": str(output), "human_review_required": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    q = sub.add_parser("lineage-queue"); q.add_argument("source"); q.add_argument("output")
    l = sub.add_parser("lineage-review-queue"); l.add_argument("source"); l.add_argument("output")
    a = sub.add_parser("validate"); a.add_argument("source")
    args = parser.parse_args()
    if args.command == "lineage-queue": result = build_lineage_queue(Path(args.source), Path(args.output))
    elif args.command == "lineage-review-queue": result = prepare_existing_lineage_review(Path(args.source), Path(args.output))
    else: result = validate_annotations(Path(args.source))
    print(json.dumps(result, indent=2))
