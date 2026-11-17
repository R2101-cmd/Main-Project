"""Validate a research staging CSV without database writes."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.datasets.staging import load_staging_csv

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--cohort")
    parser.add_argument("--include-naukri", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = load_staging_csv(args.csv_path, cohort=args.cohort, include_naukri=args.include_naukri)
    payload = {"path": result.path, "summary": result.summary}
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()
