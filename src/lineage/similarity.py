import re
from difflib import SequenceMatcher
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
    shared_job_id: bool = False
    conflicting_job_ids: bool = False

def compare(left: str, right: str, contact_left: str | None = None, contact_right: str | None = None,
            url_left: str | None = None, url_right: str | None = None,
            job_id_left: str | None = None, job_id_right: str | None = None) -> Similarity:
    a, b = normalize(left), normalize(right)
    if not a or not b:
        score = 0.0
    elif a == b:
        score = 1.0
    elif min(len(a), len(b)) < 3:
        score = float(SequenceMatcher(None, a, b).ratio())
    else:
        matrix = TfidfVectorizer(analyzer="char", ngram_range=(3, 5)).fit_transform([a, b])
        score = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    left_id = re.sub(r"[^a-z0-9]", "", (job_id_left or "").lower())
    right_id = re.sub(r"[^a-z0-9]", "", (job_id_right or "").lower())
    return Similarity(
        a == b and bool(a), score,
        bool(contact_left and contact_right and contact_left.strip().lower() == contact_right.strip().lower()),
        bool(url_left and url_right and url_left.rstrip("/").lower() == url_right.rstrip("/").lower()),
        bool(left_id and right_id and left_id == right_id),
        bool(left_id and right_id and left_id != right_id),
    )

def candidate_relationship(similarity: Similarity, threshold: float = 0.72) -> tuple[str, str]:
    # A distinct requisition ID is a hard reason not to join similar role text
    # into a copied-posting candidate. Common job descriptions are often reused.
    if similarity.conflicting_job_ids:
        return "unknown", "Distinct requisition identifiers were observed; similar descriptions are not treated as copied-posting evidence."
    if similarity.exact or similarity.score >= threshold or similarity.shared_job_id or similarity.shared_application_url:
        return "copied_derived", "Strong text or metadata overlap makes copying a candidate; source lineage remains unconfirmed without provenance or adjudication."
    if similarity.score >= 0.40:
        return "unknown", "Possible related content, but similarity is insufficient to assert copying."
    return "unknown", "No strong overlap was detected, but low similarity does not establish source independence."
