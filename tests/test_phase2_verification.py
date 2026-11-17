from datetime import date

from src.evidence.collector import collect_vacancy_evidence
from src.ingestion.content_extractor import extract_text


def _ad(text):
    return extract_text(text)


def _page(html, url=None, status=200):
    out = {"content_type": "text/html", "content": html, "http_status": status}
    if url:
        out["url"] = url
    return out


def test_exact_job_id_match_supports_authoritative_source():
    today = date.today().isoformat()
    ad = _ad(f"Title: Data Analyst. Company: Acme Corp. Location: Bengaluru. Job ID: REQ-12345. Posted: {today}")
    def f(url):
        return _page(f"<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p><p>Job ID: REQ-12345</p><p>Posted: {today}</p></main>")
    r = collect_vacancy_evidence(ad, ["https://careers.acmecorp.example/jobs/1"], f, authorized_domains={"careers.acmecorp.example"})[0]
    assert r["verification_status"] == "independently_supported"
    assert r["details"]["field_comparisons"]["job_id"]["status"] == "exact_match"
    assert r["details"]["job_id_match"] is True


def test_wrong_job_id_is_contradictory_on_authoritative_source():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. Job ID: REQ-12345")
    def f(url):
        return _page("<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Job ID: REQ-99999</p></main>")
    r = collect_vacancy_evidence(ad, ["https://careers.acmecorp.example/jobs/1"], f, authorized_domains={"careers.acmecorp.example"})[0]
    assert r["details"]["field_comparisons"]["job_id"]["status"] == "conflict"
    assert r["verification_status"] in {"independently_contradicted", "independently_unresolved"}
    assert r["evidence_state"] in {"contradicted", "unverified"}


def test_similar_job_titles_without_strong_identity_not_sufficient_for_support():
    ad = _ad("Title: Senior Data Analyst. Company: Acme Corp. Location: Remote")
    def f(url):
        return _page("<main><p>Title: Data Analyst II</p><p>Location: Remote</p></main>")
    r = collect_vacancy_evidence(ad, ["https://jobs.unknown.example/1"], f)[0]
    assert r["details"]["matching_explanation"]["vacancy_correspondence"] in {False, True}
    # title similarity alone must not establish authorization support
    assert r["verification_status"] != "independently_supported"
    assert r["evidence_state"] != "supported"


def test_different_locations_recorded_in_field_comparison():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. Location: Bengaluru")
    def f(url):
        return _page("<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Mumbai</p></main>")
    r = collect_vacancy_evidence(ad, ["https://careers.acmecorp.example/jobs/1"], f, authorized_domains={"careers.acmecorp.example"})[0]
    assert r["details"]["field_comparisons"]["location"]["advertised"] == "Bengaluru"
    assert r["details"]["field_comparisons"]["location"]["observed"] == "Mumbai"
    assert r["details"]["field_comparisons"]["location"]["status"] in {"mismatch", "conflict", "similar_match", "exact_match"}


def test_employer_mismatch_prevents_support():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. Location: Bengaluru")
    def f(url):
        return _page("<main><p>Title: Data Analyst</p><p>Company: Other Corp</p><p>Location: Bengaluru</p></main>")
    r = collect_vacancy_evidence(ad, ["https://careers.acmecorp.example/jobs/1"], f, authorized_domains={"careers.acmecorp.example"})[0]
    assert r["evidence_state"] != "supported"
    assert r["details"]["field_comparisons"]["employer_identity"]["status"] in {"mismatch", "conflict"}


def test_description_similarity_captured():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. We analyze product metrics, build dashboards, and support experiments with SQL and Python.")
    def f(url):
        return _page("<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Analyze product metrics, build dashboards, and run experiments using SQL and Python.</p></main>")
    r = collect_vacancy_evidence(ad, ["https://careers.acmecorp.example/jobs/1"], f, authorized_domains={"careers.acmecorp.example"})[0]
    sim = r["details"]["matching_explanation"]["description_similarity"]
    assert sim >= 0.5
    assert r["details"]["field_comparisons"]["job_description"]["status"] in {"similar_match", "exact_match", "mismatch"}


def test_third_party_source_not_authoritative():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. Location: Bengaluru")
    def f(url):
        return _page("<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p></main>")
    r = collect_vacancy_evidence(ad, ["https://www.indeed.com/viewjob?jk=abc"], f)[0]
    assert r["details"]["employer_relationship"] == "third_party_portal"
    assert r["verification_status"] != "independently_supported"
    assert r["evidence_state"] != "supported"


def test_verified_ats_relationship_can_support():
    today = date.today().isoformat()
    ad = _ad(f"Title: Data Analyst. Company: Acme Corp. Location: Bengaluru. Job ID: REQ-1. Posted: {today}")
    def f(url):
        return _page(f"<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p><p>Job ID: REQ-1</p><p>Posted: {today}</p></main>")
    r = collect_vacancy_evidence(ad, ["https://boards.greenhouse.io/acme/jobs/1"], f, authorized_domains={"greenhouse.io"})[0]
    assert r["details"]["employer_relationship"] == "verified_employer_associated_ats"
    assert r["verification_status"] == "independently_supported"
    assert r["evidence_state"] == "supported"


def test_unverified_ats_relationship_not_authoritative():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. Location: Bengaluru")
    def f(url):
        return _page("<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p></main>")
    r = collect_vacancy_evidence(ad, ["https://boards.greenhouse.io/unknown/jobs/1"], f)[0]
    assert r["details"]["employer_relationship"] == "unverified_ats"
    assert r["verification_status"] != "independently_supported"
    assert r["evidence_state"] != "supported"


