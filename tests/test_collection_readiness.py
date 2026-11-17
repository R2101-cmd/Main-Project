import copy
import json
from pathlib import Path

from src.annotation.validation import annotation_fingerprint, validate_annotation_bundle
from src.aggregation.rules import naive
from src.collection_readiness import evaluate_config, verify_frozen_snapshot
from src.evaluation.metrics import selective_metrics
from src.evaluation.validation import frozen_test_id_differences, validate_evaluation_record, validate_split_manifest


ROOT = Path(__file__).resolve().parents[1]


def load_template():
    return json.loads((ROOT / "config" / "collection_config_v1.json").read_text(encoding="utf-8"))


def test_unset_collection_dates_prevent_readiness():
    result = evaluate_config(load_template())
    assert result["collection_ready"] is False
    assert any(check["requirement"] == "Fixed 30-day collection window" and check["status"] == "pending" for check in result["checks"])


def test_malformed_top_level_configuration_is_blocked():
    result = evaluate_config([])
    assert result["collection_ready"] is False
    assert result["checks"][0]["status"] == "blocked"


def test_invalid_time_window_fails_validation():
    config = load_template()
    config["collection_window"].update({"start": "2026-01-01T00:00:00+05:30", "end": "2026-01-31T01:00:00+05:30"})
    result = evaluate_config(config)
    check = next(item for item in result["checks"] if item["requirement"] == "Fixed 30-day collection window")
    assert check["status"] == "blocked"


def test_duration_field_must_also_be_30_days():
    config = load_template()
    config["collection_window"]["duration_days"] = 29
    result = evaluate_config(config)
    check = next(item for item in result["checks"] if item["requirement"] == "Fixed 30-day collection window")
    assert check["status"] == "blocked"


def test_malformed_source_strata_do_not_pass():
    config = load_template()
    config["sampling_frame"]["source_strata"] = [None]
    result = evaluate_config(config)
    check = next(item for item in result["checks"] if item["requirement"] == "Source strata and selection procedure")
    assert check["status"] == "blocked"


def test_timezone_name_and_timestamp_syntax_are_checked():
    config = load_template()
    config["collection_window"].update({"start": "2026-01-01 00:00:00+05:30", "end": "2026-01-31 00:00:00+05:30", "timezone": "Not/A_Timezone"})
    result = evaluate_config(config)
    check = next(item for item in result["checks"] if item["requirement"] == "Fixed 30-day collection window")
    assert check["status"] == "blocked"


def test_invalid_approval_timestamp_does_not_pass():
    config = load_template()
    config["operational_authorization"] = {"status": "approved", "approved_by": "operator-1", "approved_at": "2026-01-01 00:00:00+05:30"}
    result = evaluate_config(config)
    check = next(item for item in result["checks"] if item["requirement"] == "Operational collection authorization")
    assert check["status"] == "blocked"


def test_missing_reviewer_setup_prevents_readiness():
    config = load_template()
    config["reviewers"]["setup_status"] = "assigned"
    config["reviewers"]["operational_authorization"] = True
    config["reviewers"]["reviewer_ids"] = ["placeholder_reviewer_a", "placeholder_reviewer_b"]
    config["reviewers"]["adjudicator_id"] = "placeholder_adjudicator"
    result = evaluate_config(config)
    check = next(item for item in result["checks"] if item["requirement"] == "Reviewer and adjudicator setup")
    assert check["status"] == "blocked"


def test_missing_privacy_decisions_prevent_readiness():
    config = load_template()
    config["privacy_and_retention"]["status"] = "approved"
    result = evaluate_config(config)
    check = next(item for item in result["checks"] if item["requirement"] == "Privacy, access, and evidence-retention decisions")
    assert check["status"] == "blocked"


def test_unavailable_evidence_is_not_contradiction():
    record = {
        "id": "case-1",
        "vacancy_group": "group-1",
        "partition": "test",
        "authorization_label": "unresolved",
        "evidence": [{"id": "e-1", "evidence_state": "unavailable"}],
    }
    assert validate_evaluation_record(record) == []
    assert record["authorization_label"] != "contradicted"
    assert naive([{"id": "e-1", "evidence_state": "unavailable"}]).state == "unresolved"


def test_original_annotations_are_preserved_as_adjudication_references():
    originals = [
        {"annotation_id": "a-1", "annotation_type": "independent_original", "reviewer_id": "r1", "authorization_label": "supported"},
        {"annotation_id": "a-2", "annotation_type": "independent_original", "reviewer_id": "r2", "authorization_label": "unresolved"},
    ]
    before = copy.deepcopy(originals)
    adjudications = [{"adjudication_id": "adj-1", "original_annotation_ids": ["a-1", "a-2"], "original_annotation_fingerprints": {item["annotation_id"]: annotation_fingerprint(item) for item in originals}, "adjudicator_id": "adjudicator", "authorization_label": "unresolved"}]
    assert validate_annotation_bundle(originals, adjudications) == []
    assert originals == before
    originals[0]["authorization_label"] = "unresolved"
    assert any("changed or fingerprint" in error for error in validate_annotation_bundle(originals, adjudications))


def test_related_groups_cannot_cross_partitions_and_test_ids_are_stable():
    manifest = [
        {"id": "a", "vacancy_group": "g1", "partition": "test"},
        {"id": "b", "vacancy_group": "g1", "partition": "test"},
    ]
    assert validate_split_manifest(manifest) == []
    assert frozen_test_id_differences(manifest, manifest) == {"added": [], "removed": [], "group_changed": [], "partition_changed": []}
    changed = manifest + [{"id": "c", "vacancy_group": "g2", "partition": "test"}]
    assert frozen_test_id_differences(changed, manifest)["added"] == ["c"]
    changed_group = [{"id": "a", "vacancy_group": "g2", "partition": "test"}, manifest[1]]
    assert frozen_test_id_differences(changed_group, manifest)["group_changed"] == ["a"]


def test_metrics_handle_zero_denominators_and_false_assurance():
    no_non_supported = selective_metrics(["supported"], ["supported"], [False])
    assert no_non_supported["false_assurance"] is None
    result = selective_metrics(["supported", "unresolved"], ["supported", "supported"], [False, False])
    assert result["false_assurance_count"] == 1
    assert result["false_assurance_denominator"] == 1
    abstained_non_supported = selective_metrics(["supported", "unresolved"], ["supported", "unresolved"], [False, True])
    assert abstained_non_supported["false_assurance_denominator"] == 1
    assert abstained_non_supported["false_assurance"] == 0.0


def test_frozen_baseline_manifest_still_matches():
    result = verify_frozen_snapshot(ROOT / "artifacts" / "experiments" / "research_v1_frozen")
    assert result["status"] == "ready"
