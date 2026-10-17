from src.evidence.collector import candidate_official_sources, collect_vacancy_evidence
from src.ingestion.content_extractor import extract_text


def test_collector_records_supported_match_without_live_network():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics. Location: Bengaluru")
    def fake_fetcher(url):
        return {"content_type": "text/html", "content": '<main><p>Title: Data Analyst Intern</p><p>Company: Rusaanalytics</p><p>Location: Bengaluru</p></main>'}
    result = collect_vacancy_evidence(advertisement, ["https://rusaanalytics.example/careers"], fake_fetcher)
    assert result[0]["evidence_state"] == "supported"
    assert result[0]["retrieval_status"] == "available"
    assert result[0]["source_url"].endswith("careers")
    assert result[0]["details"]["matched_fields"] == ["title", "employer", "location"]
    assert "Data Analyst Intern" in result[0]["details"]["evidence_excerpt"]


def test_third_party_repost_matches_vacancy_but_not_authorization():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics. Location: Bengaluru")
    def repost_fetcher(url):
        return {"content_type": "text/html", "content": "<main><p>Title: Data Analyst Intern</p><p>Company: Rusaanalytics</p><p>Location: Bengaluru</p></main>"}
    result = collect_vacancy_evidence(advertisement, ["https://www.indeed.com/viewjob?jk=abc"], repost_fetcher)
    assert result[0]["evidence_state"] == "unverified"
    assert result[0]["details"]["vacancy_match"] is True
    assert "authorization is unresolved" in result[0]["rationale"]


def test_matching_title_without_authorization_evidence_is_unresolved():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics")
    def public_fetcher(url):
        return {"content_type": "text/html", "content": "<main><p>Title: Data Analyst Intern</p></main>"}
    result = collect_vacancy_evidence(advertisement, ["https://jobs.example.net/data-analyst"], public_fetcher)
    assert result[0]["evidence_state"] == "unverified"
    assert result[0]["details"]["matched_fields"] == ["title"]


def test_missing_application_link_is_recorded_separately():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics. Location: Bengaluru")
    def employer_fetcher(url):
        return {"content_type": "text/html", "content": "<main><p>Title: Data Analyst Intern</p><p>Company: Rusaanalytics</p><p>Location: Bengaluru</p></main>"}
    result = collect_vacancy_evidence(advertisement, ["https://rusaanalytics.example/careers"], employer_fetcher)
    assert result[0]["evidence_state"] == "supported"
    assert result[0]["details"]["candidate_application_url"] is None
    assert result[0]["details"]["application_url_match"] is False


def test_third_party_source_preserves_submitted_and_final_urls():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics. Location: Bengaluru")
    def redirect_fetcher(url):
        return {"url": "https://www.indeed.com/viewjob?jk=final", "content_type": "text/html", "content": "<main><p>Title: Data Analyst Intern</p><p>Company: Rusaanalytics</p><p>Location: Bengaluru</p></main>"}
    result = collect_vacancy_evidence(advertisement, ["https://short.example/job"], redirect_fetcher)
    assert result[0]["source_type"] == "third_party_recruitment_platform"
    assert result[0]["details"]["submitted_url"] == "https://short.example/job"
    assert result[0]["details"]["final_url"] == "https://www.indeed.com/viewjob?jk=final"
    assert result[0]["evidence_state"] == "unverified"


def test_collector_records_retrieval_failure_as_unavailable():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics")
    def failing_fetcher(url):
        raise TimeoutError("blocked")
    result = collect_vacancy_evidence(advertisement, ["https://official.example/careers"], failing_fetcher)
    assert result[0]["evidence_state"] == "unavailable"
    assert result[0]["retrieval_status"] == "failed"


def test_no_source_is_not_fraud():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics")
    result = collect_vacancy_evidence(advertisement, [], lambda _: None)
    assert result[0]["evidence_state"] == "unavailable"
    assert result[0]["retrieval_status"] == "unavailable"


def test_retrieved_non_job_page_is_extraction_unavailable():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics")
    def non_job_fetcher(url):
        return {"content_type": "text/html", "content": "<html><body><nav>Sign in</nav></body></html>"}
    result = collect_vacancy_evidence(advertisement, ["https://official.example/home"], non_job_fetcher)
    assert result[0]["retrieval_status"] == "available"
    assert result[0]["evidence_state"] == "unavailable"
    assert "Extraction failure" in result[0]["rationale"]


def test_original_specific_url_is_checked_before_generic_page_links():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Integra FEC. Location: Austin, Texas")
    sources = candidate_official_sources(advertisement, "https://job-boards.greenhouse.io/integra/jobs/5406100008")
    assert sources == ["https://job-boards.greenhouse.io/integra/jobs/5406100008"]
