"""Create a deterministic vacancy-group split without rewriting source records."""
from __future__ import annotations
import argparse, json, random
from pathlib import Path

def main():
    p = argparse.ArgumentParser(); p.add_argument("source"); p.add_argument("output"); p.add_argument("--seed", type=int, default=42); p.add_argument("--test", type=float, default=.2); p.add_argument("--validation", type=float, default=.2); args = p.parse_args()
    records = [json.loads(x) for x in Path(args.source).read_text(encoding="utf-8").splitlines() if x.strip()]
    groups = {}
    for row in records: groups.setdefault(row.get("vacancy_group") or row.get("split_group") or row["id"], []).append(row)
    keys = list(groups); random.Random(args.seed).shuffle(keys)
    n_test = max(1, round(len(keys) * args.test)); n_val = max(1, round(len(keys) * args.validation))
    test, validation = set(keys[:n_test]), set(keys[n_test:n_test+n_val])
    output = []
    for row in records:
        row = dict(row); group = row.get("vacancy_group") or row.get("split_group") or row["id"]
        row["partition"] = "test" if group in test else "validation" if group in validation else "train"
        output.append(row)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in output) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(output), "groups": len(keys), "train_groups": len(keys)-len(test)-len(validation), "validation_groups": len(validation), "test_groups": len(test), "seed": args.seed}, indent=2))
if __name__ == "__main__": main()
