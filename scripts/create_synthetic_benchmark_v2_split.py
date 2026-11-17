"""Create or independently validate the Stage 7A group-aware split."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.datasets.benchmark_split_v2 import SPLIT_SEED, create_split, validate_split

SOURCE = ROOT / "research-data" / "phase2_v1" / "synthetic" / "synthetic_benchmark_v2"
OUTPUT = SOURCE / "splits"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--seed", type=int, default=SPLIT_SEED)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if not args.validate:
        print(json.dumps(create_split(args.source_dir, args.output_dir, args.seed), indent=2, sort_keys=True))
    errors = validate_split(args.source_dir, args.output_dir)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"valid": True, "source_dir": str(args.source_dir.resolve()), "output_dir": str(args.output_dir.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
