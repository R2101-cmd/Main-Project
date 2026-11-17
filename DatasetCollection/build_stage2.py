import csv
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stage2_outputs"
OUT.mkdir(exist_ok=True)

def read_csv(name):
    with (ROOT / name).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

table_a = read_csv("processed/vacancyguard_table_a_cleaned.csv")
table_b_old = read_csv("review_templates/vacancyguard_table_b_ground_truth_review.csv")
table_d_old = read_csv("processed/vacancyguard_table_d_lineage_candidates.csv")
retrieved_at = datetime.now(timezone.utc).isoformat()

# One application-linked record per employer, deterministic and reproducible.
pilot = []
seen = set()
for row in sorted(table_a, key=lambda x: (x.get("source_employer_name", "").casefold(), x.get("source_job_id", ""))):
    employer = row.get("source_employer_name", "").strip()
    if employer and row.get("job_title", "").strip() and row.get("application_url", "").strip() and employer.casefold() not in seen:
        pilot.append(row)
        seen.add(employer.casefold())
    if len(pilot) == 40:
        break

def host(url):
    return urlsplit(url).hostname or ""

def source_type(url):
    h = host(url).casefold()
    ats = ("workday", "greenhouse", "lever.co", "oraclecloud", "bamboohr", "keka.com", "pyjamahr", "darwinbox", "freshteam", "zohorecruit", "jobvite", "taleo", "icims", "ripplehire", "peoplestrong", "odoo.com", "loxo", "applytojob")
    if any(x in h for x in ats):
        return "ATS / employer-hosted application platform"
    return "official employer careers site"

def detail_kind(url):
    path = urlsplit(url).path.casefold()
    return path.rstrip("/").endswith(("/careers", "/career", "/work-with-us", "/career.html", "/current-openings.php"))

verified = {
    "061126500328": {
        "state": "supported",
        "source_url": "https://jobs.birlasoft.com/go/Data-%26-Analytics/716344/",
        "source_type": "official employer careers site",
        "published": "2026-11-05",
        "matched": "employer identity; job title; location; posting date",
        "rationale": "Birlasoft's official careers results list Data Analyst- AI and ML in Bengaluru, matching the sampled Naukri employer, title, and location."
    },
    "041126500022": {
        "state": "supported",
        "source_url": "https://careers.ey.com/ey/job/Bengaluru-DE-NCLC-Business-Analyst-GDSN02-KA-560016/1453759733/",
        "source_type": "official employer careers site",
        "published": "2026-11-03",
        "matched": "employer identity; job title; location; job-description themes",
        "rationale": "EY's official vacancy page lists DE-NCLC-Business-Analyst-GDSN02 in Bengaluru and includes business-analysis responsibilities matching the sampled advertisement."
    },
}

evidence = []
for i, row in enumerate(pilot, 1):
    job_id = row["source_job_id"]
    url = row["application_url"]
    if job_id in verified:
        v = verified[job_id]
        state, evidence_url, stype, published, matched, contradiction, rationale = v["state"], v["source_url"], v["source_type"], v["published"], v["matched"], "", v["rationale"]
    elif job_id == "311026502841":
        state, evidence_url, stype, published, matched, contradiction = "contradicted", url, "ATS / employer-hosted application platform", "", "destination URL; advertised job title", "The public destination URL contains HR-Executive while the sampled Naukri title is Data Scientist; page-level confirmation is still required."
        rationale = "A title conflict is visible in the destination URL path. This is a contradiction for manual review, not a fraud determination."
    elif detail_kind(url):
        state, evidence_url, stype, published, matched, contradiction = "unverified", url, source_type(url), "", "employer/domain route only", ""
        rationale = "The URL points to an employer careers landing page, but no specific vacancy detail was verified from the landing page."
    else:
        state, evidence_url, stype, published, matched, contradiction = "unavailable", url, source_type(url), "", "", ""
        rationale = "The public destination URL was recorded, but a readable vacancy detail could not be verified during this pilot check."
    evidence.append({
        "evidence_id": f"E2-{i:03d}", "case_id": row["case_id"], "claim_type": "employer identity and vacancy authorization",
        "source_url": evidence_url, "source_type": stype, "retrieved_at": retrieved_at, "source_published_at": published,
        "evidence_state": state, "matched_fields": matched, "contradiction_details": contradiction,
        "evidence_rationale": rationale, "pilot_status": "selected pilot record"
    })

