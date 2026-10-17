from dataclasses import dataclass
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

@dataclass
class TextBaseline:
    pipeline: Pipeline
    status: str = "unvalidated"

    @classmethod
    def train(cls, texts: list[str], labels: list[str], seed: int = 42) -> "TextBaseline":
        if len(texts) < 2 or len(set(labels)) < 2:
            raise ValueError("at least two examples and two classes are required")
        pipeline = Pipeline([("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1)), ("classifier", LogisticRegression(random_state=seed, max_iter=1000))])
        pipeline.fit(texts, labels)
        return cls(pipeline, "trained; validation status depends on the evaluation split")

    def predict(self, text: str) -> dict:
        label = str(self.pipeline.predict([text])[0])
        probabilities = self.pipeline.predict_proba([text])[0].tolist() if hasattr(self.pipeline, "predict_proba") else None
        return {"label": label, "probabilities": probabilities, "warning": "textual risk is not vacancy authorization"}

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
