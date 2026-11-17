
import json
from pathlib import Path

# Read the original collected data
data_path = (
    Path(__file__).resolve().parent.parent
    / "raw"
    / "greenhouse"
    / "greenhouse_raw.json"
)

with open(data_path, "r", encoding="utf-8") as file:
    data = json.load(file)

jobs = data["jobs"]

fields = [
    "id",
    "title",
    "company_name",
    "content",
    "location",
    "absolute_url",
    "first_published",
    "updated_at",
    "requisition_id",
    "metadata",
]

print("TOTAL RECORDS:", len(jobs))
print("\nFIELD COMPLETENESS:")

for field in fields:
    count = sum(
        1 for job in jobs
        if job.get(field) not in (None, "", {})
    )

    print(f"{field}: {count}/{len(jobs)}")

print("\nData quality check completed.")