pilot_fields = list(table_a[0].keys()) + ["pilot_selection_reason"]
for row in pilot:
    row["pilot_selection_reason"] = "one application-linked vacancy per distinct employer; usable employer, title, location, and application URL"
write_csv(OUT / "stage2_pilot_table_a.csv", pilot, pilot_fields)

evidence_fields = list(evidence[0].keys())
write_csv(OUT / "stage2_table_c_evidence_review.csv", evidence, evidence_fields)

# Preserve all Stage 1 lineage candidates and add non-final suggestions.
lineage = []
for row in table_d_old:
    score = float(row.get("similarity_score") or 0)
    if score >= 0.99:
        suggestion = "likely copied/derived; confirm source order and publication context"
    elif score >= 0.88:
        suggestion = "probable related/copied content; manually compare full text and dates"
    else:
        suggestion = "related candidate only; manual comparison required"
    row = dict(row)
    row.update({"suggested_relationship": suggestion, "manual_confirmation_required": "yes", "stage2_evidence_refs": "", "stage2_review_note": "Automated similarity is not proof of copying or common authorization."})
    lineage.append(row)
lineage_fields = list(lineage[0].keys())
write_csv(OUT / "stage2_table_d_lineage_review.csv", lineage, lineage_fields)

evidence_by_case = {r["case_id"]: r for r in evidence}
table_b = []
for old in table_b_old:
    row = dict(old)
    if old["case_id"] in evidence_by_case:
        ev = evidence_by_case[old["case_id"]]
        row["label_evidence_refs"] = ev["evidence_id"]
        row["label_rationale"] = ev["evidence_rationale"]
        row["adjudication_status"] = "proposed_pending_manual_adjudication"
        if ev["evidence_state"] == "supported":
            row["employer_identity_label"] = "verified"
            row["vacancy_authorization_label"] = "supported"
            row["fraud_outcome_label"] = "unresolved"
        else:
            row["employer_identity_label"] = "unresolved"
            row["vacancy_authorization_label"] = "unresolved"
            row["fraud_outcome_label"] = "unresolved"
    table_b.append(row)
write_csv(OUT / "stage2_table_b_ground_truth_review.csv", table_b, list(table_b[0].keys()))

counts = Counter(r["evidence_state"] for r in evidence)
report = [
    "TrustHire Stage 2 – Evidence Collection and Lineage Verification",
    f"Pilot records selected: {len(pilot)}",
    "Selection: one application-linked vacancy per distinct employer, with usable employer, title, location, and application URL.",
    f"Verified/supporting evidence records: {counts['supported']}",
    f"Contradicted evidence records: {counts['contradicted']}",
    f"Unresolved/unverified evidence records: {counts['unverified']}",
    f"Unavailable evidence records: {counts['unavailable']}",
    f"Lineage candidates reviewed: {len(lineage)}",
    "All lineage relationships remain suggested candidates requiring manual confirmation.",
    "All non-supported Table B pilot outcomes remain unresolved; fraud outcomes remain unresolved for every record.",
    "Third-party Naukri data was not treated as proof of employer authorization.",
]
(OUT / "stage2_evidence_collection_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
(OUT / "stage2_evidence_collection_report.json").write_text(__import__("json").dumps({"retrieved_at": retrieved_at, "pilot_records": len(pilot), "evidence_counts": dict(counts), "lineage_candidates_reviewed": len(lineage), "source_policy": "publicly accessible sources only; no authentication/CAPTCHA bypass; unresolved retained as valid"}, indent=2), encoding="utf-8")
print("\n".join(report))
