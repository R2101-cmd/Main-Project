"""Run TrustHire Stage 4A reclassification and a 20-record public-source pilot.

The script preserves all existing files and writes only new Stage 4A outputs.
It intentionally does not assign fraud labels or scale retrieval to 780 records.
"""
import csv
import hashlib
import html
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "processed"
REPORTS = ROOT / "reports"

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def norm(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip().casefold()

def match_text(expected, actual):
    e, a = norm(expected), norm(actual)
    if not e or not a:
        return "not_available"
    if e == a or e in a or a in e:
        return "match"
    return "mismatch"

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.title = []
        self.in_title = False
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True
    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False
    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())
            if self.in_title:
                self.title.append(data.strip())

def fetch(url):
    started = datetime.now(timezone.utc).isoformat()
    request = Request(url, headers={"User-Agent": "TrustHire-research-audit/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read()
            return {
                "requested_url": url,
                "actual_source_url": response.geturl(),
                "retrieved_at": started,
                "http_status": getattr(response, "status", 200),
                "retrieval_outcome": "retrieved",
                "response_hash": hashlib.sha256(body).hexdigest(),
                "content_type": response.headers.get("Content-Type", ""),
                "body": body,
            }
    except HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        return {
            "requested_url": url, "actual_source_url": getattr(exc, "url", url),
            "retrieved_at": started, "http_status": exc.code,
            "retrieval_outcome": "http_error", "response_hash": hashlib.sha256(body).hexdigest(),
            "content_type": "", "body": body,
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "requested_url": url, "actual_source_url": url, "retrieved_at": started,
            "http_status": "", "retrieval_outcome": f"unavailable: {type(exc).__name__}",
            "response_hash": "", "content_type": "", "body": b"",
        }

def source_relation(url):
    host = (urlparse(url).hostname or "").casefold()
    if "greenhouse" in host:
        return "fresh_retrieval_same_official_ats"
    if host:
        return "fresh_retrieval_official_or_ats_url"
    return "unknown_source"

def parse_body(result):
    body = result.get("body", b"")
    text = body.decode("utf-8", errors="replace")
    parser = TextParser()
    try:
        parser.feed(text)
    except Exception:
        pass
    return " ".join(parser.parts), " ".join(parser.title)

def source_kind(url):
    host = (urlparse(url).hostname or "").casefold()
    if "greenhouse" in host:
        return "official_greenhouse_or_ats"
    if any(x in host for x in ("workday", "lever", "oraclecloud", "smartrecruiters", "successfactors")):
        return "official_ats"
    return "official_or_ats_destination"

# Objective 1: reclassify, without modifying existing Table C.
old_c = read_csv(PROCESSED / "table_C_evidence_records.csv")
reclassified = []
for row in old_c:
    item = dict(row)
    item.update({
        "source_record_match_state": "matched_snapshot",
        "employer_identity_state": "snapshot_consistent",
        "vacancy_authorization_state": "snapshot_consistent_only",
        "independence_status": "same_source_derivation",
        "source_relation": "same_source_historical_snapshot",
        "evidence_rationale": "Table A and the Greenhouse snapshot match, but Table A was derived from this same snapshot. This establishes snapshot consistency only; it is not independent employer or authorization verification.",
    })
    reclassified.append(item)
reclass_fields = list(reclassified[0]) if reclassified else []
for field in [
    "source_record_match_state", "employer_identity_state",
    "vacancy_authorization_state", "independence_status", "source_relation",
]:
    if field not in reclass_fields:
        reclass_fields.append(field)
write_csv(PROCESSED / "table_C_stage4_reclassified.csv", reclassified, reclass_fields)

# Objective 2: schema validation.
schema = [
    "evidence_id", "case_id", "source_id", "source_type", "source_url",
    "source_relation", "retrieval_timestamp", "request_url", "http_status",
    "retrieval_outcome", "response_hash", "snapshot_id", "source_record_id",
    "source_published_at", "source_updated_at", "claim_type",
    "source_record_match_state", "employer_identity_state",
    "vacancy_authorization_state", "independence_status", "matched_fields",
    "field_match_method", "authorization_signal", "contradiction_details",
    "evidence_limitations", "evidence_rationale",
]
(REPORTS / "stage4a_schema_validation.json").write_text(json.dumps({
    "required_fields": schema,
    "reclassified_records": len(reclassified),
    "reclassified_ids_unique": len({r.get("evidence_id") for r in reclassified}) == len(reclassified),
    "reclassified_case_ids_unique": len({r.get("case_id") for r in reclassified}) == len(reclassified),
    "schema_note": "The new schema separates snapshot matching, employer identity, authorization, retrieval independence, and source relation.",
}, indent=2), encoding="utf-8")

# Objective 3: inspect employer cohort and select 10 lineage + 10 ordinary records.
greenhouse = json.loads((ROOT / "raw/greenhouse/greenhouse_raw.json").read_text(encoding="utf-8"))
greenhouse_employers = sorted({str(j.get("company_name", "")).strip() for j in greenhouse.get("jobs", []) if j.get("company_name")})
cleaned = read_csv(PROCESSED / "vacancyguard_table_a_cleaned.csv")
lineage = read_csv(PROCESSED / "vacancyguard_table_d_lineage_candidates.csv")
lineage_ids = set()
for row in lineage:
    lineage_ids.update(filter(None, row.get("related_case_ids", "").split(";")))
lineage_records = [r for r in cleaned if r.get("case_id") in lineage_ids]
ordinary_records = [r for r in cleaned if r.get("case_id") not in lineage_ids]
lineage_records = sorted(lineage_records, key=lambda r: (r.get("source_employer_name", "").casefold(), r.get("case_id", "")))[:10]
ordinary_records = sorted(ordinary_records, key=lambda r: (r.get("source_employer_name", "").casefold(), r.get("case_id", "")))[:10]
pilot_records = lineage_records + ordinary_records

pilot = []
for i, ad in enumerate(pilot_records, 1):
    url = ad.get("application_url", "")
    result = fetch(url) if url else {
        "requested_url": "", "actual_source_url": "", "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "http_status": "", "retrieval_outcome": "unavailable: missing_url", "response_hash": "",
        "content_type": "", "body": b"",
    }
    text, page_title = parse_body(result)
    title_match = match_text(ad.get("job_title"), page_title + " " + text)
    employer_match = match_text(ad.get("source_employer_name"), page_title + " " + text)
    location_match = match_text(ad.get("location"), text)
    description_match = match_text(ad.get("job_description"), text)
    if result["retrieval_outcome"] == "retrieved":
        if all(x == "match" for x in (title_match, employer_match, location_match)):
            match_state = "exact_or_strong_page_match"
        elif any(x == "match" for x in (title_match, employer_match, location_match, description_match)):
            match_state = "partial_match"
        else:
            match_state = "retrieved_unverified"
    else:
        match_state = "unavailable"
    is_greenhouse = "greenhouse" in (urlparse(url).hostname or "").casefold()
    pilot.append({
        "evidence_id": f"S4A-{i:03d}", "case_id": ad.get("case_id", ""),
        "source_id": f"pilot-source-{i:03d}", "source_type": source_kind(url),
        "source_url": result["actual_source_url"], "source_relation": source_relation(url),
        "retrieval_timestamp": result["retrieved_at"], "request_url": result["requested_url"],
        "http_status": result["http_status"], "retrieval_outcome": result["retrieval_outcome"],
        "response_hash": result["response_hash"], "snapshot_id": "",
        "source_record_id": ad.get("source_job_id", ""),
        "source_published_at": ad.get("source_created_date", ""),
        "source_updated_at": "",
        "claim_type": "source record match, employer identity, and vacancy authorization",
        "source_record_match_state": match_state,
        "employer_identity_state": "unresolved",
        "vacancy_authorization_state": "unresolved",
        "independence_status": "fresh_retrieval_same_official_ats" if is_greenhouse else "fresh_retrieval_official_or_ats_url",
        "matched_fields": f"title={title_match}; employer={employer_match}; location={location_match}; description={description_match}",
        "field_match_method": "normalized text comparison against retrieved page text; not a final adjudication",
        "authorization_signal": "official source retrieved; authorization not inferred from retrieval alone",
        "contradiction_details": "",
        "evidence_limitations": "Page parsing is heuristic; requisition ID and active status require structured page/API evidence.",
        "evidence_rationale": "Pilot observation only. Missing or inaccessible pages are not treated as fraudulent.",
        "pilot_group": "lineage_candidate" if ad.get("case_id") in lineage_ids else "ordinary",
        "source_employer_name": ad.get("source_employer_name", ""),
        "job_title": ad.get("job_title", ""),
        "location": ad.get("location", ""),
        "lineage_case": "yes" if ad.get("case_id") in lineage_ids else "no",
    })
    time.sleep(1)

pilot_fields = list(pilot[0]) if pilot else schema + ["pilot_group", "source_employer_name", "job_title", "location", "lineage_case"]
write_csv(PROCESSED / "table_C_stage4_pilot.csv", pilot, pilot_fields)

# Objective 5: lineage analysis remains conservative.
lineage_analysis = []
pilot_case_ids = {r["case_id"] for r in pilot}
for row in lineage:
    related = [x for x in row.get("related_case_ids", "").split(";") if x]
    observed = [r for r in cleaned if r.get("case_id") in related]
    lineage_analysis.append({
        "lineage_group_id": row.get("lineage_group_id", ""),
        "related_case_ids": row.get("related_case_ids", ""),
        "related_record_count": len(observed),
        "source_job_ids": ";".join(r.get("source_job_id", "") for r in observed),
        "employers": ";".join(sorted({r.get("source_employer_name", "") for r in observed})),
        "source_files": ";".join(sorted({r.get("source_file", "") for r in observed})),
        "similarity_score": row.get("similarity_score", ""),
        "likely_copy_or_repost": "candidate_only",
        "shared_underlying_source": "not established",
        "independent_official_publication_evidence": "not established by lineage similarity",
        "pilot_included_case_ids": ";".join(x for x in related if x in pilot_case_ids),
        "analysis_note": "Identical or highly similar text is not proof of copying order, common authorization, or legitimacy.",
    })
write_csv(REPORTS / "stage4a_lineage_analysis.csv", lineage_analysis, list(lineage_analysis[0]) if lineage_analysis else [])

counts = Counter(r["retrieval_outcome"] for r in pilot)
match_counts = Counter(r["source_record_match_state"] for r in pilot)
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "pilot_size": len(pilot),
    "lineage_cases_selected": len(lineage_records),
    "ordinary_cases_selected": len(ordinary_records),
    "duplicate_case_ids": len(pilot_case_ids) != len(pilot),
    "greenhouse_snapshot_employer_count": len(greenhouse_employers),
    "greenhouse_snapshot_employers": greenhouse_employers,
    "greenhouse_cohort_note": "The 780-record Table A cohort is Stripe/Greenhouse; the 21 lineage candidates are from the separate 198-record cleaned Naukri/ATS cohort.",
    "retrieval_outcomes": dict(counts),
    "match_states": dict(match_counts),
    "successful_live_retrievals": counts.get("retrieved", 0),
    "failed_or_unavailable_retrievals": len(pilot) - counts.get("retrieved", 0),
    "exact_or_strong_matches": match_counts.get("exact_or_strong_page_match", 0),
    "partial_matches": match_counts.get("partial_match", 0),
    "employer_identity_verification": "none assigned automatically; pilot records remain unresolved",
    "independent_authorization_evidence": 0,
    "contradictory_evidence": sum(1 for r in pilot if r["source_record_match_state"] == "mismatch"),
    "unavailable_evidence": match_counts.get("unavailable", 0),
    "unresolved_cases": len(pilot),
    "scale_recommendation": "Do not scale yet; first validate structured extraction and independent-source criteria on the pilot.",
}
(REPORTS / "stage4a_pilot_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
(REPORTS / "stage4a_execution_log.json").write_text(json.dumps({
    "stage": "Stage 4A evidence reclassification and independent verification pilot",
    "executed_at": report["generated_at"],
    "files_modified": [],
    "new_files": [
        "processed/table_C_stage4_reclassified.csv",
        "processed/table_C_stage4_pilot.csv",
        "reports/stage4a_schema_validation.json",
        "reports/stage4a_pilot_results.json",
        "reports/stage4a_lineage_analysis.csv",
        "reports/stage4a_execution_log.json",
        "scripts/run_stage4a.py",
    ],
    "records_reclassified": len(reclassified),
    "pilot_requests": len(pilot),
    "scope_limit": "20-record pilot only; no 780-record live scrape",
    "integrity_policy": "No fraud labels assigned; unavailable pages retained as unresolved; no CAPTCHA or authentication bypass.",
}, indent=2), encoding="utf-8")

print(json.dumps(report, indent=2))

