import csv
import hashlib
import html
import json
import re
import shutil
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "dataset_naukri-job-scraper_2026-11-10_07-56-33-603.csv"
RAW = ROOT / "raw" / SOURCE.name
PROCESSED = ROOT / "processed"
REVIEWS = ROOT / "review_templates"
REPORTS = ROOT / "reports"
for folder in (RAW.parent, PROCESSED, REVIEWS, REPORTS):
    folder.mkdir(exist_ok=True)

if not RAW.exists():
    shutil.copy2(SOURCE, RAW)


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    return value.strip()


def normalize_name(value):
    value = clean_text(value).casefold()
    value = re.sub(r"[^\w\s&.-]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def normalize_url(value):
    value = clean_text(value)
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        if not parts.scheme or not parts.netloc:
            return value.rstrip("/")
        host = parts.hostname.casefold() if parts.hostname else ""
        if parts.port:
            host += f":{parts.port}"
        netloc = host
        if parts.username:
            netloc = parts.username + (f":{parts.password}" if parts.password else "") + "@" + host
        path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
        return urlunsplit((parts.scheme.casefold(), netloc, path, parts.query, ""))
    except ValueError:
        return value.rstrip("/")


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
    raw_rows = list(csv.DictReader(f))
fieldnames = list(raw_rows[0].keys()) if raw_rows else []

blank_rows = [i + 2 for i, r in enumerate(raw_rows) if not any((v or "").strip() for v in r.values())]
rows = [r for r in raw_rows if any((v or "").strip() for v in r.values())]
exact_keys = [tuple((r.get(c) or "") for c in fieldnames) for r in raw_rows]
exact_counts = Counter(exact_keys)
exact_duplicate_groups = sum(1 for count in exact_counts.values() if count > 1)
exact_duplicate_rows = sum(count for count in exact_counts.values() if count > 1)

def dup_groups(key):
    groups = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        value = clean_text(row.get(key, ""))
        if value:
            groups[value].append(index)
    return {k: v for k, v in groups.items() if len(v) > 1}

dup_job = dup_groups("jobId")
dup_ad = dup_groups("jdURL")
dup_apply = dup_groups("applyRedirectUrl")

file_observed = datetime.fromtimestamp(SOURCE.stat().st_mtime, timezone.utc).isoformat()
employer_ids = {}
case_ids = {}
cleaned = []
for row in rows:
    company = clean_text(row.get("companyName", ""))
    company_norm = normalize_name(company)
    employer_ids.setdefault(company_norm, "emp_" + hashlib.sha256(company_norm.encode()).hexdigest()[:16])
    source_id = clean_text(row.get("jobId", ""))
    case_ids[source_id] = str(uuid.uuid4())
    ad_url = normalize_url(row.get("jdURL", ""))
    application = normalize_url(row.get("applyRedirectUrl", "")) or normalize_url(row.get("companyApplyUrl", ""))
    cleaned.append({
        "case_id": case_ids[source_id],
        "employer_id": employer_ids[company_norm],
        "job_title": clean_text(row.get("title", "")),
        "job_description": clean_text(row.get("jobDescription", "")),
        "location": clean_text(row.get("location", "")),
        "salary_text": clean_text(row.get("salary", "")),
        "contact_details": "",
        "application_url": application,
        "advertisement_url": ad_url,
        "platform_type": "job portal (Naukri)",
        "input_type": "URL",
        "observed_at": file_observed,
        "source_job_id": source_id,
        "source_employer_name": company,
        "source_company_id": clean_text(row.get("companyId", "")),
        "source_created_date": clean_text(row.get("createdDate", "")),
        "source_file": SOURCE.name,
    })

table_a_fields = list(cleaned[0].keys()) if cleaned else []
write_csv(PROCESSED / "vacancyguard_table_a_cleaned.csv", cleaned, table_a_fields)

# Candidate lineage: no records are removed. Exact URL/job matches are deterministic;
# other candidates use conservative text similarity and shared employer/location signals.
def desc_norm(row):
    return re.sub(r"\W+", " ", clean_text(row.get("jobDescription", "")).casefold()).strip()

lineage = []
for i, left in enumerate(rows):
    for j in range(i + 1, len(rows)):
        right = rows[j]
        left_ad, right_ad = normalize_url(left.get("jdURL", "")), normalize_url(right.get("jdURL", ""))
        left_apply, right_apply = normalize_url(left.get("applyRedirectUrl", "")), normalize_url(right.get("applyRedirectUrl", ""))
        same_job = bool(left.get("jobId") and left.get("jobId") == right.get("jobId"))
        same_ad = bool(left_ad and left_ad == right_ad)
        same_apply = bool(left_apply and left_apply == right_apply)
        sim = SequenceMatcher(None, desc_norm(left), desc_norm(right)).ratio()
        same_employer = normalize_name(left.get("companyName", "")) == normalize_name(right.get("companyName", ""))
        same_location = normalize_name(left.get("location", "")) == normalize_name(right.get("location", ""))
        same_title = normalize_name(left.get("title", "")) == normalize_name(right.get("title", ""))
        if same_job or same_ad or same_apply or sim >= 0.88 or (same_employer and same_title and same_location and sim >= 0.65):
            signals = []
            if same_job: signals.append("same jobId")
            if same_ad: signals.append("same normalized advertisement URL")
            if same_apply: signals.append("same normalized application URL")
            if same_employer: signals.append("same normalized employer")
            if same_title: signals.append("same normalized title")
            if same_location: signals.append("same normalized location")
            if sim >= 0.65: signals.append(f"description similarity={sim:.3f}")
            relationship = "copied/derived candidate" if (same_ad or same_apply or sim >= 0.88) else "related candidate"
            lineage.append({
                "lineage_group_id": "LG-" + hashlib.sha256((left.get("jobId", "") + "|" + right.get("jobId", "")).encode()).hexdigest()[:12],
                "source_relationship": relationship,
                "related_case_ids": case_ids.get(left.get("jobId", ""), "") + ";" + case_ids.get(right.get("jobId", ""), ""),
                "lineage_signals": "; ".join(signals),
                "lineage_review_status": "automated candidate",
                "lineage_rationale": "Similarity or shared identifiers indicate a possible duplicate/repost family; manual review is required before asserting lineage.",
                "similarity_score": f"{sim:.3f}",
                "left_source_job_id": left.get("jobId", ""),
                "right_source_job_id": right.get("jobId", ""),
            })
write_csv(PROCESSED / "vacancyguard_table_d_lineage_candidates.csv", lineage, list(lineage[0].keys()) if lineage else ["lineage_group_id", "source_relationship", "related_case_ids", "lineage_signals", "lineage_review_status", "lineage_rationale", "similarity_score", "left_source_job_id", "right_source_job_id"])

table_b = [{
    "case_id": r["case_id"], "employer_identity_label": "unresolved", "vacancy_authorization_label": "unresolved", "fraud_outcome_label": "unresolved", "label_rationale": "", "label_evidence_refs": "", "annotator_id": "", "adjudication_status": "unreviewed"
} for r in cleaned]
write_csv(REVIEWS / "vacancyguard_table_b_ground_truth_review.csv", table_b, list(table_b[0].keys()) if table_b else [])

evidence_fields = ["evidence_id", "case_id", "claim_type", "source_url", "source_type", "retrieved_at", "source_published_at", "evidence_state", "matched_fields", "contradiction_details", "evidence_rationale"]
write_csv(REVIEWS / "vacancyguard_table_c_evidence_review.csv", [], evidence_fields)

missing = {c: sum(1 for r in raw_rows if not (r.get(c) or "").strip()) for c in fieldnames}
duplicate_report = {"jobId": dup_job, "jdURL": dup_ad, "applyRedirectUrl": dup_apply}
report = {
    "source_file": SOURCE.name,
    "source_file_size_bytes": SOURCE.stat().st_size,
    "source_columns": fieldnames,
    "expected_records_reported_by_user": 240,
    "records_in_source_csv": len(raw_rows),
    "blank_rows_removed_from_cleaned_output": len(blank_rows),
    "records_in_cleaned_output": len(cleaned),
    "exact_duplicate_record_groups": exact_duplicate_groups,
    "exact_duplicate_record_rows_in_groups": exact_duplicate_rows,
    "duplicate_jobId_groups": len(dup_job),
    "duplicate_jobId_rows_in_groups": sum(len(v) for v in dup_job.values()),
    "duplicate_advertisement_url_groups": len(dup_ad),
    "duplicate_advertisement_url_rows_in_groups": sum(len(v) for v in dup_ad.values()),
    "duplicate_application_url_groups": len(dup_apply),
    "duplicate_application_url_rows_in_groups": sum(len(v) for v in dup_apply.values()),
    "lineage_candidate_pairs": len(lineage),
    "manual_review_required": len(lineage),
    "missing_values_by_column": missing,
    "duplicate_groups": duplicate_report,
    "assumptions": [
        "observed_at uses the source CSV filesystem modification time because no collection timestamp field was supplied",
        "Naukri data alone is not used to assign legitimacy or fraud labels",
        "employer_id is a stable hash of the normalized company name; same-named employers remain unresolved until independently verified",
        "lineage candidates are retained and require human review",
    ],
}
(REPORTS / "inspection_and_cleaning_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

summary = [
    "TrustHire cleaning report",
    f"Source: {SOURCE.name}",
    f"User-reported records: 240",
    f"Records found in source CSV: {len(raw_rows)}",
    f"Blank rows removed: {len(blank_rows)}",
    f"Cleaned records written: {len(cleaned)}",
    f"Duplicate jobId groups: {len(dup_job)}",
    f"Duplicate advertisement URL groups: {len(dup_ad)}",
    f"Duplicate application URL groups: {len(dup_apply)}",
    f"Lineage candidate pairs requiring manual review: {len(lineage)}",
    "Ground-truth and evidence labels are initialized as unresolved/unreviewed.",
]
(REPORTS / "cleaning_summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
print("\n".join(summary))
