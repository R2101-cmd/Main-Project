import csv
import json
from pathlib import Path

from src.aggregation.rules import naive, lineage_aware
from src.decision.policy import assess
from src.evidence.collector import collect_vacancy_evidence
from src.ingestion.content_extractor import extract_text
from src.ingestion.url_fetcher import UnsafeURL


def test_missing_and_unavailable_evidence_abstains_not_fraud():
    decision = assess(employer_identity="unresolved", vacancy_evidence_state="unavailable", evidence_available=0, retrieval_failures=1)
    assert decision["action"] in {"insufficient evidence; abstain", "authorization unresolved"}
    assert "not proof of fraud" in decision["reason"].lower() or "insufficient" in decision["reason"].lower()
    ev = collect_vacancy_evidence(extract_text(""), [], fetcher=lambda u: (_ for _ in ()).throw(RuntimeError("no")))
    assert ev[0]["evidence_state"] == "unavailable"
    assert ev[0]["retrieval_status"] == "unavailable"


def test_contradictory_evidence_detected():
    evidence = [
        {"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "independent", "lineage_review_status": "adjudicated", "lineage_group": "g1", "source_url": "synthetic://a", "id": "1"},
        {"evidence_state": "contradicted", "verification_status": "independently_contradicted", "source_relationship": "independent", "lineage_review_status": "adjudicated", "lineage_group": "g2", "source_url": "synthetic://b", "id": "2"},
    ]
    assert naive(evidence).state == "contradicted"
    assert lineage_aware(evidence).state == "contradicted"
    decision = assess(employer_identity="unresolved", vacancy_evidence_state="contradicted", evidence_available=2, retrieval_failures=0,
                      independent_evidence_count=2, vacancy_correspondence=True, source_authoritative=True,
                      freshness_status="current", supporting_evidence_count=1, contradicting_evidence_count=1,
                      material_conflicts=["job_title"])
    assert decision["action"] == "conflicting evidence; authorization unresolved"
    assert decision["vacancy_authorization"] == "unresolved"
    assert decision["fraud_outcome"] == "unresolved"


def test_duplicate_and_copied_sources_consolidated_in_lineage_aware():
    evidence = [
        {"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "copied_derived", "lineage_review_status": "adjudicated", "lineage_group": "g1", "source_url": "synthetic://a", "id": "1"},
        {"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "copied_derived", "lineage_review_status": "adjudicated", "lineage_group": "g1", "source_url": "synthetic://a-copy", "id": "2"},
        {"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "copied_derived", "lineage_review_status": "adjudicated", "lineage_group": "g1", "source_url": "synthetic://a-copy2", "id": "3"},
    ]
    assert naive(evidence).effective_sources == 3
    assert lineage_aware(evidence, dependent_group_keys={"g1"}).effective_sources == 1


def test_unknown_lineage_not_assumed_independent_or_confirmed():
    evidence = [
        {"evidence_state": "unverified", "lineage_group": None, "source_url": "synthetic://x", "id": "1"},
        {"evidence_state": "unverified", "lineage_group": None, "source_url": "synthetic://y", "id": "2"},
    ]
    res = lineage_aware(evidence)
    assert res.effective_sources == 0
    assert "unknown relationships are not treated as independent confirmation" in res.explanation.lower()


def test_independent_sources_with_distinct_groups_remain_separate():
    evidence = [
        {"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "independent", "lineage_review_status": "adjudicated", "lineage_group": "g1", "source_url": "synthetic://a", "id": "1"},
        {"evidence_state": "supported", "verification_status": "independently_supported", "source_relationship": "independent", "lineage_review_status": "adjudicated", "lineage_group": "g2", "source_url": "synthetic://b", "id": "2"},
    ]
    assert naive(evidence).effective_sources == 2
    assert lineage_aware(evidence, dependent_group_keys={"g1", "g2"}).effective_sources == 2


def test_unsafe_url_rejected():
    try:
        from src.ingestion.url_fetcher import validate_public_url
        validate_public_url("http://localhost/test")
        assert False, "expected UnsafeURL"
    except Exception as e:
        assert e.__class__.__name__ == "UnsafeURL"


def test_automated_lineage_outputs_no_fabricated_human_labels():
    root = Path(__file__).resolve().parents[1]
    p = root / "final_completion_package" / "automated_mode" / "automated_lineage_analysis.csv"
    assert p.exists(), "automated lineage analysis must be generated"
    with open(p, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 687
    assert all(r.get("machine_verifiable_provenance_confirmed") in {"False", "false", False, "0", ""} or r.get("automated_category") != "confirmed_by_direct_machine_verifiable_provenance" for r in rows)
    # ensure no similarity-based rows marked as human-confirmed lineage
    assert all("confirmed lineage" not in (r.get("rationale") or "").lower() or "not confirmed lineage" in (r.get("rationale") or "").lower() or r.get("automated_category") != "confirmed_by_direct_machine_verifiable_provenance" for r in rows)
    # no human reviewer fields fabricated
    for r in rows:
        for k in r.keys():
            assert "reviewer" not in k.lower() or r[k] in ("", None)


def test_extended_synthetic_benchmark_is_labeled_and_separate():
    root = Path(__file__).resolve().parents[1]
    orig = root / "research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl"
    ext = root / "research-data/phase2_v1/synthetic/synthetic_benchmark_extended_v1.jsonl"
    assert orig.exists() and ext.exists()
    orig_rows = [json.loads(l) for l in open(orig, encoding="utf-8") if l.strip()]
    ext_rows = [json.loads(l) for l in open(ext, encoding="utf-8") if l.strip()]
    assert len(orig_rows) == 60
    assert all(r.get("synthetic") is True for r in ext_rows)
    assert all(r.get("annotation_status", "").endswith("not_human_reviewed") or "not_human" in r.get("annotation_status", "") for r in ext_rows)
    assert all("synthetic" in (r.get("source_type") or "") or "extended" in (r.get("source_type") or "") for r in ext_rows)
