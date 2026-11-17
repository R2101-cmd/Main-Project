import json
from datetime import date

from src.aggregation.rules import lineage_aware
from src.datasets.staging import load_staging_csv
from src.decision.policy import assess, qualifying_independent_source_count
from src.evidence.collector import collect_vacancy_evidence
from src.evidence.representation import convert_collection_evidence
from src.ingestion.content_extractor import extract_text


def _page(content, url, content_type="text/html"):
    return {"content": content, "content_type": content_type, "http_status": 200, "url": url}


def test_historical_collection_confirmation_maps_to_snapshot_only():
    converted = convert_collection_evidence({
        "case_id": "case-1", "evidence_classification": "independent_official_confirmation",
        "official_response_hash": "hash-1", "retrieval_timestamp": "2026-11-12T16:08:42Z",
        "publication_date": "2026-10-05T16:08:53Z", "updated_date": "2026-10-29T14:42:09Z",
        "source_independence": "separate_employer_controlled_page_and_official_greenhouse_api",
    })
    assert converted["evidence_state"] == "snapshot_match_only"
    assert converted["verification_status"] == "independently_unresolved"
    assert converted["source_relationship"] == "unknown"
    assert converted["lineage_review_status"] == "not_assessed"
    assert converted["details"]["original_classification"] == "independent_official_confirmation"


def test_greenhouse_json_populates_comparable_fields():
    payload = json.dumps({
        "id": 8190059, "title": "Account Executive, Product Sales (Data)", "company_name": "Stripe",
        "location": {"name": "US-SF-HQ, US-NYC, US-CHI, US-SEA"},
        "content": "<p>Build strategic relationships.</p>",
        "first_published": "2026-10-05T12:08:53-04:00", "updated_at": "2026-10-29T10:42:09-04:00",
        "absolute_url": "https://stripe.com/jobs/search?gh_jid=8190059",
    })
    extracted = extract_text(payload)
    assert extracted.job_id == "8190059"
    assert extracted.title == "Account Executive, Product Sales (Data)"
    assert extracted.employer == "Stripe"
    assert extracted.location == "US-SF-HQ, US-NYC, US-CHI, US-SEA"
    assert "strategic relationships" in extracted.description
    assert extracted.date_posted == "2026-10-05T12:08:53-04:00"
    assert extracted.date_modified == "2026-10-29T10:42:09-04:00"
    assert extracted.application_url.endswith("gh_jid=8190059")


def test_greenhouse_missing_json_fields_remain_unknown():
    extracted = extract_text(json.dumps({"id": 7, "title": "Analyst", "company_name": "Acme"}))
    assert extracted.job_id == "7"
    assert extracted.location is None
    assert extracted.date_posted is None
    assert extracted.date_modified is None
    assert extracted.salary is None


def test_retrieval_timestamp_is_not_used_as_posting_date():
    converted = convert_collection_evidence({
        "evidence_state": "fresh_same_system_retrieval",
        "retrieval_timestamp": "2026-11-12T16:08:42Z",
        "publication_date": "2026-10-05T16:08:53Z",
        "updated_date": "2026-10-29T14:42:09Z",
    })
    assert converted["details"]["retrieved_at"] != converted["details"]["source_published_at"]
    assert converted["details"]["retrieved_at"] != converted["details"]["source_modified_at"]


def test_unknown_lineage_does_not_count_as_independent():
    source = {"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "unknown", "source_url": "https://a.example"}
    assert qualifying_independent_source_count([source]) == 0
    assert lineage_aware([source]).state == "unresolved"


def test_two_copies_do_not_satisfy_two_source_requirement():
    copies = [{"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "copied_derived", "lineage_review_status": "adjudicated", "lineage_group": "one-copy-group"} for _ in range(2)]
    assert qualifying_independent_source_count(copies) == 0
    result = assess(employer_identity="verified", vacancy_evidence_state="supported", evidence_available=1, independent_evidence_count=0, vacancy_correspondence=True, source_authoritative=True, freshness_status="current", supporting_evidence_count=1, contradicting_evidence_count=0)
    assert result["vacancy_authorization"] == "unresolved"


def test_two_qualifying_independent_sources_satisfy_existing_policy():
    sources = [{"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "independent", "lineage_review_status": "adjudicated", "lineage_group": f"source-{i}"} for i in (1, 2)]
    assert qualifying_independent_source_count(sources) == 2
    result = assess(employer_identity="verified", vacancy_evidence_state="supported", evidence_available=2, independent_evidence_count=2, vacancy_correspondence=True, source_authoritative=True, freshness_status="current", supporting_evidence_count=2, contradicting_evidence_count=0)
    assert result["vacancy_authorization"] == "supported"


def test_unverified_employer_authority_remains_unresolved():
    today = date.today().isoformat()
    ad = extract_text(f"Title: Analyst. Company: Acme Corp. Location: Remote. Posted: {today}")
    result = collect_vacancy_evidence(ad, ["https://boards.greenhouse.io/acme/jobs/1"], lambda url: _page(f"<main><p>Title: Analyst</p><p>Company: Acme Corp</p><p>Location: Remote</p><p>Posted: {today}</p></main>", url))[0]
    assert result["details"]["authority_assessment"]["authority_level"] == "unverified"
    assert result["evidence_state"] != "supported"


def test_missing_evidence_is_not_fraud():
    result = assess(employer_identity="unresolved", vacancy_evidence_state="unresolved", evidence_available=0, retrieval_failures=1)
    assert result["vacancy_authorization"] == "unresolved"
    assert result["fraud_outcome"] == "unresolved"
