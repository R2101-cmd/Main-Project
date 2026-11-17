# Lineage methodology v2

## Purpose

Lineage analysis prevents copied or derived advertisements from being counted as independent corroboration. It does not decide authorization by itself.

## Signals

- Exact normalized text match.
- Character TF-IDF similarity as a candidate signal.
- Shared application URL or requisition ID.
- Shared redacted contact or recruiter details.
- Redirect/final URL relationships.
- Matching employer, title, location, dates, and distinctive wording.

## Relationship states

`original`, `independent`, `copied/derived`, and `unknown`. Algorithmic candidates must not be silently promoted to reviewed relationships. Each relationship records signals, rationale, review status, and—when available—confidence.

## Current implementation

`src/lineage/similarity.py` normalizes text, calculates character TF-IDF cosine similarity, and exposes contact/application URL matches. The 0.72 threshold is a frozen pilot candidate threshold, not a validated universal threshold. Similarity alone should produce a review candidate; manual review is required before using it as a dependent group.

`src/aggregation/rules.py` consolidates only explicitly supplied dependent group keys. Unknown relationships remain separate but do not become proof of independence.

## Validation and limitations

Unit tests cover exact copies, minor edits, unrelated text, shared URLs, and uncertain similarity. A real lineage precision/recall score is not reported because the repository has no sufficiently large reviewed lineage gold standard. Threshold validation must use a separate labelled relationship set, not the final authorization test set.

## Review form

Reviewed relationships use `schemas/lineage_review_v1.schema.json`. Each record stores the case IDs, vacancy-group ID, observed signals, relationship classification, reviewer, review timestamp, rationale, confidence, and review status. A similarity score, shared URL, or shared contact is a candidate signal only; it must not be silently promoted to `copied_derived` or `independent`. When dependence cannot be established, reviewers must retain `unknown`.
