"""Build a non-destructive, descriptive union of the proposed and Naukri cohorts.

The union is not a labeled evaluation set. Each source cohort and its raw source
fields remain traceable; no labels, cross-cohort lineage, or official authority
are inferred by this adapter.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "DatasetCollection/final_research_package/unified_proposed_dataset.csv"
NAUKRI = ROOT / "DatasetCollection/final_research_package/naukri_separate_cohort.csv"
OUTPUT = ROOT / "data/processed/real_world_corpus_v2.csv"
REPORT = ROOT / "data/processed/real_world_corpus_v2_report.json"
FIELDS = [
    "corpus_id", "source_cohort", "case_id", "employer_id", "employer_name",
    "job_title", "job_description", "location", "salary", "posting_date",
    "observed_at", "source_url", "application_url", "ats_platform",
    "source_family", "source_type", "source_job_id", "vacancy_group",
    "authorization_label", "annotation_status", "lineage_status", "raw_source_file",
]


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build() -> dict:
    main_rows = _read(MAIN)
    naukri_rows = _read(NAUKRI)
    records: list[dict[str, str]] = []
    for ordinal, row in enumerate(main_rows, start=1):
        case_id = row.get("case_id", "")
        records.append({
            "corpus_id": f"main:{case_id or ordinal}",
            "source_cohort": row.get("cohort_id", "main_proposed"),
            "case_id": case_id,
            "employer_id": row.get("employer_id", ""),
            "employer_name": row.get("employer_name", ""),
            "job_title": row.get("job_title", ""),
            "job_description": row.get("job_description", ""),
            "location": row.get("location", ""),
            "salary": row.get("salary_text", ""),
            "posting_date": row.get("publication_date", ""),
            "observed_at": row.get("retrieval_timestamp", ""),
            "source_url": row.get("original_source_url", ""),
            "application_url": row.get("official_employer_url", ""),
            "ats_platform": row.get("ats_platform", ""),
            "source_family": row.get("source_family_id", ""),
            "source_type": row.get("source_type", ""),
            "source_job_id": row.get("job_identifier", ""),
            "vacancy_group": row.get("canonical_vacancy_id", "") or case_id,
            "authorization_label": "",
            "annotation_status": "unreviewed_import",
            "lineage_status": row.get("confirmed_lineage_status", "not_adjudicated"),
            "raw_source_file": "unified_proposed_dataset.csv",
        })
    for ordinal, row in enumerate(naukri_rows, start=1):
        case_id = row.get("case_id", "")
        records.append({
            "corpus_id": f"naukri:{case_id or ordinal}",
            "source_cohort": "naukri_separate_audit_cohort",
            "case_id": case_id,
            "employer_id": row.get("employer_id", ""),
            "employer_name": row.get("source_employer_name", ""),
            "job_title": row.get("job_title", ""),
            "job_description": row.get("job_description", ""),
            "location": row.get("location", ""),
            "salary": row.get("salary_text", ""),
            "posting_date": row.get("source_created_date", ""),
            "observed_at": row.get("observed_at", ""),
            "source_url": row.get("advertisement_url", ""),
            "application_url": row.get("application_url", ""),
            "ats_platform": "",
            "source_family": row.get("platform_type", "naukri"),
            "source_type": row.get("input_type", "third_party_job_portal"),
            "source_job_id": row.get("source_job_id", ""),
            "vacancy_group": case_id,
            "authorization_label": "",
            "annotation_status": "unreviewed_import",
            "lineage_status": "not_adjudicated",
            "raw_source_file": "naukri_separate_cohort.csv",
        })
    if len({row["corpus_id"] for row in records}) != len(records):
        raise ValueError("duplicate corpus IDs; source cohort keys are not unique")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    report = {
        "dataset": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "records": len(records),
        "input_counts": {"main_proposed": len(main_rows), "naukri_separate_audit": len(naukri_rows)},
        "cohorts": dict(Counter(row["source_cohort"] for row in records)),
        "distinct_employer_ids": len({row["employer_id"] for row in records if row["employer_id"]}),
        "source_families": dict(Counter(row["source_family"] or "unknown" for row in records)),
        "authorization_labels_assigned": 0,
        "confirmed_cross_cohort_lineage_assigned": 0,
        "evaluation_eligible": False,
        "limitations": [
            "The union adds descriptive source coverage only; it is not a reviewed benchmark.",
            "The Naukri cohort remains separately identified and requires compatibility and lineage audit before benchmark use.",
            "No authorization or fraud labels, official source authority, or cross-cohort duplicates were inferred.",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=False))
