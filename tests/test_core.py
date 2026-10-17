import pytest
from src.aggregation.rules import naive, lineage_aware
from src.decision.policy import assess
from src.evaluation.validation import detect_lineage_leakage, validate_records
from src.ingestion.url_fetcher import UnsafeURL, validate_public_url
from src.lineage.similarity import candidate_relationship, compare

def test_copies_are_consolidated():
    evidence = [{"id": str(i), "evidence_state": "supported", "lineage_group": "g1", "source_url": f"https://p{i}.example"} for i in range(5)]
    assert naive(evidence).effective_sources == 5
    assert lineage_aware(evidence, {"g1"}).effective_sources == 1

def test_missing_listing_abstains():
    result = assess(employer_identity="verified", vacancy_evidence_state="unverified", evidence_available=0)
    assert result["action"] == "insufficient evidence; abstain"

def test_contradiction_is_not_erased_by_employer_identity():
    result = assess(employer_identity="verified", vacancy_evidence_state="contradicted", evidence_available=1)
    assert result["action"] == "affirmative contradiction identified"

def test_uncertain_similarity_remains_unknown():
    relation, _ = candidate_relationship(compare("Python developer building APIs", "Python developer building data systems"))
    assert relation == "unknown"

def test_near_duplicate_is_a_candidate_copy():
    relation, _ = candidate_relationship(compare("Data analyst builds dashboards with Python and SQL", "Data analyst builds dashboards using Python and SQL"))
    assert relation == "copied_derived"

def test_unrelated_ads_are_not_linked():
    relation, _ = candidate_relationship(compare("Warehouse supervisor manages inventory", "Clinical research coordinator schedules participants"))
    assert relation == "independent"

def test_unsafe_url():
    with pytest.raises(UnsafeURL):
        validate_public_url("http://127.0.0.1/private")

def test_leakage_and_validation():
    records = [{"id": "a", "evidence_state": "supported", "lineage_group": "g", "partition": "train"}, {"id": "b", "evidence_state": "supported", "lineage_group": "g", "partition": "test"}]
    assert detect_lineage_leakage(records) == ["g"]
    assert validate_records(records) == []
