# Dataset compatibility review

## Cohorts

| Cohort | Records | Integration status |
|---|---:|---|
| Stripe/Greenhouse | 780 | Suitable for staging as a separate cohort |
| Stage 4F expansion | 2,200 | Suitable for staging with provenance warnings |
| Naukri/ATS | 198 | Must remain separate; not in the proposed unified main dataset |

The proposed main CSV contains 2,980 records. The final package validation report had no structural errors, but it recorded unresolved warnings for missing human ground truth, incomplete source-family diversity, and missing application integration tests.

## Compatibility findings

- Stable IDs can be preserved as `case_id`; the application must maintain an internal database ID separately.
- Existing text fields map reasonably to title, description, and location.
- Existing evidence records are observation-oriented and use `unverified`; the proposed package needs an explicit mapping to unresolved/unavailable without collapsing distinctions.
- Existing SQLite evidence has no response-hash, source-family, retrieval-event, or source-independence columns.
- Existing lineage storage can represent a reviewed pair but not the full candidate-versus-confirmed workflow or cohort-scoped lineage groups.
- Existing annotations are generic dimension/label rows, while the proposed package has three explicitly separate claims.
- Existing application data is case-by-case; importing 2,980 records would need a batch importer and an explicit cohort filter.

## Duplicate and leakage risks

Different URLs must not be treated as independent. Source families and source instances must be retained. Candidate similarity must not become a confirmed repost. Group-aware partitions are required before any model evaluation; the existing evaluation runner rejects missing labels and cross-partition lineage groups, but it expects JSONL evaluation records rather than this CSV.
