"""TrustHire Stage 4B: retrieval and evidence quality improvement.

Runs exactly the Stage 4A 20-record pilot, writes only new Stage 4B outputs,
and never assigns fraud or legitimacy labels.
"""
import csv
import hashlib
import html
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "processed"
REPORTS = ROOT / "reports"
ARCHIVE = ROOT / "raw" / "stage4b_responses"
AS_OF_DATE = "2026-11-12"

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

def tokens(value):
    return set(re.findall(r"[a-z0-9]+", norm(value)))

def compare(expected, observed):
    e, o = norm(expected), norm(observed)
    if not e or not o:
        return "not_comparable"
    if e == o:
        return "exact"
    if e.replace(" ", "") == o.replace(" ", ""):
        return "normalized"
    et, ot = tokens(e), tokens(o)
    if et and ot:
        overlap = len(et & ot) / max(1, len(et))
        if overlap >= 0.65 or e in o or o in e:
            return "partial"
    return "mismatch"

class StructuredParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.title_parts = []
        self.meta = {}
        self.links = []
        self.jsonld = []
        self._title = False
        self._script_type = ""
        self._script_parts = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag = tag.lower()
        if tag == "title":
            self._title = True
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name") or attrs.get("itemprop")
            value = attrs.get("content")
            if key and value:
                self.meta[key.casefold()] = value
        if tag == "link" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "script":
            self._script_type = attrs.get("type", "").casefold()
            self._script_parts = []
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._title = False
        if tag == "script":
            if "ld+json" in self._script_type:
                raw = "".join(self._script_parts).strip()
                if raw:
                    try:
                        self.jsonld.append(json.loads(raw))
                    except json.JSONDecodeError:
                        pass
            self._script_type = ""
            self._script_parts = []
    def handle_data(self, data):
        if self._script_type:
            self._script_parts.append(data)
        elif data.strip():
            self.text_parts.append(data.strip())
            if self._title:
                self.title_parts.append(data.strip())

def flatten_jsonld(value):
    if isinstance(value, list):
        for item in value:
            yield from flatten_jsonld(item)
    elif isinstance(value, dict):
        if "@graph" in value:
            yield from flatten_jsonld(value["@graph"])
        else:
            yield value

def first_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value)
    return ""

def location_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = [value.get(k, "") for k in ("addressLocality", "addressRegion", "addressCountry", "name")]
        return ", ".join(str(x) for x in parts if x)
    if isinstance(value, list):
        return "; ".join(location_value(x) for x in value)
    return ""

def extract_structured(body):
    parser = StructuredParser()
    text = body.decode("utf-8", errors="replace")
    try:
        parser.feed(text)
    except Exception:
        pass
    jobs = []
    for item in parser.jsonld:
        for obj in flatten_jsonld(item):
            typ = obj.get("@type", "")
            types = typ if isinstance(typ, list) else [typ]
            if any(str(x).casefold() == "jobposting" for x in types):
                jobs.append(obj)
    job = jobs[0] if jobs else {}
    observed = {
        "employer_name": first_value(job.get("hiringOrganization", {}) if isinstance(job.get("hiringOrganization"), dict) else {}, "name"),
        "job_title": first_value(job, "title", "name"),
        "job_location": location_value(job.get("jobLocation", "")),
        "job_description": first_value(job, "description"),
        "requisition_id": first_value(job, "identifier") if isinstance(job.get("identifier"), (str, int, float)) else first_value(job.get("identifier", {}) if isinstance(job.get("identifier"), dict) else {}, "value", "name"),
        "published_date": first_value(job, "datePosted"),
        "updated_date": first_value(job, "dateModified", "lastModified"),
        "employment_type": first_value(job, "employmentType"),
        "vacancy_status": first_value(job, "jobLocationType", "validThrough"),
    }
    # OpenGraph/meta fallbacks are recorded separately and never overwrite JSON-LD values.
    meta_map = {
        "employer_name": ("og:site_name", "application-name", "author"),
        "job_title": ("og:title", "twitter:title"),
        "job_description": ("og:description", "description"),
    }
    for field, keys in meta_map.items():
        if not observed[field]:
            for key in keys:
                if parser.meta.get(key):
                    observed[field] = parser.meta[key]
                    break
    return observed, {
        "parser": "HTMLParser",
        "jsonld_jobposting_found": bool(job),
        "jsonld_fields": sorted(job.keys()),
        "meta_keys_used": sorted(k for keys in meta_map.values() for k in keys if k in parser.meta),
        "title": " ".join(parser.title_parts),
        "visible_text": " ".join(parser.text_parts),
        "links": parser.links,
    }

