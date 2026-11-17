# Collection-to-live evidence mapping

This document defines the conservative boundary between collected research records and live TrustHire evidence.

| Collection value | Live `evidence_state` | Live support? |
|---|---|---|
| `independent_official_confirmation` | `snapshot_match_only` | No |
| `fresh_same_system_retrieval` | `unverified` | No |
| `supported` without explicit current authority and adjudicated lineage | `unverified` | No |
| `contradicted` without explicit current authority and adjudicated lineage | `unverified` | No |
| `unresolved` | `unresolved` | No |
| `unavailable` / `inaccessible` | `unavailable` | No |

The conversion layer preserves the original collection classification, source hashes, retrieval timestamp, source publication/modification dates, source-independence claim, and retrieval-independence claim under `details`. It never infers `source_relationship=independent` or `lineage_review_status=adjudicated`.

Promotion to live support requires explicit caller-supplied current authorization, verified authority, and an adjudicated independent lineage relationship. The shipped employer authority configuration remains empty; no employer mapping is added by this change.

Retrieval timestamps are provenance timestamps. They are not substituted for source publication or modification dates.