def test_snapshot_only_match_distinct_from_independent():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. Location: Bengaluru")
    def f(url):
        return _page("<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p></main>")
    r = collect_vacancy_evidence(ad, ["https://web.archive.org/web/20240101/https://acme.example/jobs/1"], f)[0]
    assert r["verification_status"] == "snapshot_match_only"
    assert r["evidence_state"] != "supported"
    assert r["details"]["employer_relationship"] == "archived_or_historical_snapshot"


def test_independent_official_evidence_preserves_provenance():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. Location: Bengaluru")
    def f(url):
        return _page("<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p></main>", url="https://careers.acmecorp.example/jobs/final")
    r = collect_vacancy_evidence(ad, ["https://careers.acmecorp.example/jobs/1"], f, authorized_domains={"careers.acmecorp.example"})[0]
    d = r["details"]
    assert d.get("source_url") or d.get("final_url")
    assert d.get("retrieval_timestamp")
    assert d.get("extraction_method")
    assert "field_comparisons" in d
    assert "verification_status" in d
    assert "employer_relationship" in d


def test_missing_evidence_is_inaccessible_not_fraud():
    ad = _ad("Title: Data Analyst. Company: Acme Corp")
    r = collect_vacancy_evidence(ad, [], lambda u: None)[0]
    assert r["verification_status"] == "inaccessible"
    assert r["evidence_state"] == "unavailable"
    assert "fraud" not in r["rationale"].lower()


def test_inaccessible_official_website_recorded():
    ad = _ad("Title: Data Analyst. Company: Acme Corp")
    def f(url):
        raise TimeoutError("timed out")
    r = collect_vacancy_evidence(ad, ["https://careers.acmecorp.example/jobs/1"], f)[0]
    assert r["verification_status"] == "inaccessible"
    assert r["retrieval_status"] == "failed"
    assert r["evidence_state"] == "unavailable"
    assert r["details"]["http_status"] is None


def test_contradictory_evidence_authoritative_source():
    today = date.today().isoformat()
    ad = _ad(f"Title: Data Analyst. Company: Acme Corp. Location: Bengaluru. Job ID: REQ-8. Posted: {today}")
    def f(url):
        return _page(f"<main><p>Title: Security Engineer</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p><p>Job ID: REQ-8</p><p>Posted: {today}</p></main>")
    r = collect_vacancy_evidence(ad, ["https://careers.acmecorp.example/jobs/1"], f, authorized_domains={"careers.acmecorp.example"})[0]
    assert r["details"]["field_comparisons"]["job_title"]["status"] in {"mismatch", "conflict"}
    assert r["evidence_state"] == "contradicted"
    assert r["verification_status"] == "independently_contradicted"


def test_stale_posting_is_unresolved_even_on_verified_employer_domain():
    ad = _ad("Title: Data Analyst. Company: Acme Corp. Location: Bengaluru. Job ID: REQ-1. Posted: 2020-01-01")
    page = '<main><p>Title: Data Analyst</p><p>Company: Acme Corp</p><p>Location: Bengaluru</p><p>Job ID: REQ-1</p><p>Posted: 2020-01-01</p></main>'
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page(page), authorized_domains={"careers.acme.example"})[0]
    assert result["details"]["matching_explanation"]["stale_evidence"] is True
    assert result["verification_status"] == "independently_unresolved"
    assert result["evidence_state"] == "unverified"


def test_identity_and_vacancy_authorization_are_separate():
    ad = _ad("Company: Acme Corp")
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page("<main><p>Company: Acme Corp</p></main>"), authorized_domains={"careers.acme.example"})[0]
    explanation = result["details"]["matching_explanation"]
    assert explanation["employer_identity_status"] == "verified"
    assert explanation["vacancy_authorization_status"] in {"not_comparable", "independently_unresolved"}
    assert result["evidence_state"] != "supported"


def test_hostname_resemblance_does_not_verify_employer_or_ats():
    ad = _ad("Title: Analyst. Company: Acme Corp. Location: Remote")
    page = "<main><p>Title: Analyst</p><p>Company: Acme Corp</p><p>Location: Remote</p></main>"
    for url in ("https://careers.acmecorp.example/jobs/1", "https://acmecorp.greenhouse.io/jobs/1"):
        result = collect_vacancy_evidence(ad, [url], lambda _: _page(page))[0]
        assert result["details"]["authority_assessment"]["authority_level"] != "employer_authoritative"
        assert result["details"]["matching_explanation"]["employer_identity_status"] == "unresolved"
        assert result["verification_status"] != "independently_supported"


def test_missing_salary_and_employment_type_are_not_contradictions():
    ad = _ad("Title: Analyst. Company: Acme Corp. Location: Remote")
    result = collect_vacancy_evidence(ad, ["https://careers.acme.example/jobs/1"], lambda _: _page("<main><p>Title: Analyst</p><p>Company: Acme Corp</p><p>Location: Remote</p></main>"), authorized_domains={"careers.acme.example"})[0]
    fields = result["details"]["field_comparisons"]
    assert fields["salary"]["status"] == "not_comparable"
    assert fields["employment_type"]["status"] == "not_comparable"
    assert "salary" not in result["details"]["contradicted_fields_all"]
    assert "employment_type" not in result["details"]["contradicted_fields_all"]
