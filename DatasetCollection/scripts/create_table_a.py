
import json
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = ROOT / "raw" / "greenhouse" / "greenhouse_raw.json"
OUTPUT_FILE = ROOT / "processed" / "table_A_advertisements.csv"

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

jobs = data["jobs"]
observed_at = data.get("retrieved_at", "")

columns = [
    "case_id",
    "employer_id",
    "job_title",
    "job_description",
    "location",
    "salary_text",
    "contact_details",
    "application_url",
    "advertisement_url",
    "platform_type",
    "input_type",
    "observed_at",
]

rows = []

for job in jobs:
    company = job.get("company_name") or "UNKNOWN"

    employer_slug = re.sub(
        r"[^A-Z0-9]+", "_", company.upper()
    ).strip("_")

    job_id = job.get("id")

    if job_id is None:
        continue

    location = job.get("location") or {}

    if isinstance(location, dict):
        location = location.get("name", "")

    row = {
        "case_id": f"CASE_GREENHOUSE_{employer_slug}_{job_id}",
        "employer_id": f"EMP_{employer_slug}",
        "job_title": job.get("title", ""),
        "job_description": job.get("content", ""),
        "location": location,
        "salary_text": "",
        "contact_details": "",
        "application_url": job.get("absolute_url", ""),
        "advertisement_url": job.get("absolute_url", ""),
        "platform_type": "official_careers_site",
        "input_type": "API",
        "observed_at": observed_at,
    }

    rows.append(row)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

print("Table A created successfully!")
print("Total records:", len(rows))
print("Output:", OUTPUT_FILE)
