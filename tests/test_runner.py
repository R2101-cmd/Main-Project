import json

import pytest

from src.evaluation.runner import run, save_results


def test_pilot_result_is_explicitly_exploratory_and_has_real_methods(tmp_path):
    result = run("data/annotations/pilot.jsonl")
    assert result["evaluation_status"] == "exploratory_insufficient"
    assert result["test_records"] == 1
    assert result["test_independent_vacancy_groups"] == 1
    assert "naive_evidence" in result["methods"]
    assert "lineage_aware_evidence" in result["methods"]
    assert result["methods"]["text_only_baseline"]["status"] == "not_run"
    output = tmp_path / "evaluation.json"
    save_results(result, output)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["dataset_fingerprint"] == result["dataset_fingerprint"]
    assert "confusion_matrix" in saved["methods"]["naive_evidence"]["classification"]


def test_unreviewed_import_cannot_be_scored(tmp_path):
    path = tmp_path / "raw.jsonl"
    path.write_text(json.dumps({"record_id": "r1", "partition": "test", "split_group": "g1", "authorization_label": "unresolved", "annotation_status": "unreviewed_import", "evidence": []}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unreviewed raw imports"):
        run(path)


def test_leakage_is_rejected(tmp_path):
    records = [
        {"id": "a", "vacancy_group": "same", "partition": "train", "authorization_label": "supported", "evidence": []},
        {"id": "b", "vacancy_group": "same", "partition": "test", "authorization_label": "unresolved", "evidence": []},
    ]
    path = tmp_path / "leak.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="lineage/vacancy groups"):
        run(path)
