# Methodology Update — Phase 2: Official-Source Verification Improvement

**Date:** 2026-11-14  
**Applies to:** automated evidence collection and advertisement-to-official-vacancy verification (Phase 2 scope).  
**Constraint:** no manual human review required; no fabricated evidence or ground-truth labels.

## 1. Field-level comparison
Each retrieved vacancy source is compared against the advertised claim across: **employer identity, job title, job description, job/requisition ID, job location, application URL, posting date, and recruiter/contact details** (when available).

- **Exact matching:** identifiers (job/requisition ID) and canonicalized URLs (and exact normalized field equality where applicable).
- **Normalized similarity:** textual fields (title, description, location, employer, recruiter/contact) using normalized text similarity; date consistency checked by parsed date proximity where possible.
- **Outcomes per field:** `exact_match`, `similar_match`, `mismatch`, `conflict`, `missing_in_source`, `missing_in_advertisement`, `not_comparable/unknown`, with recorded values and explanations.
- **Correspondence rule:** vacancy correspondence requires strong identity evidence (matching job ID or application URL) or corroborated attribute agreement (e.g. title plus employer/location/substantive description consistency). **Title similarity alone does not establish authorization or sufficient correspondence.** Clear employer mismatch prevents support.

## 2. Source authority assessment
Sources are classified by employer relationship/authority:
- **Employer-owned official career page** / verified employer-related official source.
- **Verified employer-associated ATS page** (defensible employer relationship/authorized domain).
- **Unverified ATS platform** (ATS detected but relationship not verified; not employer-authoritative).
- **Third-party job portal** (not employer-authoritative).
- **Unverified recruiter page** / unverified source.
- **Reposted advertisement** context (unverified).
- **Archived or historical snapshot**.

ATS platforms are not automatically treated as employer-authoritative without a defensible employer relationship.

## 3. Verification states (preserved vocabulary)
- `independently_supported`: vacancy correspondence with sufficiently authoritative, non-snapshot independent evidence.
- `independently_contradicted`: comparable authoritative evidence conflicts with the advertised vacancy.
- `independently_unresolved`: evidence insufficient, authority/independence unestablished, or ambiguity remains.
- `inaccessible`: source unavailable/retrieval failed (not fraud).
- `not_comparable`: retrieved content lacks comparable vacancy attributes.
- `snapshot_match_only`: match in archived/frozen snapshot context; **distinct from independent authorization evidence**.

Missing, removed, or unavailable evidence is **never** automatically classified as fraudulent.

## 4. Provenance and transparency
For each retrieved item the system preserves (as available): source/submitted/final URL, source type, employer relationship and authority assessment, retrieval timestamp, HTTP status, extraction method/status, matched/contradicted/unknown fields, field comparisons, matching explanation, and verification status. Retrieval failures and inaccessible sources are recorded.

## 5. Outputs and claims
Phase 2 analysis outputs (`field_matching_results.csv`, `source_authority_analysis.csv`, `verification_summary.json`) are **descriptive automated reclassifications** of existing collected artifacts (no live re-retrieval in the analysis pass). No improved real-world accuracy is claimed without ground-truth evaluation. All outputs are versioned; original datasets and prior stage outputs remain unchanged.
