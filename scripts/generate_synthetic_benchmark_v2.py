"""Build or validate the isolated, synthetic-only 300-case benchmark."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.datasets.synthetic_benchmark_v2 import SEED, build_package, validate_package

DEFAULT_OUT = ROOT / "research-data" / "phase2_v1" / "synthetic" / "synthetic_benchmark_v2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if not args.validate:
        manifest = build_package(args.output, args.seed)
        (args.output / "methodology_limitations.md").write_text(METHODOLOGY, encoding="utf-8")
        print(json.dumps(manifest, indent=2, sort_keys=True))
    errors = validate_package(args.output)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"valid": True, "output": str(args.output.resolve())}, indent=2))
    return 0


METHODOLOGY = """# Synthetic benchmark v2: methodology and limits

This package contains 300 generated cases, balanced across supported, contradicted,
and unresolved expected outcomes (100 each). It contains no real advertisements,
employers, URLs, retrieval events, or independent observations. The fixed generation
seed is 20261114. The expected outcomes are design labels justified by the explicit
synthetic evidence scenario and are not human-reviewed ground truth.

## Separation and mapping

`model_inputs.jsonl` contains only an opaque `input_key`, synthetic advertisement
fields, and synthetic evidence. It omits case IDs, scenario names, expected labels,
and scenario notes. `expected_labels.jsonl` maps every input key to a unique case ID
and expected outcome. `scenario_metadata.jsonl` maps the same key to its scenario and
vacancy group. Both latter files are evaluation-only and must not be supplied to an
approach. `manifest.json` records counts and hashes.

## Scenario construction

Each of 15 scenario families has 20 distinct synthetic vacancies. Support labels
require a current synthetic employer-controlled matching source explicitly marked
independently supported. Contradiction labels require a material, specific current
synthetic employer-controlled denial or mismatch. Unresolved labels represent
conflicting independent reports without resolution, unverified claims with unknown
or absent lineage, stale snapshot-only evidence plus unavailable current sources,
or incomplete records without decisive evidence. Copied reports are assigned one
adjudicated dependent group and cannot be interpreted as multiple independent
confirmations. These conventions make the constructed outcome traceable; they do not
simulate a validated real-world source authorization process.

## Historical artifacts

The 60-record `synthetic_benchmark_v1.jsonl`, the 30-record
`synthetic_benchmark_extended_v1.jsonl`, and the provisional 60-record
`controlled_v2` directory are historical files and remain unchanged. The first two
are retained as historical experiments; their prior splits and metrics are not
reused here. The provisional controlled_v2 manifest records 10 supported, 15
contradicted, and 35 unresolved records, so it is not this balanced benchmark and
its exposed case/scenario fields are not reused as model inputs.

## Limits

This package is for a later controlled software comparison only. No A/B/C inference,
accuracy, precision, recall, F1, calibration, or real-world performance was measured
when generating it. Synthetic coverage is intentionally finite and cannot establish
generalization, fraud prevalence, or operational suitability. Inspect construction
and validation before any later evaluation; freeze the test protocol before viewing
test results.
"""


if __name__ == "__main__":
    raise SystemExit(main())
