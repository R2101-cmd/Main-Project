import requests
import json
from pathlib import Path
from datetime import datetime, timezone

# Greenhouse public job board API
BOARD_TOKEN = "stripe"

URL = f"https://boards-api.greenhouse.io/v1/boards/{BOARD_TOKEN}/jobs?content=true"

# Request job listings
response = requests.get(URL, timeout=30)
response.raise_for_status()

data = response.json()

jobs = data.get("jobs", [])

print("Total jobs collected:", len(jobs))

# Save original API response
output_folder = Path(__file__).resolve().parent.parent / "raw" / "greenhouse"
output_folder.mkdir(parents=True, exist_ok=True)

output_file = output_folder / "greenhouse_raw.json"

with open(output_file, "w", encoding="utf-8") as file:
    json.dump({
        "source": "Greenhouse",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "total_jobs": len(jobs),
        "jobs": jobs
    }, file, ensure_ascii=False, indent=4)

print("Data saved successfully:", output_file)