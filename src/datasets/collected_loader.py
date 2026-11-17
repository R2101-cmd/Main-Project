"""Read-only loader for the collected integration package."""
from __future__ import annotations

import csv
from pathlib import Path


DEFAULT_DATASET = Path("DatasetCollection/final_research_package/unified_proposed_dataset.csv")


def load_collected_dataset(path: str | Path = DEFAULT_DATASET, limit: int | None = None) -> list[dict[str, str]]:
    source = Path(path)
    if not source.exists():
        return []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows if limit is None else rows[:limit]


def dataset_inventory(path: str | Path = DEFAULT_DATASET) -> dict:
    rows = load_collected_dataset(path)
    return {"path": str(path), "records": len(rows), "employers": len({r.get("employer_id") for r in rows if r.get("employer_id")}), "cohorts": sorted({r.get("cohort_id") for r in rows if r.get("cohort_id")})}
