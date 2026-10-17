from collections import Counter
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score


def classification_metrics(actual: list[str], predicted: list[str], positive: str = "supported", known_labels: list[str] | None = None) -> dict:
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted must have the same length")
    n = len(actual)
    if not n:
        return {"n": 0, "labels": [], "per_class": {}, "macro": {}, "weighted": {}, "confusion_matrix": []}
    labels = sorted(set(known_labels or []) | set(actual) | set(predicted))
    tp = sum(a == positive and p == positive for a, p in zip(actual, predicted))
    fp = sum(a != positive and p == positive for a, p in zip(actual, predicted))
    fn = sum(a == positive and p != positive for a, p in zip(actual, predicted))
    tn = sum(a != positive and p != positive for a, p in zip(actual, predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    per_class = {}
    for label in labels:
        per_class[label] = {"precision": precision_score(actual, predicted, labels=[label], average="macro", zero_division=0), "recall": recall_score(actual, predicted, labels=[label], average="macro", zero_division=0), "f1": f1_score(actual, predicted, labels=[label], average="macro", zero_division=0), "support": sum(value == label for value in actual)}
    return {"n": n, "accuracy": accuracy_score(actual, predicted), "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "labels": labels, "per_class": per_class, "macro": {"precision": precision_score(actual, predicted, labels=labels, average="macro", zero_division=0), "recall": recall_score(actual, predicted, labels=labels, average="macro", zero_division=0), "f1": f1_score(actual, predicted, labels=labels, average="macro", zero_division=0)}, "weighted": {"precision": precision_score(actual, predicted, labels=labels, average="weighted", zero_division=0), "recall": recall_score(actual, predicted, labels=labels, average="weighted", zero_division=0), "f1": f1_score(actual, predicted, labels=labels, average="weighted", zero_division=0)}, "confusion_matrix": confusion_matrix(actual, predicted, labels=labels).tolist(), "label_counts": dict(Counter(actual)), "missing_from_evaluation": [label for label in labels if label not in actual]}


def selective_metrics(actual: list[str], predicted: list[str], abstained: list[bool], positive: str = "supported") -> dict:
    if not (len(actual) == len(predicted) == len(abstained)):
        raise ValueError("selective metric inputs must have the same length")
    assessed = [(a, p) for a, p, abstain in zip(actual, predicted, abstained) if not abstain]
    assessed_correct = sum(a == p for a, p in assessed)
    return {"n": len(actual), "assessed": len(assessed), "coverage": len(assessed) / len(actual) if actual else 0.0, "abstention_rate": 1 - (len(assessed) / len(actual)) if actual else 0.0, "selective_risk": 1 - (assessed_correct / len(assessed)) if assessed else None, "false_assurance": sum(a != positive and p == positive for a, p in assessed) / len(assessed) if assessed else None}
