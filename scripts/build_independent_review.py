import json
from pathlib import Path

source = Path("data/annotations/job_ad_authorization_evaluation.jsonl")
target = Path("data/annotations/job_ad_independent_review_v1.jsonl")

# This subset is selected before reading predictions. Direct institutional/employer
# records are supported; aggregator/search-only records remain unresolved.
selected = {
    "JA001", "JA002", "JA003", "JA004", "JA005", "JA006", "JA007", "JA008", "JA009",
    "JA010", "JA011", "JA012", "JA013", "JA014", "JA015", "JA016", "JA017", "JA018", "JA019", "JA020",
    "JA035", "JA036", "JA037", "JA038", "JA039", "JA040", "JA041", "JA042", "JA043", "JA044", "JA045",
}
test_ids = {"JA001", "JA003", "JA004", "JA005", "JA010", "JA012", "JA013", "JA035", "JA037", "JA039", "JA041", "JA043"}
supported_ids = {"JA010", "JA035", "JA036", "JA037", "JA038", "JA039", "JA040", "JA041", "JA042", "JA043", "JA044", "JA045"}

records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
reviewed = []
for record in records:
    if record["id"] not in selected:
        continue
    record = dict(record)
    record["partition"] = "test" if record["id"] in test_ids else "train"
    record["authorization_label"] = "supported" if record["id"] in supported_ids else "unresolved"
    record["annotation_status"] = "single_reviewer_provisional_v1"
    record["reviewer_id"] = "codex_protocol_review_pending_human_confirmation"
    if record["authorization_label"] == "supported":
        record["annotation_rationale"] = "Independent protocol review: direct employer or institutional source supports the exact vacancy, employer, and role; final fraud outcome is not inferred."
    else:
        record["annotation_rationale"] = "Independent protocol review: available source is insufficient for vacancy-specific authorization; unresolved is retained rather than inferring fraud."
    reviewed.append(record)

groups = {}
for record in reviewed:
    groups.setdefault(record["vacancy_group"], set()).add(record["partition"])
leakage = [group for group, partitions in groups.items() if len(partitions) > 1]
if leakage:
    raise RuntimeError(f"lineage leakage: {leakage}")

target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in reviewed) + "\n", encoding="utf-8")
print(f"wrote {len(reviewed)} reviewed records to {target}")
print(f"train={sum(r['partition']=='train' for r in reviewed)} test={sum(r['partition']=='test' for r in reviewed)}")
