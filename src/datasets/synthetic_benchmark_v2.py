"""Deterministic builder and validator for the isolated synthetic benchmark v2."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

SEED = 20261114
CLASSES = ("supported", "contradicted", "unresolved")
EVIDENCE_STATES = {"supported", "contradicted", "unverified", "unavailable"}
RELATIONSHIPS = {"original", "independent", "copied_derived", "unknown"}
SCENARIOS: tuple[tuple[str, str], ...] = (
    ("current_official_corroboration", "supported"),
    ("official_match_with_reposts", "supported"),
    ("distinct_independent_official_sources", "supported"),
    ("complete_match_with_unavailable_noise", "supported"),
    ("specific_role_among_similar_titles", "supported"),
    ("official_requisition_cancellation", "contradicted"),
    ("official_employer_denial", "contradicted"),
    ("official_material_field_conflict", "contradicted"),
    ("copied_claims_with_official_rejection", "contradicted"),
    ("official_application_route_conflict", "contradicted"),
    ("conflicting_independent_sources", "unresolved"),
    ("supported_claim_unknown_lineage", "unresolved"),
    ("supported_claim_missing_lineage", "unresolved"),
    ("stale_or_unavailable_sources", "unresolved"),
    ("incomplete_insufficient_advertisement", "unresolved"),
)

JOBS = (
    ("People Operations Analyst", "Northwind Care", "Portland", "full-time"),
    ("Cloud Security Engineer", "Juniper Works", "Austin", "contract"),
    ("Clinical Data Coordinator", "Harbor Health", "Boston", "part-time"),
    ("Revenue Operations Lead", "Cedar Systems", "Denver", "full-time"),
    ("Laboratory Technician", "Mosaic Bio", "Raleigh", "contract"),
    ("Customer Support Specialist", "Bluebird Transit", "Chicago", "full-time"),
    ("Product Researcher", "Summit Learning", "Remote", "part-time"),
    ("Network Administrator", "Redwood Energy", "Phoenix", "full-time"),
    ("Payroll Associate", "Common Ground Foods", "Atlanta", "contract"),
    ("Quality Engineer", "Silverline Devices", "Seattle", "full-time"),
    ("Procurement Specialist", "Lattice Harbor", "Toronto", "full-time"),
    ("Environmental Field Technician", "Pine & Vale Utilities", "Calgary", "seasonal"),
)
TEXT_FORMS = (
    "{employer} is seeking a {title} in {location}. The role coordinates team work, maintains accurate records, and reports operational issues.",
    "Join {employer} as a {title}. The position is based in {location} and involves planning daily work, documenting outcomes, and working with partner teams.",
    "A {title} opening is listed for {employer} in {location}; responsibilities include reviewing work requests, keeping project records current, and communicating progress.",
    "{employer} has an opening for a {title}, {location}. The successful candidate will support ongoing programs, check work quality, and share clear updates.",
    "The {title} role at {employer} supports service delivery from {location}, including coordination, record keeping, and practical problem solving.",
    "Based in {location}, this {title} position with {employer} works across internal teams to organize assignments, track results, and improve routine processes.",
)


def _digest(value: str, length: int = 20) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _evidence(key: str, number: int, state: str, relationship: str | None, group: str | None,
              *, verification: str | None = None, retrieval: str = "available",
              review: str | None = None, source_type: str = "employer_controlled_source",
              matched: list[str] | None = None, contradicted: list[str] | None = None,
              note: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": f"ev-{_digest(key + ':' + str(number), 14)}",
        "evidence_state": state,
        "retrieval_status": retrieval,
        "source_type": source_type,
        "source_url": f"synthetic://evidence/{_digest(key, 14)}/{number}",
        "matched_fields": matched or [],
        "contradicted_fields": contradicted or [],
        "summary": note or ("Synthetic source record for a specific vacancy claim."),
    }
    if relationship is not None:
        row["source_relationship"] = relationship
    if group is not None:
        row["lineage_group"] = group
    if review is not None:
        row["lineage_review_status"] = review
    if verification is not None:
        row["verification_status"] = verification
    return row


def generate_records(seed: int = SEED) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    scenario_rows = [(name, label, slot) for name, label in SCENARIOS for slot in range(20)]
    rng.shuffle(scenario_rows)
    inputs: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    scenarios: list[dict[str, Any]] = []
    for index, (scenario, label, slot) in enumerate(scenario_rows):
        key = f"r-{_digest(f'{seed}:{index}:{scenario}:{slot}', 20)}"
        case_id = f"VG-SYN2-{index + 1:04d}"
        title, employer, location, employment_type = JOBS[(index * 7 + slot * 5) % len(JOBS)]
        if scenario == "specific_role_among_similar_titles":
            # Same employer has another opening with an adjacent title; the source identifies this requisition's distinct title and location.
            text = f"{employer} lists a {title} in {location}, focused on {('network operations' if 'Administrator' in title else 'the stated team program')}. A separate {title.replace('Specialist', 'Coordinator')} opening belongs to another department and location."
        elif scenario == "incomplete_insufficient_advertisement":
            text = f"{employer} is hiring. Interested applicants may send a resume. Further role and requisition details are not included in this listing."
        else:
            template = TEXT_FORMS[(index + slot) % len(TEXT_FORMS)]
            text = template.format(employer=employer, title=title, location=location)
        if scenario == "official_material_field_conflict":
            text += f" The listing describes the position as {employment_type}; the employer's current vacancy notice identifies a different employment arrangement."
        if scenario == "official_application_route_conflict":
            text += " The advertisement directs applicants to a recruiting mailbox that differs from the employer's current careers listing."
        vacancy_group = f"vac-{_digest(f'{seed}:vacancy:{index}', 14)}"
        official_group = f"line-{_digest(f'{seed}:official:{index}', 14)}"
        requisition_id = f"{employer[:2].upper()}-{_digest(key + ':req', 8).upper()}"
        evidence: list[dict[str, Any]] = []
        synthetic_official = "synthetic_employer_controlled_current"

        def add(state: str, relationship: str | None, group: str | None, **kwargs: Any) -> None:
            evidence.append(_evidence(key, len(evidence) + 1, state, relationship, group, **kwargs))

        if scenario == "current_official_corroboration":
            add("supported", "independent", official_group, review="adjudicated", verification="independently_supported", source_type=synthetic_official, matched=["employer", "title", "requisition_id", "location"], note="Current synthetic employer-controlled vacancy record matches the advertised role and requisition.")
            add("supported", "independent", f"line-{_digest(key + ':second', 14)}", review="adjudicated", verification="independently_supported", matched=["employer", "title", "location"], note="A separately controlled synthetic employer careers record corroborates the same vacancy.")
        elif scenario == "official_match_with_reposts":
            add("supported", "independent", official_group, review="adjudicated", verification="independently_supported", source_type=synthetic_official, matched=["employer", "title", "requisition_id", "application_url"], note="Current synthetic employer-controlled vacancy record matches the specific requisition.")
            for copy in range(3):
                add("supported", "copied_derived", f"line-{_digest(key + ':copies', 14)}", review="adjudicated", source_type="third_party_repost", matched=["title", "employer"], note="Third-party advertisement repeats vacancy details from a shared posting group.")
        elif scenario == "distinct_independent_official_sources":
            for source in range(2):
                add("supported", "independent", f"line-{_digest(key + ':ind' + str(source), 14)}", review="adjudicated", verification="independently_supported", source_type=synthetic_official, matched=["employer", "title", "location", "employment_type"], note="Distinct synthetic employer-controlled source confirms the same vacancy fields.")
        elif scenario == "complete_match_with_unavailable_noise":
            add("supported", "independent", official_group, review="adjudicated", verification="independently_supported", source_type=synthetic_official, matched=["employer", "title", "requisition_id", "location"], note="Current synthetic employer-controlled record confirms the identified vacancy.")
            add("unavailable", "unknown", None, retrieval="unavailable", source_type="third_party_archive", note="Related third-party page could not be retrieved.")
        elif scenario == "specific_role_among_similar_titles":
            add("supported", "independent", official_group, review="adjudicated", verification="independently_supported", source_type=synthetic_official, matched=["employer", "title", "requisition_id", "location"], note="Employer-controlled record identifies this title, department, and location as a distinct open vacancy.")
        elif scenario == "official_requisition_cancellation":
            add("contradicted", "independent", official_group, review="adjudicated", verification="independently_contradicted", source_type=synthetic_official, contradicted=["requisition_id", "posting_status"], note="Current synthetic employer-controlled notice states that this exact requisition was withdrawn before the advertisement date.")
        elif scenario == "official_employer_denial":
            add("contradicted", "independent", official_group, review="adjudicated", verification="independently_contradicted", source_type=synthetic_official, contradicted=["employer", "requisition_id"], note="Current synthetic employer-controlled notice explicitly denies issuing the named vacancy and requisition.")
        elif scenario == "official_material_field_conflict":
            add("contradicted", "independent", official_group, review="adjudicated", verification="independently_contradicted", source_type=synthetic_official, contradicted=["employment_type", "location"], note="Comparable current employer-controlled vacancy details materially conflict on employment arrangement and location.")
        elif scenario == "copied_claims_with_official_rejection":
            for copy in range(4):
                add("supported", "copied_derived", f"line-{_digest(key + ':copies', 14)}", review="adjudicated", source_type="third_party_repost", matched=["employer", "title"], note="Third-party listing repeats the same claim from a shared source group.")
            add("contradicted", "independent", official_group, review="adjudicated", verification="independently_contradicted", source_type=synthetic_official, contradicted=["requisition_id", "posting_status"], note="Current synthetic employer-controlled notice rejects the specific requisition repeated by third-party copies.")
        elif scenario == "official_application_route_conflict":
            add("contradicted", "independent", official_group, review="adjudicated", verification="independently_contradicted", source_type=synthetic_official, contradicted=["application_url", "requisition_id"], note="The employer confirms the named requisition is not available through its controlled application route.")
        elif scenario == "conflicting_independent_sources":
            add("unverified", "independent", f"line-{_digest(key + ':one', 14)}", review="adjudicated", verification="independently_unresolved", source_type=synthetic_official, note="One current synthetic employer-controlled source lists the vacancy as open.")
            add("unverified", "independent", f"line-{_digest(key + ':two', 14)}", review="adjudicated", verification="independently_unresolved", source_type=synthetic_official, note="A second current synthetic employer-controlled source gives incompatible status or vacancy details; conflict is not resolved.")
        elif scenario == "supported_claim_unknown_lineage":
            add("supported", "unknown", None, review="unknown", verification="independently_unresolved", source_type="third_party_listing", matched=["employer", "title"], note="A listing matches basic fields, but source independence and employer control are not established.")
            add("supported", "unknown", None, review="unknown", source_type="third_party_repost", matched=["employer", "title"], note="Another listing repeats the claim; its relationship to the first source is unknown.")
        elif scenario == "supported_claim_missing_lineage":
            # Missing relationship and review fields are intentional and distinct from adjudicated dependence.
            evidence.append(_evidence(key, 1, "supported", None, None, source_type="third_party_listing", matched=["employer", "title"], note="A listing matches basic fields but has no source-independence or lineage review metadata."))
            evidence.append(_evidence(key, 2, "supported", None, None, source_type="third_party_repost", matched=["employer", "title"], note="A second listing repeats the claim without source relationship metadata."))
        elif scenario == "stale_or_unavailable_sources":
            stale = _evidence(key, 1, "supported", "independent", official_group, review="adjudicated", verification="snapshot_match_only", source_type="historical_employer_snapshot", matched=["employer", "title", "location"], note="Historical synthetic vacancy snapshot is outside the current evidence freshness window.")
            stale["source_published_at"] = "2025-01-15T00:00:00Z"
            stale["retrieved_at"] = "2026-11-14T00:00:00Z"
            evidence.append(stale)
            add("unavailable", "unknown", None, retrieval="unavailable", source_type="employer_careers_page", note="The current employer careers page is unavailable for retrieval.")
        elif scenario == "incomplete_insufficient_advertisement":
            add("unverified", "unknown", None, review="unknown", source_type="third_party_listing", note="Available listing omits role, requisition, location, and verifiable application details.")
            add("unavailable", "unknown", None, retrieval="unavailable", source_type="employer_careers_page", note="Employer source cannot be retrieved to resolve the incomplete listing.")

        inputs.append({
            "input_key": key,
            "synthetic": True,
            "advertisement": {
                "text": text,
                "employer_name": employer,
                "job_title": title,
                "location": location,
                "employment_type": employment_type,
                "salary_text": None,
                "requisition_id": requisition_id,
            },
            "evidence": evidence,
        })
        labels.append({"input_key": key, "case_id": case_id, "expected_label": label})
        scenarios.append({"input_key": key, "case_id": case_id, "vacancy_group": vacancy_group, "scenario": scenario, "scenario_slot": slot})
    return inputs, labels, scenarios


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_package(output_dir: Path, seed: int = SEED) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs, labels, scenarios = generate_records(seed)
    input_path, label_path, scenario_path = (output_dir / name for name in ("model_inputs.jsonl", "expected_labels.jsonl", "scenario_metadata.jsonl"))
    _jsonl(input_path, inputs)
    _jsonl(label_path, labels)
    _jsonl(scenario_path, scenarios)
    counts = Counter(row["expected_label"] for row in labels)
    scenario_counts = Counter(row["scenario"] for row in scenarios)
    manifest: dict[str, Any] = {
        "name": "vacancyguard_synthetic_benchmark_v2",
        "synthetic_only": True,
        "seed": seed,
        "records": len(inputs),
        "class_counts": dict(sorted(counts.items())),
        "scenario_counts": dict(sorted(scenario_counts.items())),
        "input_file": input_path.name,
        "expected_labels_file": label_path.name,
        "scenario_metadata_file": scenario_path.name,
        "labels_and_scenarios_excluded_from_model_inputs": True,
        "case_ids_excluded_from_model_inputs": True,
        "evaluation_performed": False,
        "historical_artifacts_preserved": True,
        "files_sha256": {path.name: _sha(path) for path in (input_path, label_path, scenario_path)},
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_package(output_dir: Path) -> list[str]:
    errors: list[str] = []
    try:
        inputs = load_jsonl(output_dir / "model_inputs.jsonl")
        labels = load_jsonl(output_dir / "expected_labels.jsonl")
        scenarios = load_jsonl(output_dir / "scenario_metadata.jsonl")
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load benchmark package: {exc}"]
    if len(inputs) != 300 or len({row.get("input_key") for row in inputs}) != 300:
        errors.append("inputs must contain exactly 300 unique input keys")
    if len(labels) != 300 or len({row.get("input_key") for row in labels}) != 300:
        errors.append("labels must contain exactly 300 unique input keys")
    if len(scenarios) != 300 or len({row.get("input_key") for row in scenarios}) != 300:
        errors.append("scenario metadata must contain exactly 300 unique input keys")
    input_keys = {row.get("input_key") for row in inputs}
    label_keys = {row.get("input_key") for row in labels}
    scenario_keys = {row.get("input_key") for row in scenarios}
    if input_keys != label_keys or input_keys != scenario_keys:
        errors.append("input, label, and scenario keys do not map one-to-one")
    counts = Counter(row.get("expected_label") for row in labels)
    if counts != Counter({"supported": 100, "contradicted": 100, "unresolved": 100}):
        errors.append(f"class distribution is not exactly balanced: {dict(counts)}")
    scenario_counts = Counter(row.get("scenario") for row in scenarios)
    if len(scenario_counts) != 15 or any(count < 20 for count in scenario_counts.values()):
        errors.append("scenario diversity is incomplete or imbalanced")
    label_by_key = {row.get("input_key"): row.get("expected_label") for row in labels}
    scenario_by_key = {row.get("input_key"): row.get("scenario") for row in scenarios}
    expected_by_scenario = dict(SCENARIOS)
    if any(label_by_key.get(key) != expected_by_scenario.get(scenario) for key, scenario in scenario_by_key.items()):
        errors.append("one or more labels do not match their documented evidence scenario")
    if any(row.get("synthetic") is not True or not isinstance(row.get("advertisement"), dict) for row in inputs):
        errors.append("each model input must be explicitly synthetic and include an advertisement")
    forbidden = {"expected_label", "authorization_label", "scenario", "scenario_name", "case_id", "evaluation_note", "annotation_rationale"}
    for index, row in enumerate(inputs):
        if forbidden.intersection(row):
            errors.append(f"model input {index} contains evaluation-only fields")
        serialized = json.dumps(row, ensure_ascii=False).casefold()
        if any(case_id.casefold() in serialized for case_id in (label.get("case_id", "") for label in labels)):
            errors.append(f"model input {index} exposes an evaluation case ID")
        if any(name.casefold() in serialized for name in expected_by_scenario):
            errors.append(f"model input {index} exposes an evaluation scenario name")
        for evidence_index, item in enumerate(row.get("evidence", [])):
            if item.get("evidence_state") not in EVIDENCE_STATES:
                errors.append(f"model input {index} evidence {evidence_index} has invalid evidence state")
            if item.get("source_relationship") is not None and item.get("source_relationship") not in RELATIONSHIPS:
                errors.append(f"model input {index} evidence {evidence_index} has invalid lineage relationship")
    for name in ("model_inputs.jsonl", "expected_labels.jsonl", "scenario_metadata.jsonl"):
        path = output_dir / name
        if manifest.get("files_sha256", {}).get(name) != _sha(path):
            errors.append(f"manifest hash mismatch for {name}")
    if manifest.get("records") != 300 or manifest.get("evaluation_performed") is not False:
        errors.append("manifest record count or evaluation status is invalid")
    return errors


def package_hashes(output_dir: Path) -> dict[str, str]:
    return {path.name: _sha(path) for path in sorted(output_dir.iterdir()) if path.is_file()}

