from src.evaluation.metrics import classification_metrics, selective_metrics


def test_multiclass_metrics_include_per_class_and_confusion_matrix():
    result = classification_metrics(["supported", "unresolved", "contradicted"], ["supported", "supported", "unresolved"])
    assert result["n"] == 3
    assert set(result["labels"]) == {"supported", "unresolved", "contradicted"}
    assert set(result["per_class"]) == set(result["labels"])
    assert len(result["confusion_matrix"]) == 3
    assert result["macro"]["f1"] >= 0
    assert result["weighted"]["f1"] >= 0


def test_empty_and_all_abstained_metrics_are_explicit():
    assert classification_metrics([], []) ["n"] == 0
    result = selective_metrics(["supported"], ["unresolved"], [True])
    assert result["coverage"] == 0
    assert result["selective_risk"] is None
