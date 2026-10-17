import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.datasets.importer import import_csv

parser = argparse.ArgumentParser(description="Import a public job-posting CSV without assigning authorization labels.")
parser.add_argument("csv_path", nargs="?", default="data/raw/fake_job_postings.csv")
parser.add_argument("--output", default="data/processed/fake_job_postings_imported.jsonl")
parser.add_argument("--report", default="data/processed/fake_job_postings_import_report.json")
args = parser.parse_args()
report = import_csv(args.csv_path, args.output)
Path(args.report).parent.mkdir(parents=True, exist_ok=True)
Path(args.report).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
print(json.dumps(report.to_dict(), indent=2))
