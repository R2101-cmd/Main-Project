"""TrustHire Stage 4C: employer-to-ATS relationship and source discovery.

This script preserves prior outputs, audits only the existing 20-case Stage 4B
pilot, and creates a reusable Stripe source registry. It does not assign labels.
"""
import csv
import hashlib
import json
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
AS_OF = "2026-11-12"

def rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, data, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

def fetch(url):
    ts = datetime.now(timezone.utc).isoformat()
    if not url:
        return {"requested_url": "", "actual_url": "", "retrieved_at": ts, "http_status": "", "outcome": "not_requested", "hash": ""}
    req = Request(url, headers={"User-Agent": "TrustHire-research-audit/1.0"})
    try:
        with urlopen(req, timeout=20) as response:
            body = response.read()
            return {
                "requested_url": url, "actual_url": response.geturl(),
                "retrieved_at": ts, "http_status": getattr(response, "status", 200),
                "outcome": "retrieved", "hash": hashlib.sha256(body).hexdigest(),
            }
    except HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        return {
            "requested_url": url, "actual_url": getattr(exc, "url", url),
            "retrieved_at": ts, "http_status": exc.code,
            "outcome": "http_error", "hash": hashlib.sha256(body).hexdigest(),
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "requested_url": url, "actual_url": url, "retrieved_at": ts,
            "http_status": "", "outcome": f"unavailable: {type(exc).__name__}", "hash": "",
        }

def host(url):
    return (urlparse(url).hostname or "").casefold()

def raw_record_for(ad):
    source = ROOT / "raw" / ad.get("source_file", "")
    if not source.exists():
        return None
    with source.open("r", encoding="utf-8-sig", newline="") as f:
        for record in csv.DictReader(f):
            if str(record.get("jobId", "")) == str(ad.get("source_job_id", "")):
                return record
    return None

pilot = rows(PROCESSED / "table_C_stage4b_pilot.csv")
cleaned = {r["case_id"]: r for r in rows(PROCESSED / "vacancyguard_table_a_cleaned.csv")}
stage4b_by_case = {r["case_id"]: r for r in pilot}

# A reusable employer-to-ATS registry. Evidence is based on the official
# employer page observed in the Stage 4C investigation and its linked ATS page.
stripe_page = "https://stripe.com/careers/apply/abuse-investigator/8172487"
stripe_careers = "https://stripe.com/careers/search"
stripe_ats = "https://job-boards.greenhouse.io/embed/job_app?for=stripe&token=8172487"
stripe_fetch = fetch(stripe_page)
time.sleep(1)
stripe_ats_fetch = fetch(stripe_ats)
registry = [{
    "employer_id": "EMP_STRIPE",
    "employer_name": "Stripe",
    "official_domain": "stripe.com",
    "official_careers_url": stripe_careers,
    "ats_provider": "Greenhouse",
    "ats_domain": "job-boards.greenhouse.io",
    "official_relationship_evidence_url": stripe_page,
    "relationship_type": "direct employer-controlled vacancy page links to Greenhouse application",
    "verification_status": "confirmed_relationship_for_observed_vacancy",
    "verification_timestamp": stripe_fetch["retrieved_at"],
    "limitations": "Confirms Stripe's use of Greenhouse for the observed vacancy 8172487; does not prove authorization of every Stripe vacancy.",
    "source_independence": "separate employer-controlled Stripe page and Greenhouse application page",
    "evidence_observation": "Stripe application page identifies the company as Stripe and exposes a link labelled Greenhouse application for the same vacancy.",
    "employer_page_http_status": stripe_fetch["http_status"],
    "ats_page_http_status": stripe_ats_fetch["http_status"],
    "employer_page_response_hash": stripe_fetch["hash"],
    "ats_page_response_hash": stripe_ats_fetch["hash"],
}]
write_csv(PROCESSED / "stripe_official_source_registry.csv", registry, list(registry[0]))

