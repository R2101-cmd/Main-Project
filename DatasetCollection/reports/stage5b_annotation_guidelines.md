# Stage 5B Annotation Guidelines

## Scope
Reviewers annotate evidence, not intuition. Stripe/Greenhouse and Naukri/ATS are separate cohorts. Missing or inaccessible evidence is not contradiction. Every non-unresolved decision requires source references and a written rationale.

## Labels
- Employer identity: `verified`, `contradicted`, `unresolved`. Verify the employer as the named organization; do not use ATS hosting alone.
- Vacancy authorization: `supported`, `contradicted`, `unresolved`. Supported requires vacancy-level evidence sufficient to connect the employer, exact/identifiable vacancy, and authorization. Employer identity alone is insufficient.
- Fraud outcome: `confirmed_legitimate`, `confirmed_fraudulent`, `unresolved`. Use only direct, adequate evidence. Missing URLs, unavailable/removed pages, incomplete descriptions, partial matches, and absent independent evidence do not establish fraud. A removed vacancy is not automatically fraudulent.

## Evidence and provenance
Record URLs or evidence IDs, retrieval dates, and relevant excerpts or fields. Keep source independence separate from retrieval independence; a fresh Greenhouse response is same-system evidence, not independent confirmation. Check response provenance, case ID, source URL, hashes, and whether evidence belongs to this case.

## Workflow
Review independently. Select unresolved when evidence is insufficient or contradictory without a reliable resolution. Submit rationale and confidence. Do not change Table B. A lead adjudicator resolves disagreements after both initial worksheets are frozen; adjudication must cite the decisive evidence and preserve both original labels.

## Pair review
Allowed decisions: `confirmed_same_vacancy`, `confirmed_repost`, `probable_copy`, `template_similarity`, `unrelated`, `unresolved`. Similarity alone never proves copy direction or reposting.

## Agreement
After both reviewers submit, report class distributions and Cohen's kappa for each nominal label when two complete, independent ratings exist; use prevalence-aware interpretation and do not calculate agreement on blank/unsubmitted rows. Analyze disagreements by evidence state and provenance, then adjudicate.
