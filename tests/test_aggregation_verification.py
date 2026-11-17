from src.aggregation.rules import lineage_aware, naive


def ev(state, **extra):
    return {"evidence_state": state, **extra}


def test_snapshot_only_is_excluded_from_both_aggregators():
    items = [ev("supported", verification_status="snapshot_match_only")]
    for result in (naive(items), lineage_aware(items)):
        assert result.state == "unresolved"
        assert result.supporting_sources == 0
        assert result.contradicting_sources == 0
        assert result.effective_sources == 0


def test_unresolved_inaccessible_and_not_comparable_are_excluded():
    items = [
        ev("supported", verification_status="independently_unresolved"),
        ev("contradicted", verification_status="inaccessible"),
        ev("supported", verification_status="not_comparable"),
        ev("unavailable"),
    ]
    assert naive(items).state == "unresolved"
    assert lineage_aware(items).state == "unresolved"
    assert naive(items).effective_sources == lineage_aware(items).effective_sources == 0


def test_unknown_lineage_never_counts_as_independent_confirmation():
    items = [ev("supported", verification_status="independently_supported", source_relationship="unknown", source_url="https://a.example")]
    assert naive(items).state == "supported"  # ordinary appearance-level method
    result = lineage_aware(items)
    assert result.state == "unresolved"
    assert result.supporting_sources == result.effective_sources == 0


def test_unknown_lineage_exclusion_cannot_hide_conflicting_qualifying_evidence():
    items = [
        ev("supported", verification_status="independently_supported", source_relationship="independent", lineage_review_status="adjudicated", lineage_group="known-a"),
        ev("contradicted", verification_status="independently_contradicted", source_relationship="independent", lineage_review_status="adjudicated", lineage_group="known-b"),
        ev("supported", verification_status="independently_supported", lineage_status="unknown", lineage_group="unknown-c"),
    ]
    assert naive(items).state == "contradicted"
    result = lineage_aware(items)
    assert result.state == "contradicted"
    assert (result.supporting_sources, result.contradicting_sources) == (1, 1)


def test_all_insufficient_evidence_abstains_without_forced_decision():
    items = [ev("unverified"), ev("unavailable"), ev("supported", verification_status="snapshot_match_only")]
    assert naive(items).state == "unresolved"
    assert lineage_aware(items).state == "unresolved"


def test_ordinary_and_lineage_aware_methods_remain_distinct():
    items = [ev("supported", verification_status="independently_supported", source_relationship="copied_derived", lineage_review_status="adjudicated", lineage_status="confirmed_dependent", lineage_group="copy-set"), ev("supported", verification_status="independently_supported", source_relationship="copied_derived", lineage_review_status="adjudicated", lineage_status="confirmed_dependent", lineage_group="copy-set")]
    ordinary = naive(items)
    lineage = lineage_aware(items, dependent_group_keys={"copy-set"})
    assert ordinary.effective_sources == 2
    assert lineage.effective_sources == 1
    assert ordinary.state == lineage.state == "supported"


def test_missing_null_empty_and_unknown_lineage_all_abstain():
    items = [
        ev("supported"),
        ev("supported", source_relationship=None, lineage_status=None),
        ev("supported", source_relationship="", lineage_status=""),
        ev("supported", source_relationship="unknown"),
        ev("supported", lineage_status="unknown"),
    ]
    result = lineage_aware(items)
    assert result.state == "unresolved"
    assert result.supporting_sources == result.effective_sources == 0


def test_explicit_adjudicated_independence_is_eligible():
    item = ev("supported", verification_status="independently_supported", source_relationship="independent", lineage_review_status="adjudicated", lineage_group_id="ind-1")
    result = lineage_aware([item])
    assert result.state == "supported"
    assert result.supporting_sources == result.effective_sources == 1


def test_confirmed_dependency_counts_as_one_source_group():
    items = [
        ev("supported", verification_status="independently_supported", source_relationship="copied_derived", lineage_review_status="adjudicated", lineage_status="confirmed_dependent", lineage_group="copy-g"),
        ev("supported", verification_status="independently_supported", source_relationship="copied_derived", lineage_review_status="adjudicated", lineage_status="confirmed_dependent", lineage_group="copy-g"),
    ]
    result = lineage_aware(items, dependent_group_keys={"copy-g"})
    assert result.state == "supported"
    assert result.supporting_sources == result.effective_sources == 1


def test_missing_lineage_does_not_override_qualifying_contradiction():
    items = [
        ev("supported", verification_status="independently_supported"),
        ev("contradicted", verification_status="independently_contradicted", source_relationship="independent", lineage_review_status="adjudicated", lineage_group="ind-2"),
    ]
    result = lineage_aware(items)
    assert result.state == "contradicted"
    assert result.supporting_sources == 0
    assert result.contradicting_sources == 1


def test_independent_relationship_without_adjudication_is_not_eligible():
    items = [ev("supported", verification_status="independently_supported", source_relationship="independent", lineage_review_status="reviewed", lineage_group="g")]
    assert naive(items).state == "supported"
    result = lineage_aware(items)
    assert result.state == "unresolved"
    assert result.effective_sources == 0


def test_not_assessed_relationship_and_missing_review_are_excluded():
    items = [
        ev("supported", verification_status="independently_supported", source_relationship="not_assessed", lineage_review_status="adjudicated", lineage_group="g1"),
        ev("supported", verification_status="independently_supported", source_relationship="independent", lineage_group="g2"),
    ]
    result = lineage_aware(items)
    assert result.state == "unresolved"
    assert result.effective_sources == 0


def test_adjudicated_copies_with_incomplete_group_metadata_do_not_multiply():
    items = [
        ev("supported", verification_status="independently_supported", source_relationship="copied_derived", lineage_review_status="adjudicated", lineage_group_id="copies"),
        ev("supported", verification_status="independently_supported", source_relationship="copied_derived", lineage_review_status="adjudicated", lineage_group_id="copies"),
    ]
    result = lineage_aware(items)
    assert result.state == "supported"
    assert result.effective_sources == result.supporting_sources == 1


def test_ordinary_aggregation_excludes_missing_unknown_and_inconsistent_verification_status():
    items = [
        ev("supported"),
        ev("supported", verification_status=None),
        ev("supported", verification_status=""),
        ev("supported", verification_status="unknown"),
        ev("supported", verification_status="independently_unresolved"),
        ev("supported", verification_status="independently_contradicted"),
        ev("contradicted", verification_status="independently_supported"),
    ]
    result = naive(items)
    assert result.state == "unresolved"
    assert result.effective_sources == result.supporting_sources == result.contradicting_sources == 0


def test_ordinary_aggregation_counts_verified_appearances_without_lineage_deduplication():
    items = [
        ev("supported", verification_status="independently_supported", source_relationship="copied_derived", lineage_review_status="adjudicated", lineage_group="copy"),
        ev("supported", verification_status="independently_supported", source_relationship="copied_derived", lineage_review_status="adjudicated", lineage_group="copy"),
        ev("contradicted", verification_status="independently_contradicted", source_relationship="unknown"),
    ]
    result = naive(items)
    assert result.state == "contradicted"
    assert (result.supporting_sources, result.contradicting_sources, result.effective_sources) == (2, 1, 3)