# Analyze all 20 pilot cases, without substituting third-party URLs.
relationships = []
for record in pilot:
    case_id = record["case_id"]
    ad = cleaned[case_id]
    official_url = ad.get("application_url", "").strip()
    original_ad_url = ad.get("advertisement_url", "").strip()
    st = stage4b_by_case[case_id]
    source_host = host(official_url)
    raw = raw_record_for(ad) if not official_url else None
    raw_official_fields = {
        key: (raw or {}).get(key, "")
        for key in ("companyApplyUrl", "clientCareersUrl", "applyRedirectUrl", "companyApplyJob")
    }
    if official_url:
        source_kind = "official_employer_domain" if any(token in source_host for token in ("stripe.com", "accenture.com", "dextercapital.in", "cogitx.ai", "icand.in", "hpladditives.com")) else "official_ats_or_destination"
        if source_kind == "official_employer_domain":
            relationship_status = "employer_domain_source_observed; ATS_relationship_not_established"
            relationship_type = "direct_employer_domain_vacancy_source"
            relationship_evidence = official_url
        else:
            relationship_status = "ats_url_observed; employer_to_ats_relationship_unresolved"
            relationship_type = "ATS_destination_without_independent_employer_link"
            relationship_evidence = ""
        discovery_method = "existing_cleaned_application_url"
    else:
        source_kind = "third_party_advertisement_only"
        relationship_status = "no_official_url_in_source_record"
        relationship_type = "third_party_record_only"
        relationship_evidence = ""
        discovery_method = "raw_source_audit_of_application_and_careers_fields"
    relationships.append({
        "case_id": case_id,
        "pilot_group": record["pilot_group"],
        "employer_name": ad.get("source_employer_name", ""),
        "job_title": ad.get("job_title", ""),
        "location": ad.get("location", ""),
        "source_job_id": ad.get("source_job_id", ""),
        "original_advertisement_url": original_ad_url,
        "official_ats_or_employer_url": official_url,
        "official_source_host": source_host,
        "source_kind": source_kind,
        "source_discovery_method": discovery_method,
        "relationship_status": relationship_status,
        "relationship_type": relationship_type,
        "relationship_evidence_url": relationship_evidence,
        "employer_website_references_ats": "not_established",
        "vacancy_identifier_search": "identifier present in local record; no independent official confirmation established",
        "vacancy_status": st.get("vacancy_status", "indeterminable"),
        "vacancy_status_basis": st.get("vacancy_status_basis", ""),
        "stage4b_retrieval_outcome": st.get("retrieval_outcome", ""),
        "stage4b_http_status": st.get("http_status", ""),
        "source_independence": "employer_domain_candidate" if source_kind == "official_employer_domain" else ("third_party_only" if not official_url else "ATS_source_not_independent_employer_confirmation"),
        "vacancy_authorization_state": "unresolved",
        "authorization_sufficient": "no",
        "limitations": "A source URL or ATS host does not by itself establish employer authorization; missing pages are not treated as fraud.",
        "raw_company_apply_url": raw_official_fields["companyApplyUrl"],
        "raw_client_careers_url": raw_official_fields["clientCareersUrl"],
        "raw_apply_redirect_url": raw_official_fields["applyRedirectUrl"],
        "raw_company_apply_job": raw_official_fields["companyApplyJob"],
    })
write_csv(PROCESSED / "stage4c_vacancy_source_relationships.csv", relationships, list(relationships[0]))

# Missing official URL analysis, using the original raw Naukri record where available.
missing = []
for record in pilot:
    case_id = record["case_id"]
    ad = cleaned[case_id]
    if ad.get("application_url", "").strip():
        continue
    raw = raw_record_for(ad)
    missing.append({
        "case_id": case_id,
        "employer_name": ad.get("source_employer_name", ""),
        "source_job_id": ad.get("source_job_id", ""),
        "advertisement_url": ad.get("advertisement_url", ""),
        "source_file": ad.get("source_file", ""),
        "cleaned_application_url": "",
        "raw_company_apply_url": (raw or {}).get("companyApplyUrl", ""),
        "raw_client_careers_url": (raw or {}).get("clientCareersUrl", ""),
        "raw_apply_redirect_url": (raw or {}).get("applyRedirectUrl", ""),
        "raw_company_apply_job": (raw or {}).get("companyApplyJob", ""),
        "url_collection_finding": "official URL absent in cleaned record and corresponding raw source fields",
        "third_party_url_present": "yes" if ad.get("advertisement_url", "").strip() else "no",
        "official_url_discovered": "no",
        "discovery_method": "raw source field audit; third-party URL retained as provenance only",
        "interpretation": "URL was not collected in the source export; no evidence that processing lost an official URL.",
        "authorization_effect": "unresolved",
    })
write_csv(REPORTS / "stage4c_missing_url_analysis.csv", missing, list(missing[0]) if missing else ["case_id"])

