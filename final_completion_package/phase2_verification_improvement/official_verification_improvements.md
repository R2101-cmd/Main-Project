# Official-Source Verification Improvements (Phase 2)

**Project:** Beyond Fake-Job Classification: Lineage-Aware Evidence for Vacancy Authorization Verification  
**Date:** 2026-11-14  
**Scope:** Phase 2 only (official-source verification / advertisement-to-official-vacancy matching). No lineage, aggregation, benchmark, or other phase changes implemented.

## Audit basis
Implemented improvements address relevant weaknesses from `accuracy_improvement_audit.md`, primarily **W1** (coarse field matching/limited contradiction logic) and **W2** (heuristic source authority and weak separation of snapshot vs independent verification), while preserving existing working functionality and conservative behavior.

## 1. Field-level matching improvements
**Before:** `src/evidence/collector.py` compared normalized employer, title, location, and application URL equality only; contradiction was mainly employer-match/title-different; no job/requisition ID, description similarity, posting-date, or recruiter/contact comparison.

**After (implemented):**
- **Compared attributes:** employer identity, job title, job description, job/requisition ID, location, application URL, posting date, recruiter/contact (best-effort extraction and comparison).
- **Matching methods:** exact matching for identifiers/URLs (normalized/canonicalized) and normalized similarity methods for textual fields (title/description/location/employer/contact via sequence-based similarity); date consistency checks (parsed date delta where possible).
- **Per-field outcomes:** `field_comparisons` records status (`exact_match`, `similar_match`, `mismatch`, `conflict`, `missing_in_source`, `missing_in_advertisement`, `not_comparable/unknown`), values, similarity, and notes.
- **No title-only authorization:** vacancy correspondence requires strong identity (job ID or application URL match) or title match corroborated by employer/location/substantive description consistency; title similarity alone does not establish authorization/support.
- **Contradictions:** explicit conflicts/mismatches captured (e.g. job ID/application URL conflicts, employer-title contradictions, employer mismatch preventing support) and reflected in verification/evidence states where authority permits.
- **Extraction support:** `src/ingestion/content_extractor.py` now captures `job_id`, `posting_date`, and `recruiter` (best-effort, no fabrication).

## 2. Source authority assessment improvements
**Before:** authority inferred mainly from hostname/name heuristics with limited categories.

**After (implemented):** each retrieved item assessed into explicit relationship/authority categories:
- `employer_owned_official` / employer-related official career page (authoritative when evidenced by domain/name/authorization context)
- `verified_employer_associated_ats` (authoritative only when employer association is defensible, e.g. authorized domains / verified mapping)
- `unverified_ats` (ATS detected but employer relationship not verified; **not** treated as employer-authoritative)
- `third_party_portal` (not employer-authoritative)
- `unverified_recruiter_page` / unverified source
- `reposted_advertisement` / possible unverified repost context
- `archived_or_historical_snapshot` (snapshot context)

Authority assessment and explanation are preserved in evidence details; ATS platforms are not automatically treated as employer-authoritative without a defensible relationship.

## 3. Verification states and provenance
**State vocabulary preserved/used:** `independently_supported`, `independently_contradicted`, `independently_unresolved`, `inaccessible`, `not_comparable`, `snapshot_match_only` (stored as `verification_status`; backward-compatible `evidence_state`/retrieval fields retained).

**Key distinctions:**
- **`snapshot_match_only`** remains distinct from independent authorization evidence.
- **`inaccessible`/unavailable** retrieval or missing evidence **never implies fraud**.
- Strong contradictions yield `independently_contradicted` only when source authority supports independence; otherwise unresolved/unverified as appropriate.

**Provenance preserved per retrieved item (when available):** source URL/submitted & final URL, source type, employer relationship/authority assessment, retrieval timestamp, HTTP status, extraction method/status, matched/contradicted/unknown fields (legacy and full), field comparisons, matching explanation, verification status, and retrieval failures/errors.

## 4. Versioned analysis outputs (existing collected artifacts)
Automated, conservative reclassification of existing Stage 4E collected records (`DatasetCollection/processed/stage4e_evidence_records.csv`, 780 records) produced in this Phase 2 directory without live network retrieval, fabricated evidence, or human labels:
- `field_matching_results.csv`
- `source_authority_analysis.csv`
- `verification_summary.json`

**Counts (Phase 2 reclassification):**
| Verification status | Count |
|---|---:|
| independently_supported | 0 |
| independently_contradicted | 0 |
| independently_unresolved | 0 |
| inaccessible | 17 |
| not_comparable | 0 |
| snapshot_match_only | 763 |

## 5. Before/after comparison
| Aspect | Before | After |
|---|---|---|
| Field matching | Employer/title/location/application URL equality; limited contradiction | Employer, title, description similarity, job/requisition ID, location, application URL, posting date, recruiter/contact with per-field outcomes and explanations; title alone insufficient |
| Authority | Heuristic host/name basis | Explicit relationship categories (official, verified ATS, unverified ATS, third-party, unverified recruiter/repost, archived snapshot) and authority explanation |
| Verification states | Conservative artifact mapping in prior summary reported all 780 `independently_unresolved` | Same evidence reclassified conservatively with snapshot distinction: 763 `snapshot_match_only`, 17 `inaccessible`, 0 `independently_supported/contradicted/unresolved/not_comparable` |
| Provenance | Basic evidence fields | Added/retained source URL/type/relationship, retrieval timestamp/status, extraction method, matched/contradicted/unknown fields, matching explanation, verification status |

**Interpretation:** The increase in `snapshot_match_only` reflects correct separation of snapshot/frozen-snapshot matched evidence from independent authorization (not a claim of improved ground-truth accuracy). No real-world accuracy improvement is claimed without ground-truth evaluation.

## 6. Limitations (Phase 2)
- Real-world authorization remains largely unresolved without independently verified employer relationships and non-snapshot authoritative confirmation; 0 independently supported/contradicted reflects conservative evidence/authority constraints, not validated performance.
- ATS-employer and official-domain verification depend on available/authorized mappings and observed signals; unverified relationships remain non-authoritative.
- No live network re-verification performed in this analysis pass; results are descriptive reclassifications of existing collected artifacts.
- No manual review, no fabricated evidence/labels, and no lineage/aggregation/benchmark changes in this phase.
