import json
from datetime import date, timedelta

from src.aggregation.rules import lineage_aware
from src.decision.policy import assess, qualifying_independent_source_count
from src.evidence.authority_config import authority_for_employer, load_authority_config
from src.evidence.collector import collect_vacancy_evidence
from src.ingestion.content_extractor import extract_text
from src.ui_support import comparison_rows


def _page(text):
    return {"content_type": "text/html", "http_status": 200, "content": f"<main>{text}</main>"}


def test_authority_mapping_requires_verified_provenance_relationship_and_employer(tmp_path):
    config_file = tmp_path / "authority.json"
    config_file.write_text(json.dumps({"schema_version": "employer-sources-v1", "max_current_posting_age_days": 180, "mappings": [
        {"employer_id": "acme", "canonical_employer_name": "Acme Corp", "authorized_domain": "careers.acme.example", "relationship_type": "employer_owned_official", "verification_status": "verified", "verification_provenance": "company legal footer", "last_verified_at": "2026-01-01"},
        {"employer_id": "bad", "canonical_employer_name": "Acme Corp", "authorized_domain": "bad.example", "relationship_type": "employer_owned_official", "verification_status": "unverified", "verification_provenance": "", "last_verified_at": ""},
        {"employer_id": "wrong", "canonical_employer_name": "Other Corp", "authorized_domain": "other.example", "relationship_type": "verified_employer_associated_ats", "verification_status": "verified", "verification_provenance": "employer ATS page", "last_verified_at": "2026-01-01"}
    ]}), encoding="utf-8")
    config = load_authority_config(config_file)
    domains, rows = authority_for_employer("Acme Corp", config)
    assert domains == {"careers.acme.example"}
    assert len(rows) == 1 and rows[0]["verification_provenance"] == "company legal footer"
    assert authority_for_employer("Unknown Employer", config) == (set(), [])


def test_authority_configuration_is_scoped_to_verified_stripe_careers_pages():
    config = load_authority_config()
    assert len(config["mappings"]) == 1
    assert authority_for_employer("Stripe", config)[0] == {"stripe.com"}
    assert authority_for_employer("Any Employer", config) == (set(), [])
    assert config["mappings"][0]["authorized_path_prefix"] == "/careers/"


def test_verified_domain_mapping_does_not_authorize_hostname_resemblance(tmp_path):
    path = tmp_path / "domain.json"
    row = {"employer_id": "acme", "canonical_employer_name": "Acme Corp", "authorized_domain": "careers.acme.example", "relationship_type": "employer_owned_official", "verification_status": "verified", "verification_provenance": "verified company careers page", "last_verified_at": "2026-01-01"}
    path.write_text(json.dumps({"schema_version": "employer-sources-v1", "mappings": [row]}), encoding="utf-8")
    domains, mappings = authority_for_employer("Acme Corp", load_authority_config(path))
    today = date.today().isoformat()
    ad = extract_text(f"Title: Analyst. Company: Acme Corp. Job ID: A-1. Posted: {today}")
    page = _page(f"<p>Title: Analyst</p><p>Company: Acme Corp</p><p>Job ID: A-1</p><p>Posted: {today}</p>")
    result = collect_vacancy_evidence(ad, ["https://careers-acme.example/jobs/A-1"], lambda _: page, authorized_domains=domains, authority_mappings=mappings)[0]
    assert result["details"]["authority_assessment"]["authority_level"] != "employer_authoritative"
    assert result["evidence_state"] == "unverified"


def test_verified_employer_associated_ats_requires_explicit_relationship(tmp_path):
    path = tmp_path / "ats.json"
    row = {"employer_id": "acme", "canonical_employer_name": "Acme Corp", "authorized_domain": "greenhouse.io", "authorized_path_prefix": "/acme/", "relationship_type": "verified_employer_associated_ats", "verification_status": "verified", "verification_provenance": "linked from verified careers page", "last_verified_at": "2026-01-01"}
    path.write_text(json.dumps({"schema_version": "employer-sources-v1", "mappings": [row]}), encoding="utf-8")
    config = load_authority_config(path)
    domains, mappings = authority_for_employer("Acme Corp", config)
    today = date.today().isoformat()
    ad = extract_text(f"Title: Analyst. Company: Acme Corp. Job ID: A-100. Posted: {today}")
    page = _page(f"<p>Title: Analyst</p><p>Company: Acme Corp</p><p>Job ID: A-100</p><p>Posted: {today}</p>")
    evidence = collect_vacancy_evidence(ad, ["https://boards.greenhouse.io/acme/jobs/100"], lambda _: page, authorized_domains=domains, authority_mappings=mappings)[0]
    assert evidence["employer_relationship"] == "verified_employer_associated_ats"
    assert evidence["details"]["authority_configuration"][0]["verification_provenance"] == "linked from verified careers page"


