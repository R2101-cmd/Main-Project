"""Run Stage 7B A/B/C evaluation on the validated benchmark v2 split."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation.synthetic_v2 import run_evaluation

SOURCE = ROOT / "research-data" / "phase2_v1" / "synthetic" / "synthetic_benchmark_v2"
SPLITS = SOURCE / "splits"
OUTPUT = ROOT / "final_completion_package" / "synthetic_evaluation_v2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--split-dir", type=Path, default=SPLITS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = run_evaluation(args.source_dir, args.split_dir, args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "test_n": result["manifest"]["test_records"], "metrics": result["metrics"], "paired_B_vs_C": result["statistical_comparison"]["paired_B_vs_C"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
