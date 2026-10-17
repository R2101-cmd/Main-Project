from src.datasets.importer import import_csv


def test_missing_job_ids_are_not_reported_as_duplicate_ids(tmp_path):
    source = tmp_path / "jobs.csv"
    source.write_text("title,location,description,fraudulent\nAnalyst,London,Analyze data,f\nDesigner,Paris,Create designs,t\n", encoding="utf-8")
    report = import_csv(source, tmp_path / "out.jsonl")
    assert report.duplicate_job_ids == 0
