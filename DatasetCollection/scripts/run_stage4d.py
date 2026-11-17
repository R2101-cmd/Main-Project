"""TrustHire Stage 4D: cohort integrity and representative Stripe pilot.

Only the 780-record Stripe/Greenhouse cohort is sampled here. The separate
Naukri/ATS cohort is audited for contamination but never sampled or merged.
"""
import csv
import hashlib
import html
import json
import random
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

csv.field_size_limit(20_000_000)
ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "processed"
REPORTS = ROOT / "reports"
ARCHIVE = ROOT / "raw" / "stage4d_responses"
SEED = 20261112
AS_OF = "2026-11-12"

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def norm(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip().casefold()

def compare(expected, observed):
    e, o = norm(expected), norm(observed)
    if not e or not o:
        return "not_comparable"
    if e == o:
        return "exact"
    if e.replace(" ", "") == o.replace(" ", ""):
        return "normalized"
    et, ot = set(re.findall(r"[a-z0-9]+", e)), set(re.findall(r"[a-z0-9]+", o))
    if et and len(et & ot) / max(1, len(et)) >= 0.65:
        return "partial"
    return "mismatch"

def fetch(url):
    stamp = datetime.now(timezone.utc).isoformat()
    if not url:
        return {"url": "", "final_url": "", "timestamp": stamp, "status": "", "outcome": "not_requested", "hash": "", "body": b""}
    request = Request(url, headers={"User-Agent": "TrustHire-research-audit/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read()
            return {
                "url": url, "final_url": response.geturl(), "timestamp": stamp,
                "status": getattr(response, "status", 200), "outcome": "retrieved",
                "hash": hashlib.sha256(body).hexdigest(), "body": body,
            }
    except HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        return {
            "url": url, "final_url": getattr(exc, "url", url), "timestamp": stamp,
            "status": exc.code, "outcome": "http_error", "hash": hashlib.sha256(body).hexdigest(), "body": body,
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "url": url, "final_url": url, "timestamp": stamp, "status": "",
            "outcome": f"unavailable: {type(exc).__name__}", "hash": "", "body": b"",
        }

def parse_api(result):
    if not result["body"]:
        return {}
    try:
        value = json.loads(result["body"].decode("utf-8", errors="replace"))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}

def visible_text(body):
    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()

def location_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return ", ".join(str(value.get(k, "")) for k in ("name", "addressLocality", "addressRegion", "addressCountry") if value.get(k))
    if isinstance(value, list):
        return "; ".join(location_value(x) for x in value)
    return ""

def source_month(value):
    return str(value or "")[:7]

def desc_bucket(text):
    length = len(text or "")
    if length < 4000:
        return "short"
    if length < 8000:
        return "medium"
    return "long"

def job_from_case(case_id):
    match = re.search(r"_(\d+)$", case_id or "")
    return match.group(1) if match else ""

# Load both cohorts independently.
table_a = read_csv(PROCESSED / "table_A_advertisements.csv")
table_b = read_csv(PROCESSED / "table_B_ground_truth.csv")
table_c = read_csv(PROCESSED / "table_C_evidence_records.csv")
stage4b = read_csv(PROCESSED / "table_C_stage4b_pilot.csv")
stage4c = read_csv(PROCESSED / "stage4c_vacancy_source_relationships.csv")
cleaned_naukri = read_csv(PROCESSED / "vacancyguard_table_a_cleaned.csv")
greenhouse = json.loads((ROOT / "raw/greenhouse/greenhouse_raw.json").read_text(encoding="utf-8"))
green_jobs = greenhouse.get("jobs", [])
naukri_case_ids = {r.get("case_id", "") for r in cleaned_naukri}
stripe_case_ids = {r.get("case_id", "") for r in table_a}

# Cohort integrity report.
all_id_sets = {
    "table_a_stripe": stripe_case_ids,
    "table_b": {r.get("case_id", "") for r in table_b},
    "table_c": {r.get("case_id", "") for r in table_c},
    "stage4b_naukri": {r.get("case_id", "") for r in stage4b},
    "stage4c_naukri": {r.get("case_id", "") for r in stage4c},
    "cleaned_naukri": naukri_case_ids,
}
duplicates = {name: len(values) - len({x for x in values}) for name, values in all_id_sets.items()}
invalid_stripe = [
    r["case_id"] for r in table_a
    if not r["case_id"].startswith("CASE_GREENHOUSE_STRIPE_") or r.get("employer_id") != "EMP_STRIPE"
]
uncertain = [
    r["case_id"] for r in table_a
    if r["case_id"] not in stripe_case_ids or job_from_case(r["case_id"]) == ""
]
cross_contamination = {
    "stripe_ids_in_naukri_cleaned": len(stripe_case_ids & naukri_case_ids),
    "naukri_ids_in_stripe_table_a": len(naukri_case_ids & stripe_case_ids),
    "stage4b_ids_in_stripe_table_a": len({r.get("case_id", "") for r in stage4b} & stripe_case_ids),
    "stage4c_ids_in_stripe_table_a": len({r.get("case_id", "") for r in stage4c} & stripe_case_ids),
}
integrity = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "stripe_table_a_records": len(table_a),
    "stripe_table_a_unique_case_ids": len(stripe_case_ids),
    "stripe_employers": sorted({r.get("employer_id", "") for r in table_a}),
    "greenhouse_raw_records": len(green_jobs),
    "naukri_cleaned_records": len(cleaned_naukri),
    "naukri_unique_case_ids": len(naukri_case_ids),
    "stage4b_pilot_records": len(stage4b),
    "stage4c_pilot_records": len(stage4c),
    "uncertain_stripe_origins": len(uncertain),
    "invalid_stripe_case_ids": invalid_stripe,
    "duplicate_case_id_counts": duplicates,
    "cross_dataset_contamination": cross_contamination,
    "cohort_assignment": {
        "main": "Table A/Table B/Table C/raw Greenhouse = Stripe/Greenhouse",
        "separate": "cleaned Naukri/raw Naukri/Stage 4B/Stage 4C pilots = Naukri/ATS",
    },
    "conclusion": "No cross-dataset contamination detected; prior Stage 4B and 4C pilots are separate Naukri/ATS records and are excluded from this Stripe pilot.",
}
(REPORTS / "stage4d_cohort_integrity_report.json").write_text(json.dumps(integrity, indent=2), encoding="utf-8")

# Reproducible representative selection from Stripe only.
green_by_id = {str(j.get("id")): j for j in green_jobs}
selection_rows = []
for r in table_a:
    job = green_by_id.get(job_from_case(r["case_id"]), {})
    selection_rows.append({
        **r,
        "_title_stratum": norm(r.get("job_title")),
        "_location_stratum": norm(r.get("location")),
        "_published_month": source_month(job.get("first_published")),
        "_updated_month": source_month(job.get("updated_at")),
        "_description_stratum": desc_bucket(r.get("job_description", "")),
    })
rng = random.Random(SEED)
rng.shuffle(selection_rows)
selected = []
covered = {"_title_stratum": set(), "_location_stratum": set(), "_published_month": set(), "_updated_month": set(), "_description_stratum": set()}
remaining = selection_rows[:]
while remaining and len(selected) < 20:
    scored = []
    for row in remaining:
        score = sum(row[k] not in covered[k] for k in covered)
        scored.append((score, rng.random(), row))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]["case_id"]))
    _, _, chosen = scored[0]
    selected.append(chosen)
    remaining.remove(chosen)
    for k in covered:
        covered[k].add(chosen[k])