def fetch(url):
    timestamp = datetime.now(timezone.utc).isoformat()
    req = Request(url, headers={"User-Agent": "TrustHire-research-audit/1.0"})
    try:
        with urlopen(req, timeout=20) as response:
            body = response.read()
            final_url = response.geturl()
            result = {
                "requested_url": url, "actual_source_url": final_url,
                "retrieval_timestamp": timestamp, "http_status": getattr(response, "status", 200),
                "retrieval_outcome": "retrieved", "response_hash": hashlib.sha256(body).hexdigest(),
                "content_type": response.headers.get("Content-Type", ""), "body": body,
            }
    except HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        result = {
            "requested_url": url, "actual_source_url": getattr(exc, "url", url),
            "retrieval_timestamp": timestamp, "http_status": exc.code,
            "retrieval_outcome": "http_error", "response_hash": hashlib.sha256(body).hexdigest(),
            "content_type": "", "body": body,
        }
    except (URLError, TimeoutError, OSError) as exc:
        result = {
            "requested_url": url, "actual_source_url": url,
            "retrieval_timestamp": timestamp, "http_status": "",
            "retrieval_outcome": f"unavailable: {type(exc).__name__}",
            "response_hash": "", "content_type": "", "body": b"",
        }
    return result

def status_from_evidence(result, observed, visible_text):
    status_text = norm(visible_text)
    valid_through = observed.get("vacancy_status", "")
    if result["http_status"] in (404, 410):
        return "removed", "HTTP status indicates the resource is unavailable."
    if valid_through:
        try:
            date = valid_through[:10]
            if date < AS_OF_DATE:
                return "expired", f"Structured validThrough={valid_through} is before {AS_OF_DATE}."
            return "active", f"Structured validThrough={valid_through} is on/after {AS_OF_DATE}."
        except Exception:
            pass
    if any(x in status_text for x in ("job is no longer available", "position has been filled", "job has expired")):
        return "expired", "Page text indicates the vacancy is no longer available."
    if result["retrieval_outcome"] == "retrieved":
        return "indeterminable", "Page retrieved, but no reliable active/expired status signal was extracted."
    return "indeterminable", "No reliable vacancy-status signal; missing or inaccessible pages are not treated as fraud."

def source_relation(url):
    host = (urlparse(url).hostname or "").casefold()
    if "greenhouse" in host:
        return "fresh_retrieval_same_official_ats"
    if host:
        return "fresh_retrieval_official_or_ats_url"
    return "unknown_source"

def source_type(url):
    host = (urlparse(url).hostname or "").casefold()
    if "greenhouse" in host:
        return "official_greenhouse_or_ats"
    if any(x in host for x in ("workday", "lever", "oraclecloud", "smartrecruiters", "successfactors", "zohorecruit")):
        return "official_ats"
    return "employer_or_ats_destination"

def select_same_pilot():
    cleaned = read_csv(PROCESSED / "vacancyguard_table_a_cleaned.csv")
    lineage = read_csv(PROCESSED / "vacancyguard_table_d_lineage_candidates.csv")
    lineage_ids = set()
    for row in lineage:
        lineage_ids.update(x for x in row.get("related_case_ids", "").split(";") if x)
    lineage_records = sorted(
        [r for r in cleaned if r.get("case_id") in lineage_ids],
        key=lambda r: (r.get("source_employer_name", "").casefold(), r.get("case_id", ""),
    ))[:10]
    ordinary_records = sorted(
        [r for r in cleaned if r.get("case_id") not in lineage_ids],
        key=lambda r: (r.get("source_employer_name", "").casefold(), r.get("case_id", ""),
    ))[:10]
    return lineage_records + ordinary_records, lineage_ids, lineage

