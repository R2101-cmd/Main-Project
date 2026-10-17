import json

from src.datasets.importer import import_csv, normalize_text


def test_import_preserves_source_label_and_unresolved_authorization(tmp_path):
    source = tmp_path / "jobs.csv"
    source.write_text("job_id,title,location,company_profile,description,requirements,benefits,fraudulent\n1,Data Analyst,London,Acme,Analyze data,SQL,,None\n2,Data Analyst,London,Acme,Analyze data,SQL,,None\n3,Designer,Paris,Other,Create designs,,,1\n", encoding="utf-8")
    output = tmp_path / "out.jsonl"
    report = import_csv(source, output)
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert report.total_rows == 3
    assert report.output_rows == 2
    assert report.duplicate_job_ids == 0
    assert all(record["authorization_label"] == "unresolved" for record in records)
    assert records[1]["source_fraud_label"] == "1"
    assert records[0]["original_title"] == "Data Analyst"
    assert records[0]["normalized_title"] == "data analyst"


def test_exact_duplicates_and_repost_candidates_are_reported_not_merged(tmp_path):
    source = tmp_path / "jobs.csv"
    source.write_text("job_id,title,location,company_profile,description,requirements,benefits,fraudulent\n1,Analyst,London,Acme,Analyze sales data with SQL and Python,SQL Python,,,\n2,Analyst,London,Acme,Analyze sales data with SQL and Python,SQL Python,,,\n3,Analyst,London,Acme,Analyze sales data using SQL and Python,SQL Python,,,\n", encoding="utf-8")
    output = tmp_path / "out.jsonl"
    report = import_csv(source, output)
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert report.exact_duplicate_rows == 1
    assert report.potential_repost_pairs >= 1
    assert len(records) == 2
    assert len({record["record_id"] for record in records}) == 2
    assert len({record["partition"] for record in records}) == 1
    assert records[0]["duplicate_source_record_ids"] == ["2"]


def test_normalization_preserves_meaningful_text():
    assert normalize_text("Café & Data Analyst") == "café data analyst"
