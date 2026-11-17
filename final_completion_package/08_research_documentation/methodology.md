# Research methodology (as executed/available)

## Problem
Determine whether a specific job vacancy is authorized by the claimed employer, distinct from employer identity and text-only fraud cues. Central contribution: **lineage-aware evidence aggregation** with provenance, authority, independence, freshness, contradiction, sufficiency, and abstention.

## Design principles
- Independent decisions: employer identity (`verified|contradicted|unresolved`), vacancy authorization (`supported|contradicted|unresolved`), fraud outcome (`confirmed_legitimate|confirmed_fraudulent|unresolved`).
- Evidence states: `supported|contradicted|unverified|unavailable`; missing/inaccessible evidence ≠ fraud.
- Source lineage: candidate relationships require signals and human confirmation; dependent/copied sources must not inflate independent corroboration.

## Implemented approaches (codebase)
- **A. Text-only baseline:** TF-IDF + logistic regression on advertisement text/derived fields (no external authorization/lineage features) where applicable.
- **B. Ordinary aggregation:** combines evidence observations/statuses without dependence correction.
- **C. Lineage-aware aggregation:** consolidates only explicitly supplied dependent groups; preserves unknown relationships; supports abstention/unresolved when evidence insufficient.

## Automated validation mode execution
- **No manual review dependency:** automated pipeline runs without case-by-case human adjudication; historical human-review artifacts preserved as research records (not deleted/modified, no fabricated labels).
- **Automated official-source verification:** permitted public-source retrieval/comparison implemented (`src/ingestion/url_fetcher.py`, `src/evidence/collector.py`); artifact-based conservative state mapping produced for collected records (states: `independently_supported|independently_contradicted|independently_unresolved|inaccessible|not_comparable|snapshot_match_only`). Missing/inaccessible evidence is not fraud.
- **Automated lineage detection:** all 687 candidates processed with machine-comparable signals/similarity scoring into `confirmed_by_direct_machine_verifiable_provenance` (if evidenced), `likely_dependent`, `possible_dependency`, `unknown_relationship`. Similarity is not confirmation; unknown not assumed independent; independence estimated conservatively.
- **Three-way evaluation:** A text-only, B ordinary aggregation, C lineage-aware aggregation on identical cases/rules. Original synthetic benchmark preserved; extended synthetic benchmark (separately versioned, labeled synthetic, not human-reviewed) added for dependence/copy/contradiction/unavailable scenarios.
- **Real-world analysis:** descriptive system outputs only (retrieval/match/availability/snapshot-only/unresolved/contradiction/duplicate/candidate-lineage/independence estimates/decision-abstention distributions); **no ground-truth accuracy/precision/recall/F1/false-assurance claims**.

## Safeguards
- No overwrites of original datasets/annotations/evidence; versioned outputs in `final_completion_package/`; checksums recorded for protected files; no fabricated evidence, labels, URLs, or results.