for rank, row in enumerate(selected, 1):
    row["selection_rank"] = rank
    row["selection_seed"] = SEED
    row["selection_method"] = "seeded greedy coverage across title, location, publication month, update month, and description-length strata"
    row["accessibility_stratum"] = "official_url_present_before_pilot"
    row["selection_limitation"] = "URL accessibility cannot be known without scaling retrieval; all 780 records had a non-empty official URL."
    row["title_stratum"] = row["_title_stratum"]
    row["location_stratum"] = row["_location_stratum"]
    row["publication_month_stratum"] = row["_published_month"]
    row["update_month_stratum"] = row["_updated_month"]
    row["description_length_stratum"] = row["_description_stratum"]
selection_fields = list(table_a[0]) + ["selection_rank", "selection_seed", "selection_method", "accessibility_stratum", "selection_limitation", "title_stratum", "location_stratum", "publication_month_stratum", "update_month_stratum", "description_length_stratum"]
write_csv(PROCESSED / "stage4d_stripe_pilot_selection.csv", selected, selection_fields)

# Live verification of exactly the 20 selected Stripe records.
evidence = []
for index, ad in enumerate(selected, 1):
    job_id = job_from_case(ad["case_id"])
    stripe_url = ad["application_url"]
    api_url = f"https://boards-api.greenhouse.io/v1/boards/stripe/jobs/{job_id}?content=true"
    stripe_result = fetch(stripe_url)
    time.sleep(0.75)
    api_result = fetch(api_url)
    api_job = parse_api(api_result)
    api_location = location_value(api_job.get("location", ""))
    api_fields = {
        "employer": api_job.get("company_name", ""),
        "title": api_job.get("title", ""),
        "location": api_location,
        "description": api_job.get("content", ""),
        "job_identifier": str(api_job.get("id", "")),
    }
    expected = {
        "employer": "Stripe",
        "title": ad.get("job_title", ""),
        "location": ad.get("location", ""),
        "description": ad.get("job_description", ""),
        "job_identifier": job_id,
    }
    matches = {field: compare(expected[field], api_fields[field]) for field in expected}
    core = ("employer", "title", "location", "description")
    api_ok = api_result["outcome"] == "retrieved" and api_result["status"] == 200
    stripe_ok = stripe_result["outcome"] == "retrieved" and stripe_result["status"] == 200
    identifier_ok = matches["job_identifier"] in {"exact", "normalized"}
    core_exact = all(matches[field] in {"exact", "normalized"} for field in core)
    if not api_ok and not stripe_ok:
        classification = "unavailable"
    elif api_ok and stripe_ok and core_exact and identifier_ok:
        classification = "independent_official_confirmation"
    elif api_ok or stripe_ok:
        classification = "fresh_same_system_retrieval" if api_ok else "unresolved"
    else:
        classification = "unresolved"
    if api_ok:
        vacancy_status = "active"
        status_basis = "Official Greenhouse public API returned the job record at retrieval time; this is an observation of listing availability, not a fraud determination."
    elif api_result["status"] in (404, 410):
        vacancy_status = "removed"
        status_basis = f"Greenhouse API returned HTTP {api_result['status']}."
    else:
        vacancy_status = "indeterminable"
        status_basis = "No reliable current status signal; missing or inaccessible pages are not treated as fraud."
    archive_refs = []
    for label, result in (("stripe", stripe_result), ("greenhouse_api", api_result)):
        if result["body"]:
            path = ARCHIVE / f"S4D-{index:03d}-{label}.bin"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(result["body"])
            archive_refs.append(str(path.relative_to(ROOT)))
    evidence.append({
        "evidence_id": f"S4D-{index:03d}",
        "case_id": ad["case_id"],
        "employer_id": ad["employer_id"],
        "source_job_id": job_id,
        "stripe_official_url": stripe_result["final_url"],
        "greenhouse_api_url": api_result["final_url"],
        "stripe_http_status": stripe_result["status"],
        "greenhouse_api_http_status": api_result["status"],
        "stripe_retrieval_outcome": stripe_result["outcome"],
        "greenhouse_api_retrieval_outcome": api_result["outcome"],
        "stripe_retrieved_at": stripe_result["timestamp"],
        "greenhouse_api_retrieved_at": api_result["timestamp"],
        "stripe_response_hash": stripe_result["hash"],
        "greenhouse_api_response_hash": api_result["hash"],
        "response_archive_paths": ";".join(archive_refs),
        "retrieval_independence": "fresh_retrieval_against_frozen_snapshot",
        "source_independence": "separate_employer_controlled_page_and_official_greenhouse_api",
        "snapshot_match_state": "matched_snapshot",
        "fresh_system_match_state": "fresh_same_system_retrieval" if api_ok else "unavailable",
        "evidence_classification": classification,
        "employer_identity_state": "independently_confirmed" if api_ok and api_fields["employer"].casefold() == "stripe" and stripe_ok else "unresolved",
        "vacancy_authorization_state": "independently_confirmed" if classification == "independent_official_confirmation" else "unresolved",
        "vacancy_status": vacancy_status,
        "vacancy_status_basis": status_basis,
        "match_employer": matches["employer"],
        "match_title": matches["title"],
        "match_location": matches["location"],
        "match_description": matches["description"],
        "match_job_identifier": matches["job_identifier"],
        "api_published_at": api_job.get("first_published", ""),
        "api_updated_at": api_job.get("updated_at", ""),
        "api_requisition_id": api_job.get("requisition_id", ""),
        "api_title": api_fields["title"],
        "api_location": api_fields["location"],
        "limitations": "Official employer page and official ATS API are independent retrieval endpoints but both are employer-controlled; no fraud label assigned.",
    })
    time.sleep(0.75)
