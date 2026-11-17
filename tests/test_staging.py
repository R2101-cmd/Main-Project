import csv

import pytest

from src.datasets.staging import load_staging_csv

FIELDS = ["case_id", "employer_id", "job_title", "job_description", "location", "application_url", "advertisement_url", "platform_type", "cohort_id", "source_family_id", "source_instance_id", "retrieval_event_id", "source_url", "official_employer_url", "canonical_vacancy_id", "retrieved_at", "response_hash", "evidence_state", "source_independence", "lineage_candidate_id", "confirmed_lineage_id"]

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

def row(case_id, **overrides):
    base = {field: "" for field in FIELDS}
    base.update({"case_id": case_id, "employer_id": "EMP", "job_title": "Engineer", "cohort_id": "stripe", "source_family_id": "greenhouse", "source_instance_id": case_id, "retrieval_event_id": "event-" + case_id, "source_url": "https://example.com/jobs/1", "evidence_state": "unresolved", "source_independence": "unknown"})
    base.update(overrides)
    return base

def test_staging_is_read_only_and_keeps_candidates_distinct(tmp_path):
    path = tmp_path / "rows.csv"
    write_csv(path, [row("a", lineage_candidate_id="candidate-1"), row("n", platform_type="Naukri")])
    loaded = load_staging_csv(path)
    assert len(loaded.rows) == 1
    assert loaded.rows[0]["lineage"]["status"] == "candidate"
    assert loaded.summary["excluded_naukri"] == 1
    assert loaded.summary["read_only"] is True
    assert loaded.summary["supervised_labels_assigned"] is False

def test_cohort_filter_and_provenance_are_preserved(tmp_path):
    path = tmp_path / "rows.csv"
    write_csv(path, [row("a", response_hash="hash-a"), row("b", cohort_id="stage4f", response_hash="hash-b")])
    loaded = load_staging_csv(path, cohort="stripe")
    assert [item["case_id"] for item in loaded.rows] == ["a"]
    assert loaded.rows[0]["provenance"]["response_hash"] == "hash-a"
    assert loaded.summary["excluded_cohort"] == 1

def test_duplicate_retrieval_event_is_rejected(tmp_path):
    path = tmp_path / "rows.csv"
    write_csv(path, [row("a", retrieval_event_id="same"), row("b", retrieval_event_id="same")])
    with pytest.raises(ValueError, match="duplicate retrieval_event_id"):
        load_staging_csv(path)

def test_historical_official_confirmation_is_snapshot_only_not_authorization(tmp_path):
    path = tmp_path / "rows.csv"
    write_csv(path, [row("a", evidence_state="independent_official_confirmation")])
    loaded = load_staging_csv(path)
    assert loaded.rows[0]["evidence_state"] == "snapshot_match_only"
    assert loaded.summary["evidence_states"] == {"snapshot_match_only": 1}