pilot_records, lineage_ids, lineage_rows = select_same_pilot()
field_rows = []
evidence_rows = []
for i, ad in enumerate(pilot_records, 1):
    official_url = ad.get("application_url", "").strip()
    fallback_url = ad.get("advertisement_url", "").strip()
    request_url = official_url
    recovery = "not_needed" if official_url else ("third_party_advertisement_url_available" if fallback_url else "no_recovery_candidate")
    result = fetch(request_url) if request_url else {
        "requested_url": "", "actual_source_url": "", "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        "http_status": "", "retrieval_outcome": "unavailable: missing_official_url", "response_hash": "",
        "content_type": "", "body": b"",
    }
    observed, provenance = extract_structured(result["body"])
    visible = provenance["visible_text"]
    fields = {
        "employer_name": ad.get("source_employer_name", ""),
        "job_title": ad.get("job_title", ""),
        "job_location": ad.get("location", ""),
        "job_description": ad.get("job_description", ""),
        "requisition_id": ad.get("source_job_id", ""),
    }
    observed_fields = {
        "employer_name": observed.get("employer_name", ""),
        "job_title": observed.get("job_title", ""),
        "job_location": observed.get("job_location", ""),
        "job_description": observed.get("job_description", ""),
        "requisition_id": observed.get("requisition_id", ""),
    }
    comparisons = {key: compare(fields[key], observed_fields[key]) for key in fields}
    # Generic values are not informative identifiers.
    if norm(observed_fields["requisition_id"]) in {"see opening id", "opening id", "job id", "n/a", "na"}:
        comparisons["requisition_id"] = "not_comparable"
        observed_fields["requisition_id"] = ""
    status, status_basis = status_from_evidence(result, observed, visible)
    page_host = (urlparse(result["actual_source_url"] or request_url).hostname or "").casefold()
    employer_host_token = re.sub(r"[^a-z0-9]", "", norm(ad.get("source_employer_name", "")))
    official_domain_signal = "not_observed"
    ats_relationship = "not_observed"
    if result["retrieval_outcome"] == "retrieved":
        if employer_host_token and employer_host_token in re.sub(r"[^a-z0-9]", "", page_host):
            official_domain_signal = "retrieved_host_contains_employer_token"
        if "greenhouse" in page_host or any(x in page_host for x in ("workday", "lever", "oraclecloud", "zohorecruit")):
            ats_relationship = "ats_host_observed; employer relationship not independently confirmed"
    if result["body"]:
        archive_path = ARCHIVE / f"S4B-{i:03d}.bin"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(result["body"])
        archive_ref = str(archive_path.relative_to(ROOT))
    else:
        archive_ref = ""
    retrieval_independence = "fresh_retrieval" if result["retrieval_outcome"] == "retrieved" else "not_retrieved"
    source_independence = "not_established"
    if result["retrieval_outcome"] == "retrieved" and official_url:
        if "greenhouse" in page_host or any(x in page_host for x in ("workday", "lever", "oraclecloud", "zohorecruit")):
            source_independence = "same_or_ats_system_not_independent_employer_confirmation"
        elif official_domain_signal == "retrieved_host_contains_employer_token":
            source_independence = "employer_domain_candidate_not_independently_confirmed"
    match_values = set(comparisons.values())
    if result["retrieval_outcome"] != "retrieved":
        overall = "unavailable"
    elif all(comparisons[k] in {"exact", "normalized"} for k in ("employer_name", "job_title", "job_location", "job_description")):
        overall = "exact_or_normalized_all_core_fields"
    elif any(comparisons[k] in {"partial", "exact", "normalized"} for k in ("employer_name", "job_title", "job_location", "job_description")):
        overall = "partial_or_mixed"
    else:
        overall = "retrieved_unverified"
    evidence_rows.append({
        "evidence_id": f"S4B-{i:03d}", "case_id": ad.get("case_id", ""),
        "source_id": f"stage4b-source-{i:03d}", "source_type": source_type(request_url),
        "source_url": result["actual_source_url"], "source_relation": source_relation(request_url),
        "retrieval_independence": retrieval_independence, "source_independence": source_independence,
        "retrieval_timestamp": result["retrieval_timestamp"], "request_url": result["requested_url"],
        "http_status": result["http_status"], "retrieval_outcome": result["retrieval_outcome"],
        "response_hash": result["response_hash"], "response_archive_path": archive_ref,
        "content_type": result["content_type"], "source_record_id": ad.get("source_job_id", ""),
        "extraction_method": "JSON-LD JobPosting; OpenGraph/meta fallback; visible HTML text",
        "extraction_provenance": json.dumps(provenance, ensure_ascii=False),
        "employer_name_observed": observed_fields["employer_name"],
        "job_title_observed": observed_fields["job_title"],
        "job_location_observed": observed_fields["job_location"],
        "job_description_observed": observed_fields["job_description"],
        "requisition_id_observed": observed_fields["requisition_id"],
        "published_date_observed": observed.get("published_date", ""),
        "updated_date_observed": observed.get("updated_date", ""),
        "employment_type_observed": observed.get("employment_type", ""),
        "vacancy_status": status, "vacancy_status_basis": status_basis,
        "overall_match_state": overall,
        "employer_identity_state": "unresolved",
        "vacancy_authorization_state": "unresolved",
        "authorization_signal_official_domain": official_domain_signal,
        "authorization_signal_ats_relationship": ats_relationship,
        "authorization_signal_identifier_agreement": "not_established",
        "recovery_assessment": recovery,
        "evidence_limitations": "Fresh same-ATS retrieval is not an independent source; extraction does not itself prove authorization; unresolved retained.",
        "evidence_rationale": "Stage 4B pilot observation only. No fraud or legitimacy label assigned.",
        "pilot_group": "lineage_candidate" if ad.get("case_id") in lineage_ids else "ordinary",
    })
    for field in ("employer_name", "job_title", "job_location", "job_description", "requisition_id"):
        field_rows.append({
            "evidence_id": f"S4B-{i:03d}", "case_id": ad.get("case_id", ""),
            "field_name": field, "expected_value": fields[field],
            "observed_value": observed_fields[field], "match_class": comparisons[field],
            "source": "jsonld" if provenance["jsonld_jobposting_found"] and observed_fields[field] else ("meta_or_visible_html" if observed_fields[field] else "not_extracted"),
            "comparison_method": "exact, normalized, token-overlap partial, mismatch, or not_comparable",
        })
    time.sleep(1)

