"""Build an explicitly synthetic, balanced smoke benchmark.

This generator creates controlled scenarios for software and metric checks. It does
not copy or relabel the real benchmark and its labels are not human ground truth.
"""

from __future__ import annotations

import json
import hashlib
import random
from pathlib import Path


SEED = 20261022
TOTAL_PER_LABEL = 20
LABELS = ("supported", "contradicted", "unresolved")
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "synthetic_benchmark_v1.jsonl"
MANIFEST = ROOT / "SYNTHETIC_MANIFEST_v1.json"


def evidence(record_id: str, group: str, index: int, state: str, relationship: str, lineage_group: str | None, source_kind: str, rationale: str, retrieval_status: str = "available") -> dict:
    return {
        "id": f"SYN-EV-{record_id}-{index}",
        "evidence_id": f"SYN-EV-{record_id}-{index}",
        "advertisement_id": record_id,
        "case_id": record_id,
        "vacancy_group_id": group,
        "source_url": f"synthetic://source/{record_id}/{index}",
        "source_type": source_kind,
        "source_relationship": relationship,
        "lineage_group": lineage_group,
        "lineage_review_status": "synthetic_scenario_not_human_reviewed",
        "retrieval_status": retrieval_status,
        "retrieval_state": retrieval_status,
        "evidence_state": state,
        "evidence_status": state,
        "matched_fields": ["employer", "title", "location"] if state == "supported" else [],
        "contradicted_fields": ["authorization"] if state == "contradicted" else [],
        "summary": rationale,
        "rationale": rationale,
        "evidence_excerpt": f"Synthetic scenario evidence for {record_id}; not a real source record.",
        "retrieved_at": None,
        "source_published_at": None,
        "snapshot_reference": None,
        "privacy_review_status": "not_needed",
    }


def make_record(number: int, label: str, partition: str) -> dict:
    record_id = f"SYN-{number:04d}"
    group = f"SYN-G-{number:04d}"
    employer = f"Synthetic Employer {number % 10:02d}"
    title = {"supported": "Data Analyst Intern", "contradicted": "Data Analyst Intern", "unresolved": "Data Analyst Intern"}[label]
    location = ["Bengaluru", "Mumbai", "Remote", "New Delhi"][number % 4]
    if label == "supported":
        text = f"Synthetic advertisement. Employer: {employer}. Title: {title}. Location: {location}. An employer-controlled careers source confirms requisition SYN-{number:04d}. This is a generated scenario, not a real vacancy."
        state = "supported"
        rationale = "Synthetic scenario: an employer-controlled source explicitly matches the vacancy and authorization basis."
        source_kind = "synthetic_official_employer_source"
    elif label == "contradicted":
        text = f"Synthetic advertisement. Employer: {employer}. Title: {title}. Location: {location}. A separate synthetic authorization notice states that requisition SYN-{number:04d} was not issued by the employer. This is a generated scenario, not a real vacancy."
        state = "contradicted"
        rationale = "Synthetic scenario: an affirmative source-level contradiction is supplied for this specific requisition."
        source_kind = "synthetic_contradicting_source"
    else:
        text = f"Synthetic advertisement. Employer: {employer}. Title: {title}. Location: {location}. The only available source is a third-party listing and employer authorization is not established. This is a generated scenario, not a real vacancy."
        state = "unverified"
        rationale = "Synthetic scenario: evidence is insufficient to support or contradict authorization."
        source_kind = "synthetic_third_party_source"

    items = [evidence(record_id, group, 1, state, "original", f"SYN-LG-{number:04d}-A", source_kind, rationale)]
    pattern = number % 4
    if pattern == 0:
        items.append(evidence(record_id, group, 2, state, "copied_derived", f"SYN-LG-{number:04d}-A", "synthetic_copied_source", "Synthetic duplicate of the first source; the relationship is fixed by the scenario generator."))
    elif pattern == 1:
        items.append(evidence(record_id, group, 2, state, "independent", f"SYN-LG-{number:04d}-B", "synthetic_independent_source", "Synthetic independently published source; no dependency is asserted."))
    elif pattern == 2:
        items.append(evidence(record_id, group, 2, "unavailable", "unknown", None, "synthetic_unavailable_source", "Synthetic source is inaccessible; unavailable evidence is not treated as fraud.", "unavailable"))
    else:
        items.append(evidence(record_id, group, 2, state, "unknown", None, "synthetic_unknown_source", "Synthetic source relationship is intentionally unknown and is not consolidated."))

    return {
        "id": record_id,
        "advertisement_id": record_id,
        "vacancy_group": group,
        "vacancy_group_id": group,
        "partition": partition,
        "text": text,
        "employer_id": f"SYN-EMP-{number % 10:02d}",
        "employer_name": employer,
        "job_title": title,
        "location": location,
        "salary_text": "Synthetic value only",
        "requisition_id": f"SYN-{number:04d}",
        "original_source_url": f"synthetic://advertisement/{record_id}",
        "source_type": "synthetic_scenario",
        "input_type": "pasted_text",
        "observed_at": None,
        "source_published_at": None,
        "snapshot_reference": None,
        "privacy_review_status": "not_needed",
        "missing_data_notes": ["No real source was observed; all source and timestamps are synthetic scenario fields."],
        "authorization_label": label,
        "employer_identity": "synthetic_scenario_label",
        "annotation_status": "synthetic_generator_v1_not_human_reviewed",
        "annotation_rationale": rationale,
        "synthetic": True,
        "synthetic_label_source": "scenario_generator_v1",
        "synthetic_generation_seed": SEED,
        "evidence": items,
    }


def main() -> None:
    records: list[dict] = []
    number = 1
    for label in LABELS:
        for offset in range(TOTAL_PER_LABEL):
            partition = "train" if offset < 12 else "validation" if offset < 16 else "test"
            records.append(make_record(number, label, partition))
            number += 1
    random.Random(SEED).shuffle(records)
    OUTPUT.write_text("\n".join(json.dumps(record, separators=(",", ":")) for record in records) + "\n", encoding="utf-8")
    output_sha256 = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps({
        "dataset": OUTPUT.name,
        "synthetic": True,
        "generator": Path(__file__).name,
        "seed": SEED,
        "records": len(records),
        "sha256": output_sha256,
        "labels": {label: TOTAL_PER_LABEL for label in LABELS},
        "partitions_per_label": {"train": 12, "validation": 4, "test": 4},
        "human_annotation": False,
        "real_world_evidence": False,
        "permitted_use": "software, schema, aggregation, and metric smoke tests only",
        "not_permitted": "real-world accuracy, fraud prevalence, or generalization claims",
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "manifest": str(MANIFEST), "records": len(records), "labels": {label: TOTAL_PER_LABEL for label in LABELS}}, indent=2))


if __name__ == "__main__":
    main()
