from src.evaluation.metrics import classification_metrics, selective_metrics


def test_balanced_accuracy_and_false_assurance_are_explicit():
    result = classification_metrics(["supported", "unresolved"], ["supported", "supported"])
    assert result["balanced_accuracy"] == 0.5
    selective = selective_metrics(["supported", "unresolved"], ["supported", "supported"], [False, False])
    assert selective["false_assurance_count"] == 1
    assert selective["false_assurance_denominator"] == 1
    assert selective["false_assurance"] == 1.0
