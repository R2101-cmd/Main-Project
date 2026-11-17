# TrustHire final implementation summary

**Status:** implementation complete for the safely achievable live workflow. Live authorization remains unresolved unless the repository receives verified employer-source mappings and adjudicated lineage evidence that meets the documented sufficiency policy.

## What changed

- Added a central, read-only employer authority configuration at `config/employer_sources_v1.json` and a schema. The checked-in configuration contains no trusted mappings. A mapping is usable only with an exact employer identity, verified relationship type, provenance and valid verification date. A shared ATS additionally requires a verified tenant path prefix. User-entered links cannot create authority.
- Connected the validated mappings to the Streamlit collector. Evidence preserves mapping provenance, source URL, final URL, HTTP status, retrieval time, extraction method, field-level comparisons and source relationship explanations.
- Added evidence IDs, source-family and publication/modification dates, and explicit `unknown` / `not_assessed` lineage defaults. Pairwise similarity creates candidate-only records. It never sets confirmed relationships or group IDs. The existing ordinary and lineage-aware aggregation functions were not changed.
- Split `datePosted`, `dateModified`, `validThrough` and retrieval time. Freshness uses the source’s date fields, treats expired/stale, missing, invalid and future evidence as unresolved, and applies the configured 180-day policy. This is a conservative rule, not a calibrated threshold.
- Made title, requisition ID, location, employment type, comparable salary, application route, posting date and description conflicts affect vacancy correspondence. Missing or incomparable optional fields are not contradictions. A field disagreement on an exactly identified vacancy can be recorded as a contradiction; uncertain correspondence remains unresolved.
- Strengthened final live decisions without changing A/B/C: the final decision requires at least two eligible independent source groups, authoritative source relationships and current evidence. Mixed support/contradiction remains unresolved. Fraud outcome remains `unresolved`; authorization states are never mapped to fraud or legitimacy.
- Removed the synthetic benchmark selector and reference-label code from the normal Streamlit app. The research evaluation remains a separate CLI workflow. Corrected the extracted-fields panel and made employer identity, vacancy authorization and fraud outcome distinct.
- Pinned each validated DNS answer into the HTTP/TLS socket connection, retained the original hostname for Host/SNI verification, disabled implicit environment proxies, rejected non-global DNS results, and kept redirect validation, timeout, content-type and response-size controls.

## Verification summary

- Targeted suite: 107 passed.
- Full suite: 163 passed, 7 warnings.
- Streamlit AppTest smoke: exit 0; all three intake modes rendered and the pasted-text review completed without an exception.
- Leakage-safe split validator: valid, exit 0.
- Read-only Stripe staging validator: 780/780 loaded, exit 0.
- Protected checksum comparison: 69/69 unchanged, zero mismatches. Five historical synthetic files and 3,841 raw scraper files have current-only hashes but no pre-change comparison baseline; see the integrity report.
- Historical Stage 7B evaluation files were not rerun, tuned or rewritten.

See `test_results.md`, `security_review.md`, `data_integrity_report.md`, and `remaining_limitations.md` for details.
