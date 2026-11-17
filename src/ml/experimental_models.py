"""Leakage-safe lightweight baselines for the E2/E3 experiment ladder.

These are deliberately transparent feature-string baselines. Structured fields are
serialized as tokens and fitted only on the training partition, so they are useful
as an executable MVP while the richer annotated benchmark is being completed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectPercentile, chi2
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def _value(record: dict, *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return "unknown"


def metadata_text(record: dict) -> str:
    """Return non-free-text metadata as stable, learnable tokens."""
    fields = {
        "employer": _value(record, "employer", "employer_name", "company"),
        "location": _value(record, "location"),
        "source_type": _value(record, "source_type", "platform_type"),
        "ats": _value(record, "ats_platform"),
        "employment": _value(record, "employment_type"),
        "has_salary": "yes" if record.get("salary") or record.get("salary_text") else "no",
        "has_job_id": "yes" if record.get("job_id") or record.get("job_identifier") else "no",
        "has_application_url": "yes" if record.get("application_url") else "no",
        "evidence_count": str(len(record.get("evidence") or [])),
    }
    return " ".join(f"meta_{key}_{value}" for key, value in fields.items())


def employer_context_text(record: dict) -> str:
    evidence = record.get("evidence") or []
    context = [
        f"employer_{_value(record, 'employer', 'employer_name', 'company')}",
        f"identity_{_value(record, 'employer_identity', 'employer_identity_state')}",
        f"source_{_value(record, 'source_type', 'platform_type')}",
    ]
    for item in evidence:
        context.extend([
            f"evidence_state_{_value(item, 'evidence_state')}",
            f"verification_{_value(item, 'verification_status')}",
            f"relationship_{_value(item, 'employer_relationship', 'source_relationship')}",
            f"retrieval_{_value(item, 'retrieval_status')}",
        ])
    return " ".join(context)


def _train(texts: Iterable[str], labels: Iterable[str]) -> Pipeline:
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1)),
        # Fixed before evaluation; fit() learns scores from training rows only.
        ("feature_selection", SelectPercentile(score_func=chi2, percentile=75)),
        ("classifier", LogisticRegression(random_state=42, max_iter=1000)),
    ])
    pipeline.fit(list(texts), list(labels))
    return pipeline


@dataclass
class ExperimentalBaseline:
    name: str
    pipeline: Pipeline

    @classmethod
    def train(cls, records: list[dict], mode: str) -> "ExperimentalBaseline":
        if mode not in {"e2", "e3"}:
            raise ValueError("mode must be e2 or e3")
        texts = []
        for record in records:
            base = _value(record, "text", "job_description")
            extra = metadata_text(record) if mode == "e2" else employer_context_text(record)
            texts.append(f"{base} {extra}")
        labels = [record["authorization_label"] for record in records]
        if len(set(labels)) < 2:
            raise ValueError("training partition contains fewer than two classes")
        return cls("E2_text_plus_metadata" if mode == "e2" else "E3_employer_context", _train(texts, labels))

    def predict(self, records: list[dict]) -> list[str]:
        values = []
        for record in records:
            base = _value(record, "text", "job_description")
            extra = metadata_text(record) if self.name.startswith("E2") else employer_context_text(record)
            values.append(f"{base} {extra}")
        return [str(value) for value in self.pipeline.predict(values)]

    @property
    def selected_feature_count(self) -> int:
        """Number of features retained by the train-fitted selector."""
        return int(self.pipeline.named_steps["feature_selection"].get_support().sum())