def test_generic_shared_ats_domain_without_tenant_path_is_not_loaded(tmp_path):
    path = tmp_path / "generic-ats.json"
    row = {"employer_id": "acme", "canonical_employer_name": "Acme Corp", "authorized_domain": "greenhouse.io", "relationship_type": "verified_employer_associated_ats", "verification_status": "verified", "verification_provenance": "generic ATS hostname only", "last_verified_at": "2026-01-01"}
    path.write_text(json.dumps({"schema_version": "employer-sources-v1", "mappings": [row]}), encoding="utf-8")
    assert load_authority_config(path)["mappings"] == []


def test_live_collector_records_lineage_candidates_but_never_adjudicates_them():
    now = date.today().isoformat()
    ad = extract_text(f"Title: Data Analyst. Company: Acme Corp. Location: Bengaluru. Job ID: R-10. Posted: {now}")
    content = f"<p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p><p>Job ID: R-10</p><p>Posted: {now}</p><p>Build analytics dashboards with SQL and Python for product teams.</p>"
    evidence = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/10", "https://jobs.acme.example/role/10"], lambda _: _page(content), authorized_domains={"acme.example"})
    assert len(evidence) == 2
    for item in evidence:
        assert item["evidence_id"]
        assert item["source_family"]
        assert item["source_relationship"] == "unknown"
        assert item["lineage_group_id"] is None
        assert item["lineage_status"] == "not_assessed"
        assert item["lineage_review_status"] == "not_assessed"
    assert evidence[0]["details"]["lineage_candidates"][0]["review_status"] == "candidate"
    assert evidence[0]["details"]["lineage_candidates"][0]["candidate_relationship"] in {"copied_derived_candidate", "unknown_candidate", "independent_candidate"}
    assert lineage_aware(evidence).state == "unresolved"


def test_salary_comparison_only_conflicts_with_comparable_currency_and_period():
    today = date.today().isoformat()
    ad = extract_text(f"Title: Analyst. Company: Acme Corp. Location: Remote. Job ID: R-1. Posted: {today}. Salary: INR 10 LPA")
    candidate = f"<p>Title: Analyst</p><p>Company: Acme Corp</p><p>Location: Remote</p><p>Job ID: R-1</p><p>Posted: {today}</p><p>Salary: USD 100,000 annually</p>"
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page(candidate), authorized_domains={"acme.example"})[0]
    assert result["details"]["field_comparisons"]["salary"]["status"] == "not_comparable"
    assert "salary" not in result["details"]["matching_explanation"]["material_conflicts"]


def test_comparable_salary_and_employment_conflicts_block_support_without_inventing_fraud():
    today = date.today().isoformat()
    ad = extract_text(f"Title: Analyst. Company: Acme Corp. Location: Remote. Job ID: R-1. Posted: {today}. Salary: INR 10 LPA. Employment type: Full-time")
    source = f"<p>Title: Analyst</p><p>Company: Acme Corp</p><p>Location: Remote</p><p>Job ID: R-1</p><p>Posted: {today}</p><p>Salary: INR 15 LPA</p><p>Employment type: Contract</p>"
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page(source), authorized_domains={"acme.example"})[0]
    fields = result["details"]["field_comparisons"]
    assert fields["salary"]["status"] == "conflict"
    assert fields["employment_type"]["status"] == "mismatch"
    assert result["evidence_state"] == "contradicted"
    assert set(result["details"]["matching_explanation"]["material_conflicts"]) >= {"salary", "employment_type"}
    assert result["verification_status"] == "independently_contradicted"
    final = assess(employer_identity="verified", vacancy_evidence_state="contradicted", evidence_available=1,
                   independent_evidence_count=1, vacancy_correspondence=True, source_authoritative=True,
                   freshness_status="current", supporting_evidence_count=0, contradicting_evidence_count=1,
                   material_conflicts=["employment_type", "salary"])
    assert final["vacancy_authorization"] == "unresolved"
    assert final["fraud_outcome"] == "unresolved"


def test_date_posted_modified_valid_through_are_distinct():
    body = '''<script type="application/ld+json">{"@type":"JobPosting","title":"Analyst","datePosted":"2026-01-02","dateModified":"2026-02-03","validThrough":"2026-03-04","hiringOrganization":{"name":"Acme"}}</script>'''
    result = extract_text(body, is_html=True)
    assert result.date_posted == "2026-01-02"
    assert result.posting_date == "2026-01-02"
    assert result.date_modified == "2026-02-03"
    assert result.valid_through == "2026-03-04"