pilot_fields = list(evidence_rows[0]) if evidence_rows else []
write_csv(PROCESSED / "table_C_stage4b_pilot.csv", evidence_rows, pilot_fields)
write_csv(REPORTS / "stage4b_field_matching_report.csv", field_rows, list(field_rows[0]) if field_rows else [])

# Authorization audit and Stage 4A comparison.
auth = Counter()
for row in evidence_rows:
    auth[row["authorization_signal_official_domain"]] += 1
    auth[row["authorization_signal_ats_relationship"]] += 1
auth_report = {
    "pilot_size": len(evidence_rows),
    "official_domain_signals": dict(Counter(r["authorization_signal_official_domain"] for r in evidence_rows)),
    "ats_relationship_signals": dict(Counter(r["authorization_signal_ats_relationship"] for r in evidence_rows)),
    "identifier_agreement_signals": dict(Counter(r["authorization_signal_identifier_agreement"] for r in evidence_rows)),
    "independent_authorization_evidence": 0,
    "interpretation": "Fresh retrieval and ATS hosting are provenance signals, not independent employer authorization. No employer-domain confirmation or separate official confirmation was established automatically.",
}
(REPORTS / "stage4b_authorization_audit.json").write_text(json.dumps(auth_report, indent=2), encoding="utf-8")