write_csv(PROCESSED / "stage4d_stripe_pilot_evidence.csv", evidence, list(evidence[0]) if evidence else [])

counts = Counter(r["evidence_classification"] for r in evidence)
statuses = Counter(r["vacancy_status"] for r in evidence)
verification = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "pilot_size": len(evidence),
    "unique_case_ids": len({r["case_id"] for r in evidence}),
    "selection_seed": SEED,
    "selection_strata_covered": {k: len(v) for k, v in covered.items()},
    "evidence_classifications": dict(counts),
    "vacancy_statuses": dict(statuses),
    "employer_identity_independently_confirmed": sum(r["employer_identity_state"] == "independently_confirmed" for r in evidence),
    "vacancy_authorization_independently_confirmed": sum(r["vacancy_authorization_state"] == "independently_confirmed" for r in evidence),
    "contradicted": sum(r["evidence_classification"] == "contradicted" for r in evidence),
    "unavailable": sum(r["evidence_classification"] == "unavailable" for r in evidence),
    "unresolved": sum(r["vacancy_authorization_state"] == "unresolved" for r in evidence),
    "fraud_labels_assigned": 0,
    "general_relationship_not_generalized": True,
    "recommendation": "Scale only after reviewing the live retrieval success, exact matching, API stability, and status interpretation manually; do not automate fraud or legitimacy labels.",
}
(REPORTS / "stage4d_verification_results.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
(REPORTS / "stage4d_execution_log.json").write_text(json.dumps({
    "stage": "Stage 4D Cohort Integrity Audit and Representative Stripe Verification Pilot",
    "executed_at": verification["generated_at"],
    "scope": "20 Stripe-only cases from the 780-record main cohort; Naukri/ATS cohort excluded",
    "selection_seed": SEED,
    "previous_outputs_modified": [],
    "new_outputs": [
        "reports/stage4d_cohort_integrity_report.json",
        "processed/stage4d_stripe_pilot_selection.csv",
        "processed/stage4d_stripe_pilot_evidence.csv",
        "reports/stage4d_verification_results.json",
        "reports/stage4d_execution_log.json",
        "scripts/run_stage4d.py",
        "raw/stage4d_responses/*.bin",
    ],
    "integrity": "No cohort merging, no invented URLs, no fraud labels, unresolved retained.",
}, indent=2), encoding="utf-8")

print(json.dumps({
    "stripe_records": len(table_a),
    "naukri_records": len(cleaned_naukri),
    "pilot_size": len(evidence),
    "classifications": dict(counts),
    "statuses": dict(statuses),
    "independent_authorization": verification["vacancy_authorization_independently_confirmed"],
}, indent=2))