def test_future_source_date_remains_unresolved():
    future = (date.today() + timedelta(days=30)).isoformat()
    ad = extract_text(f"Title: Analyst. Company: Acme Corp. Location: Remote. Job ID: R-1. Posted: {future}")
    page = f"<p>Title: Analyst</p><p>Company: Acme Corp</p><p>Location: Remote</p><p>Job ID: R-1</p><p>Posted: {future}</p>"
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page(page), authorized_domains={"acme.example"})[0]
    assert result["details"]["matching_explanation"]["freshness"]["status"] == "unresolved"
    assert result["evidence_state"] == "unverified"


def test_invalid_source_dates_remain_unresolved():
    ad = extract_text("Title: Analyst. Company: Acme Corp. Job ID: A-1")
    page = "<p>Title: Analyst</p><p>Company: Acme Corp</p><p>Job ID: A-1</p><p>Posted: 32/99/2026</p>"
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page(page), authorized_domains={"acme.example"})[0]
    assert result["details"]["matching_explanation"]["freshness"]["status"] == "unresolved"
    assert result["details"]["matching_explanation"]["freshness"]["basis"] == "invalid_source_date"


def test_missing_official_source_date_and_incomplete_advertisement_remain_unresolved():
    ad = extract_text("Title: Analyst. Company: Acme Corp. Location: Remote. Job ID: A-1")
    page = "<p>Title: Analyst</p><p>Company: Acme Corp</p><p>Location: Remote</p><p>Job ID: A-1</p>"
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page(page), authorized_domains={"acme.example"})[0]
    assert result["details"]["matching_explanation"]["freshness"]["status"] == "unknown"
    assert result["verification_status"] == "independently_unresolved"
    assert result["evidence_state"] == "unverified"


def test_decision_requires_multiple_independent_sources_currentness_and_correspondence():
    one = assess(employer_identity="verified", vacancy_evidence_state="supported", evidence_available=1, independent_evidence_count=1, vacancy_correspondence=True, source_authoritative=True, freshness_status="current", supporting_evidence_count=1, contradicting_evidence_count=0)
    assert one["vacancy_authorization"] == "unresolved"
    assert one["fraud_outcome"] == "unresolved"
    enough = assess(employer_identity="verified", vacancy_evidence_state="supported", evidence_available=2, independent_evidence_count=2, vacancy_correspondence=True, source_authoritative=True, freshness_status="current", supporting_evidence_count=2, contradicting_evidence_count=0)
    assert enough["vacancy_authorization"] == "supported"
    conflict = assess(employer_identity="verified", vacancy_evidence_state="contradicted", evidence_available=2, independent_evidence_count=2, vacancy_correspondence=True, source_authoritative=True, freshness_status="current", supporting_evidence_count=1, contradicting_evidence_count=1)
    assert conflict["vacancy_authorization"] == "unresolved"
    assert "conflicting" in conflict["action"]
    stale = assess(employer_identity="verified", vacancy_evidence_state="supported", evidence_available=2, independent_evidence_count=2, vacancy_correspondence=True, source_authoritative=True, freshness_status="stale", supporting_evidence_count=2, contradicting_evidence_count=0)
    assert stale["vacancy_authorization"] == "unresolved"


def test_authorized_employer_identity_does_not_itself_authorize_vacancy():
    result = assess(employer_identity="verified", vacancy_evidence_state="unresolved", evidence_available=0, independent_evidence_count=0, vacancy_correspondence=False, source_authoritative=True, freshness_status="current")
    assert result["employer_identity"] == "verified"
    assert result["vacancy_authorization"] == "unresolved"
    assert result["fraud_outcome"] == "unresolved"


def test_copied_or_duplicate_records_do_not_satisfy_independent_source_minimum():
    source = {"source_relationship": "independent", "lineage_review_status": "adjudicated", "verification_status": "independently_supported", "lineage_group_id": "ind-1", "source_url": "https://a.example"}
    copies = [dict(source, source_relationship="copied_derived", lineage_group_id="copy-1", source_url=f"https://copy{i}.example") for i in range(3)]
    assert qualifying_independent_source_count([source, source, *copies]) == 1
    assert qualifying_independent_source_count([*copies]) == 0


def test_comparison_table_includes_dates_salary_and_employment_type():
    ad = extract_text("Title: Analyst. Company: Acme. Location: Remote. Salary: INR 5 LPA. Employment type: Full-time")
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page("<p>Title: Analyst</p><p>Company: Acme</p><p>Location: Remote</p>"), authorized_domains={"acme.example"})
    rows = comparison_rows(ad, result)
    labels = {row["Field"] for row in rows}
    assert {"Requisition/job ID", "Salary", "Employment type", "Posting date", "Location", "Employer identity"} <= labels
    assert any(row["Field"] == "Salary" and row["State"] == "Not comparable" for row in rows)
