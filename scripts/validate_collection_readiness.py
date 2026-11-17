"""Run the pre-collection gate and write a human-readable readiness report.

This command never collects sources or creates benchmark records.  The template
is intentionally expected to fail until human decisions are completed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.collection_readiness import evaluate_config


def render_report(result: dict, config_path: Path, frozen_root: Path) -> str:
    lines = [
        "# Collection-readiness report",
        "",
        "This report is a pre-collection gate. It does not collect records, assign labels, or validate the research hypothesis.",
        "",
        f"- Configuration: `{config_path.as_posix()}`",
        f"- Configuration fingerprint: `{result['configuration_fingerprint']}`",
        f"- Frozen baseline checked: `{frozen_root.as_posix()}`",
        f"- Overall status: **{'COLLECTION READY' if result['collection_ready'] else 'NOT COLLECTION READY'}**",
        "",
        "| Requirement | Status | Reason | Corrective action |",
        "|---|---|---|---|",
    ]
    for check in result["checks"]:
        reason = check["reason"].replace("|", "\\|")
        action = check["corrective_action"].replace("|", "\\|")
        lines.append(f"| {check['requirement']} | {check['status']} | {reason} | {action} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "`pending` means a human or operational decision is not yet supplied. `blocked` means the supplied configuration is invalid or contradictory. Collection must not begin unless every check is `ready`.",
        "",
        "The 100–200 vacancy-group target is a feasibility target, not a guarantee of statistical power. Reviewer identities, independent annotation, adjudication, and a new frozen test set remain human-process requirements.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/collection_config_v1.json")
    parser.add_argument("--frozen-root", default="artifacts/experiments/research_v1_frozen")
    parser.add_argument("--report", default="docs/collection_readiness_report.md")
    parser.add_argument("--json-report", default="artifacts/readiness/collection_readiness.json")
    args = parser.parse_args()

    config_path = ROOT / args.config
    frozen_root = ROOT / args.frozen_root
    report_path = ROOT / args.report
    json_path = ROOT / args.json_report
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        result = evaluate_config(config, frozen_root=frozen_root)
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "collection_ready": False,
            "configuration_fingerprint": "unavailable",
            "checks": [{"requirement": "Configuration file", "status": "blocked", "reason": str(exc), "corrective_action": "Provide a readable valid JSON configuration object."}],
            "required_schema_versions": {},
        }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result, config_path.relative_to(ROOT), frozen_root.relative_to(ROOT)), encoding="utf-8")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["collection_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

