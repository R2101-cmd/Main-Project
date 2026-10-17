# Requirements checklist

Status is based on verified implementation and tests, not on the presence of a file alone.

| Requirement | Status | Notes |
|---|---|---|
| Pasted-text and public-URL input | Implemented and tested | `app.py` and ingestion tests |
| Structured/page/text vacancy extraction | Implemented and tested | Unknown values remain null; conflicts are retained |
| Safe public retrieval | Implemented and tested | Public HTTP/HTTPS only; access controls are not bypassed |
| Poster/image OCR | Partially implemented | Optional Pillow/Tesseract path; requires local OCR engine |
| Vacancy-specific evidence | Implemented and tested | Matched fields, excerpts, timestamps and retrieval states |
| Employer-controlled versus third-party source distinction | Implemented and tested | Third-party matching pages remain unresolved for authorization |
| Separate employer, authorization and fraud dimensions | Implemented and tested | Imported fraud labels are never authorization labels |
| Inconclusive/unavailable evidence and abstention | Implemented and tested | Stored backend term `unverified` represents inconclusive evidence |
| Naive aggregation | Implemented and tested | Counts evidence appearances |
| Lineage-aware aggregation | Implemented and tested | Consolidates known dependent groups only |
| Leakage-safe import splits | Implemented and tested | Candidate repost components share split groups |
| Reviewed annotation protocol | Implemented and documented | Current pilot has a one-reviewer limitation |
| Text/evidence evaluation comparison | Implemented and tested | Current pilot is exploratory and insufficient |
| Validated research claim | Blocked by unavailable data | No sufficiently large reviewed authorization dataset exists |
| General external-source coverage | Blocked by external access | Public pages can change, block or expire |

The latest deterministic suite passes 35 tests. The four-record pilot does not support a generalization or improvement claim.