old = json.loads((REPORTS / "stage4a_pilot_results.json").read_text(encoding="utf-8"))
new_counts = Counter(r["retrieval_outcome"] for r in evidence_rows)
new_matches = Counter(r["overall_match_state"] for r in evidence_rows)
comparison = {
    "stage4a": {
        "pilot_size": old.get("pilot_size"),
        "successful_live_retrievals": old.get("successful_live_retrievals"),
        "unavailable": old.get("unavailable_evidence"),
        "strong_matches": old.get("exact_or_strong_matches"),
        "partial_matches": old.get("partial_matches"),
        "independent_authorization_evidence": old.get("independent_authorization_evidence"),
        "unresolved_cases": old.get("unresolved_cases"),
    },
    "stage4b": {
        "pilot_size": len(evidence_rows),
        "successful_live_retrievals": new_counts.get("retrieved", 0),
        "extraction_successful_response_parses": sum(bool(r["extraction_provenance"]) and r["retrieval_outcome"] == "retrieved" for r in evidence_rows),
        "jsonld_jobposting_extractions": sum('"jsonld_jobposting_found": true' in r["extraction_provenance"] for r in evidence_rows),
        "retrieved_responses_with_any_extracted_field": sum(any(r[k] for k in ("employer_name_observed", "job_title_observed", "job_location_observed", "job_description_observed", "requisition_id_observed")) for r in evidence_rows),
        "exact_or_normalized_core_matches": new_matches.get("exact_or_normalized_all_core_fields", 0),
        "partial_or_mixed_matches": new_matches.get("partial_or_mixed", 0),
        "retrieved_unverified": new_matches.get("retrieved_unverified", 0),
        "unavailable": sum(r["overall_match_state"] == "unavailable" for r in evidence_rows),
        "vacancy_status_counts": dict(Counter(r["vacancy_status"] for r in evidence_rows)),
        "employer_identity_verification": 0,
        "independent_authorization_evidence": 0,
        "contradictory_evidence": 0,
        "unresolved_cases": len(evidence_rows),
    },
    "method_change": "Stage 4B uses structured extraction, response hashes, archived responses, field-level comparison, and explicit authorization signals.",
}
(REPORTS / "stage4b_comparison_with_stage4a.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

(REPORTS / "stage4b_retrieval_quality.json").write_text(json.dumps({
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "pilot_size": len(evidence_rows),
    "retrieval_outcomes": dict(new_counts),
    "overall_match_states": dict(new_matches),
    "field_match_counts": dict(Counter(r["match_class"] for r in field_rows)),
    "vacancy_status_counts": dict(Counter(r["vacancy_status"] for r in evidence_rows)),
    "missing_url_recovery": dict(Counter(r["recovery_assessment"] for r in evidence_rows)),
    "successful_retrievals": new_counts.get("retrieved", 0),
    "jsonld_jobposting_extractions": sum('"jsonld_jobposting_found": true' in r["extraction_provenance"] for r in evidence_rows),
    "retrieved_responses_with_any_extracted_field": sum(any(r[k] for k in ("employer_name_observed", "job_title_observed", "job_location_observed", "job_description_observed", "requisition_id_observed")) for r in evidence_rows),
    "failed_or_unavailable": sum(r["overall_match_state"] == "unavailable" for r in evidence_rows),
    "independent_employer_verifications": 0,
    "independent_authorization_evidence": 0,
    "fraud_labels_assigned": 0,
    "scale_recommendation": "Not yet suitable for full-scale verification; improve URL recovery, structured requisition/status extraction, and employer-domain confirmation first.",
}, indent=2), encoding="utf-8")

(REPORTS / "stage4b_execution_log.json").write_text(json.dumps({
    "stage": "Stage 4B Retrieval and Evidence Quality Improvement",
    "executed_at": datetime.now(timezone.utc).isoformat(),
    "pilot_cases": len(evidence_rows),
    "scope": "same 20 Stage 4A cases; no scale-up",
    "previous_outputs_modified": [],
    "new_outputs": [
        "processed/table_C_stage4b_pilot.csv",
        "reports/stage4b_retrieval_quality.json",
        "reports/stage4b_field_matching_report.csv",
        "reports/stage4b_authorization_audit.json",
        "reports/stage4b_comparison_with_stage4a.json",
        "reports/stage4b_execution_log.json",
        "scripts/run_stage4b.py",
        "raw/stage4b_responses/*.bin",
    ],
    "integrity": "No URLs invented; missing URLs retained as unavailable with recovery candidates; no fraud labels; same-ATS retrieval not called independent.",
}, indent=2), encoding="utf-8")

print(json.dumps({
    "pilot_size": len(evidence_rows),
    "retrieval_outcomes": dict(new_counts),
    "overall_match_states": dict(new_matches),
    "vacancy_status_counts": dict(Counter(r["vacancy_status"] for r in evidence_rows)),
    "field_match_counts": dict(Counter(r["match_class"] for r in field_rows)),
}, indent=2))

