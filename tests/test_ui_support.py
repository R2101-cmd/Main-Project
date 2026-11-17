from src.aggregation.rules import lineage_aware, naive
from src.ingestion.content_extractor import extract_text
from src.ui_support import aggregation_summary, comparison_rows, evidence_ledger_rows, evidence_stats, retrieval_label


def test_successful_source_is_counted_as_retrieved_and_relevant():
    evidence = [{
        "source_url": "https://careers.example/jobs/1",
        "source_type": "employer_controlled_or_employer_named_domain",
        "observed_at": "2026-10-22T10:00:00Z",
        "retrieval_status": "available",
        "evidence_state": "supported",
        "rationale": "Matched title and employer.",
        "details": {"matched_fields": ["title", "employer"], "extraction_status": "content_extracted", "http_status": 200},
    }]
    stats = evidence_stats(evidence)
    assert stats["successfully_retrieved"] == 1
    assert stats["relevant_evidence_sources"] == 1
    assert stats["availability_denominator"] == 1
    assert retrieval_label(evidence[0]) == "Retrieved successfully"


def test_failed_source_is_not_relevant_or_supporting():
    evidence = [{
        "source_url": "https://blocked.example/job",
        "retrieval_status": "failed",
        "evidence_state": "unavailable",
        "details": {"error": "connection refused", "extraction_status": "not_attempted"},
    }]
    stats = evidence_stats(evidence)
    assert stats["successfully_retrieved"] == 0
    assert stats["relevant_evidence_sources"] == 0
    assert stats["supporting_items"] == 0
    assert stats["retrieval_failures"] == 1
    assert retrieval_label(evidence[0]) == "Retrieval failed or unavailable"


def test_empty_extraction_is_distinct_from_retrieval_failure():
    evidence = [{
        "source_url": "https://example.org/home",
        "retrieval_status": "available",
        "evidence_state": "unavailable",
        "details": {"extraction_status": "no_usable_content"},
    }]
    stats = evidence_stats(evidence)
    assert stats["successfully_retrieved"] == 1
    assert stats["retrieval_failures"] == 0
    assert retrieval_label(evidence[0]) == "Retrieved, no usable content"


def test_retrieved_source_without_vacancy_match_is_not_called_supporting():
    evidence = [{"retrieval_status": "available", "evidence_state": "unverified", "details": {"vacancy_match": False}}]
    assert retrieval_label(evidence[0]) == "Retrieved, no relevant evidence"


def test_missing_optional_and_malformed_details_are_safe():
    rows = evidence_ledger_rows([{"evidence_state": "unverified", "details": None}])
    assert rows[0]["Source"] == "Not available"
    assert rows[0]["Lineage group"] == "Unknown lineage"
    assert rows[0]["Matched fields"] == "None recorded"


def test_contradicted_field_is_rendered_from_backend_details():
    advertisement = extract_text("Title: Data Analyst Intern. Company: Rusaanalytics. Location: Bengaluru")
    evidence = [{
        "source_url": "https://rusaanalytics.example/careers",
        "evidence_state": "contradicted",
        "rationale": "Same employer, different role.",
        "details": {
            "field_matches": {"title": False, "employer": True, "location": True, "application_url": False},
            "contradicted_fields": ["title"],
            "advertised_values": {"title": "Data Analyst Intern", "employer": "Rusaanalytics", "location": "Bengaluru"},
            "evidence_values": {"title": "Accountant", "employer": "Rusaanalytics", "location": "Bengaluru"},
        },
    }]
    rows = comparison_rows(advertisement, evidence)
    title_row = next(row for row in rows if row["Field"] == "Job title")
    assert title_row["State"] == "Contradicted"
    assert title_row["Observed value"] == "Accountant"


def test_aggregation_summary_reports_unknown_lineage_without_consolidating():
    evidence = [{"source_url": "https://a.example/job", "evidence_state": "unverified", "retrieval_status": "available"}, {"source_url": "https://b.example/job", "evidence_state": "unverified", "retrieval_status": "available"}]
    summary = aggregation_summary(evidence, naive(evidence), lineage_aware(evidence))
    assert summary["consolidated_records"] == 0
    assert summary["lineage_groups"] == []
    assert "unknown relationships" in summary["lineage_review_note"]