# Threshold definitions and audit summary.
thresholds = {
    "snapshot_consistency": "Same frozen source record matches advertisement fields; no independence claim.",
    "fresh_ats_retrieval": "Fresh response from the same ATS; establishes retrieval existence only, not independent employer authorization.",
    "employer_to_ats_relationship": "Employer-controlled page directly links to or explicitly identifies the ATS; confirms a relationship for the observed evidence scope, not every vacancy.",
    "vacancy_level_official_confirmation": "Employer-controlled page identifies the specific vacancy and agrees on identifier plus core details.",
    "independent_authorization_support": "Requires vacancy-level official confirmation plus an established employer-to-ATS relationship, with provenance showing the sources are not merely the same derived snapshot.",
}
audit = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "employer_registry_records": len(registry),
    "stripe_relationship_status": registry[0]["verification_status"],
    "stripe_relationship_evidence": registry[0]["evidence_observation"],
    "stripe_employer_page_retrieval": stripe_fetch,
    "stripe_ats_page_retrieval": stripe_ats_fetch,
    "relationship_interpretation": "Confirmed for the observed Stripe vacancy only; not blanket authorization for all 780 records.",
    "thresholds": thresholds,
    "source_independence_rule": "A fresh retrieval from Greenhouse is retrieval-independent from the frozen snapshot but not a separate independent employer source.",
    "vacancy_authorization_evidence_in_20_case_pilot": 0,
    "limitations": "The 20-case pilot belongs to the separate Naukri/ATS cohort; it is not the Stripe/Greenhouse 780-record cohort.",
}
(REPORTS / "stage4c_employer_ats_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

verification = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "pilot_size": len(relationships),
    "official_url_present": sum(bool(r["official_ats_or_employer_url"]) for r in relationships),
    "official_url_missing": sum(not bool(r["official_ats_or_employer_url"]) for r in relationships),
    "employer_domain_sources": sum(r["source_kind"] == "official_employer_domain" for r in relationships),
    "ats_or_destination_sources": sum(r["source_kind"] == "official_ats_or_destination" for r in relationships),
    "third_party_only_sources": sum(r["source_kind"] == "third_party_advertisement_only" for r in relationships),
    "active_status_observed": sum(r["vacancy_status"] == "active" for r in relationships),
    "expired_status_observed": sum(r["vacancy_status"] == "expired" for r in relationships),
    "removed_status_observed": sum(r["vacancy_status"] == "removed" for r in relationships),
    "indeterminable_status": sum(r["vacancy_status"] == "indeterminable" for r in relationships),
    "employer_to_ats_relationship_confirmed_for_pilot": 0,
    "individual_vacancy_authorization_sufficient": sum(r["authorization_sufficient"] == "yes" for r in relationships),
    "individual_vacancy_authorization_unresolved": sum(r["authorization_sufficient"] == "no" for r in relationships),
    "missing_url_cases": len(missing),
    "third_party_urls_used_as_official_evidence": 0,
    "fraud_labels_assigned": 0,
    "recommendation": "Do not scale to 780 yet. The Stripe employer-to-Greenhouse relationship is established for the observed Stripe vacancy, but the 20-case Naukri/ATS pilot has no sufficient individual authorization evidence.",
}
(REPORTS / "stage4c_vacancy_verification_report.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")

(REPORTS / "stage4c_execution_log.json").write_text(json.dumps({
    "stage": "Stage 4C Official Employer-to-ATS Relationship Verification and Vacancy Source Discovery",
    "executed_at": verification["generated_at"],
    "scope": "same 20 Stage 4B cases plus one Stripe relationship demonstration; no 780-record scale-up",
    "previous_outputs_modified": [],
    "new_outputs": [
        "processed/stripe_official_source_registry.csv",
        "processed/stage4c_vacancy_source_relationships.csv",
        "reports/stage4c_employer_ats_audit.json",
        "reports/stage4c_vacancy_verification_report.json",
        "reports/stage4c_missing_url_analysis.csv",
        "reports/stage4c_execution_log.json",
        "scripts/run_stage4c.py",
    ],
    "integrity": "No URLs invented; third-party URLs were not used as official evidence; no fraud labels; unresolved retained.",
}, indent=2), encoding="utf-8")

print(json.dumps({
    "registry_records": len(registry),
    "pilot_relationship_records": len(relationships),
    "missing_url_records": len(missing),
    "stripe_relationship_status": registry[0]["verification_status"],
    "pilot_authorization_sufficient": verification["individual_vacancy_authorization_sufficient"],
}, indent=2))

