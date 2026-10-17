import re
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()

@dataclass(frozen=True)
class Similarity:
    exact: bool
    score: float
    shared_contact: bool
    shared_application_url: bool

def compare(left: str, right: str, contact_left: str | None = None, contact_right: str | None = None, url_left: str | None = None, url_right: str | None = None) -> Similarity:
    a, b = normalize(left), normalize(right)
    if a == b and a:
        score = 1.0
    else:
        matrix = TfidfVectorizer(analyzer="char", ngram_range=(3, 5)).fit_transform([a, b])
        score = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    return Similarity(a == b and bool(a), score, bool(contact_left and contact_right and contact_left.lower() == contact_right.lower()), bool(url_left and url_right and url_left == url_right))

def candidate_relationship(similarity: Similarity, threshold: float = 0.72) -> tuple[str, str]:
    if similarity.exact or similarity.score >= threshold or similarity.shared_contact or similarity.shared_application_url:
        return "copied_derived", "Strong text or metadata overlap; manual review is still required."
    if similarity.score >= 0.40:
        return "unknown", "Possible related content, but similarity is insufficient to assert copying."
    return "independent", "No strong overlap signal under the configured rule."
