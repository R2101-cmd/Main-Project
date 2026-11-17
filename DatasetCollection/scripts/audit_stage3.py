"""Validate Table B and match Table A to the preserved Greenhouse snapshot.

This stage is deliberately non-destructive: it never changes Table A, Table B,
or prior Stage 2 review files. Recommendations are written separately from
the unresolved ground-truth labels.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
PROCESSED = ROOT / "processed"

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def norm(value):
    value = unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip().casefold()

def sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def job_id_from_case(case_id):
    match = re.search(r"_(\d+)$", case_id or "")
    return match.group(1) if match else ""

table_a = read_csv(PROCESSED / "table_A_advertisements.csv")
table_b = read_csv(PROCESSED / "table_B_ground_truth.csv")
with (ROOT / "raw/greenhouse/greenhouse_raw.json").open(encoding="utf-8") as handle:
    greenhouse = json.load(handle)
jobs = greenhouse.get("jobs", [])

required_b = [
    "case_id", "employer_identity_label", "vacancy_authorization_label",
    "fraud_outcome_label", "label_rationale", "label_evidence_refs",
    "annotator_id", "adjudication_status",
]
allowed = {
    "employer_identity_label": {"verified", "contradicted", "unresolved"},
    "vacancy_authorization_label": {"supported", "contradicted", "unresolved"},
    "fraud_outcome_label": {"confirmed_fraudulent", "confirmed_legitimate", "unresolved"},
}

a_ids = [row.get("case_id", "") for row in table_a]
b_ids = [row.get("case_id", "") for row in table_b]
count_a, count_b = Counter(a_ids), Counter(b_ids)
validation = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "table_a_records": len(table_a),
    "table_b_records": len(table_b),
    "table_b_columns_exact": list(table_b[0]) == required_b if table_b else False,
    "table_b_missing_ids": sum(not value.strip() for value in b_ids),
    "table_b_duplicate_ids": sum(count - 1 for count in count_b.values() if count > 1),
    "table_a_duplicate_ids": sum(count - 1 for count in count_a.values() if count > 1),
    "ids_missing_from_table_b": len(set(a_ids) - set(b_ids)),
    "ids_missing_from_table_a": len(set(b_ids) - set(a_ids)),
    "invalid_label_values": {
        field: sorted({row.get(field, "") for row in table_b if row.get(field, "") not in values})
        for field, values in allowed.items()
    },
    "table_b_label_counts": {
        field: dict(Counter(row.get(field, "") for row in table_b))
        for field in allowed
    },
    "table_b_linkable_to_table_c": "case_id is linkable; no canonical full Table C existed before this stage",
}

job_by_id = {str(job.get("id")): job for job in jobs if job.get("id") is not None}
evidence = []
matches = []
for index, ad in enumerate(table_a, 1):
    job_id = job_id_from_case(ad.get("case_id", ""))
    job = job_by_id.get(job_id)
    if job is None:
        matches.append({
            "case_id": ad.get("case_id", ""), "source_job_id": job_id,
            "match_status": "unavailable", "matched_fields": "",
            "mismatch_fields": "missing job id in snapshot", "source_url": "",
        })
        continue
    location = job.get("location") if isinstance(job.get("location"), str) else (job.get("location") or {}).get("name", "")
    comparisons = {
        "employer_identity": norm(ad.get("employer_id")) == "emp_stripe" and norm(job.get("company_name")) == "stripe",
        "job_title": norm(ad.get("job_title")) == norm(job.get("title")),
        "job_location": norm(ad.get("location")) == norm(location),
        "job_description": norm(ad.get("job_description")) == norm(job.get("content")),
        "vacancy_url": ad.get("application_url", "") == job.get("absolute_url", ""),
    }
    matched = [key for key, value in comparisons.items() if value]
    mismatched = [key for key, value in comparisons.items() if not value]
    state = "supported" if len(matched) == len(comparisons) else "unverified"
    rationale = (
        "Official Greenhouse snapshot matches the advertisement on employer, title, location, description, and vacancy URL. "
        "This is source-snapshot evidence; human adjudication remains required."
        if state == "supported" else
        "Official Greenhouse job ID was found, but one or more advertisement fields differ from the snapshot; retain for manual review."
    )
    evidence.append({
        "evidence_id": f"GH-{index:04d}", "case_id": ad["case_id"],
        "claim_type": "employer identity and vacancy authorization",
        "source_url": job.get("absolute_url", ""),
        "source_type": "official Greenhouse job board API snapshot",
        "retrieved_at": greenhouse.get("retrieved_at", ""),
        "source_published_at": job.get("first_published", ""),
        "evidence_state": state, "matched_fields": "; ".join(matched),
        "contradiction_details": "; ".join(mismatched), "evidence_rationale": rationale,
        "retrieval_outcome": "snapshot record available; live HTTP status not asserted",
        "source_job_id": job_id, "requisition_id": job.get("requisition_id", ""),
        "source_updated_at": job.get("updated_at", ""),
        "description_sha256": sha256(norm(job.get("content", ""))),
    })
    matches.append({
        "case_id": ad["case_id"], "source_job_id": job_id, "match_status": state,
        "matched_fields": "; ".join(matched), "mismatch_fields": "; ".join(mismatched),
        "source_url": job.get("absolute_url", ""),
    })

evidence_fields = list(evidence[0]) if evidence else []
write_csv(PROCESSED / "table_C_evidence_records.csv", evidence, evidence_fields)
write_csv(REPORTS / "source_matching_report.csv", matches, list(matches[0]) if matches else ["case_id"])

recommendations = []
evidence_by_case = {row["case_id"]: row for row in evidence}
for row in table_b:
    ev = evidence_by_case.get(row["case_id"])
    recommendation = dict(row)
    recommendation.update({
        "recommended_employer_identity_label": "verified" if ev and ev["evidence_state"] == "supported" else "unresolved",
        "recommended_vacancy_authorization_label": "supported" if ev and ev["evidence_state"] == "supported" else "unresolved",
        "recommended_fraud_outcome_label": "unresolved",
        "review_basis": ev["evidence_id"] if ev else "",
        "review_note": "Recommendation only; human adjudication required. Source snapshot does not by itself establish fraud outcome." if ev else "No matching official snapshot record; manual review required.",
    })
    recommendations.append(recommendation)
write_csv(PROCESSED / "table_B_human_review_preparation.csv", recommendations, list(recommendations[0]))

unresolved = [{
    "case_id": row["case_id"],
    "reason": "human adjudication still pending; fraud outcome intentionally unresolved",
    "evidence_state": evidence_by_case.get(row["case_id"], {}).get("evidence_state", "unavailable"),
} for row in table_b]
write_csv(REPORTS / "unresolved_advertisements.csv", unresolved, list(unresolved[0]))

lineage_path = PROCESSED / "vacancyguard_table_d_lineage_candidates.csv"
lineage_count = len(read_csv(lineage_path)) if lineage_path.exists() else 0
counts = Counter(row["evidence_state"] for row in evidence)
validation["greenhouse_records"] = len(jobs)
validation["evidence_counts"] = dict(counts)
validation["potential_repost_relationships_existing"] = lineage_count
validation["human_review_ready_records"] = len(recommendations)
validation["remaining_unresolved_cases"] = len(unresolved)
(REPORTS / "table_b_validation_report.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
(REPORTS / "scraping_execution_log.json").write_text(json.dumps({
    "stage": "local official-source matching",
    "executed_at": validation["generated_at"],
    "source_file": "raw/greenhouse/greenhouse_raw.json",
    "records_processed": len(table_a), "records_matched_to_snapshot": len(evidence),
    "live_requests_made": 0,
    "http_statuses": "not available; this stage used the preserved snapshot and did not assert live retrieval",
    "restrictions": "No CAPTCHA, authentication, or access restriction was bypassed.",
}, indent=2), encoding="utf-8")

print(json.dumps({
    "validation": validation,
    "outputs": [
        str(PROCESSED / "table_C_evidence_records.csv"),
        str(PROCESSED / "table_B_human_review_preparation.csv"),
        str(REPORTS / "source_matching_report.csv"),
        str(REPORTS / "unresolved_advertisements.csv"),
        str(REPORTS / "table_b_validation_report.json"),
        str(REPORTS / "scraping_execution_log.json"),
    ],
}, indent=2))

