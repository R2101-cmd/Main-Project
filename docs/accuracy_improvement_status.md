# Accuracy improvement status

Updated 2026-11-16. This records engineering changes and evidence limits for the 15 requested accuracy priorities. A code path or synthetic check is not a real-world accuracy result.

## Data and evidence coverage

The source package contains 2,980 proposed records from 18 employer identities, largely across Greenhouse and Lever. A separate 198-record Naukri cohort was kept apart for compatibility review. `scripts/build_diverse_real_corpus.py` now creates `data/processed/real_world_corpus_v2.csv`, a 3,178-row descriptive union across three cohorts and 175 distinct employer IDs, while preserving cohort/source fields. Its report marks the result evaluation-ineligible: it adds source coverage, not verified labels, confirmed lineage, or cross-cohort deduplication. The existing collected records remain immutable.

The authority registry has one scoped mapping: Stripe's employer-owned `stripe.com/careers/` pages. It is supported by a public role page on Stripe's own domain, last checked 2026-11-16. No Greenhouse domain has been added as authorized based only on an ATS brand or a job-board URL. Other employer mappings require source-by-source verification.

## Changes made in this pass

- Vacancy application URL canonicalization retains stable vacancy query IDs (`gh_jid`, requisition and job ID variants) and drops tracking parameters. Distinct jobs on the same search path no longer compare as the same URL.
- Evidence support now requires an authoritative source, an extracted employer match, and a title match. Strong vacancy conflicts only become a contradiction when source authority and employer identity are established; otherwise they remain unresolved.
- Lineage similarity uses requisition identifiers as a guard: different IDs prevent similar descriptions from becoming copy candidates. Low text similarity now yields `unknown`; it no longer asserts independence. Shared generic contact details alone no longer make a copy candidate.
- Pair-level lineage output records shared/conflicting job-ID, contact, and application-URL signals for review.
- E2/E3 text-plus-metadata baselines now use a fixed chi-square feature selector fit only on training data; selected feature counts and the no-test-tuning rule are reported.
- Existing extraction preserves structured metadata, visible text, conflicts, warnings, and field provenance. Existing OCR uses preprocessing variants, orientation correction, confidence selection, raw text and diagnostics; only generated fixtures have been checked, not a representative real-poster set.

## Status against the 15 priorities

| # | Priority | Current result and remaining limit |
|---:|---|---|
| 1 | Dataset size and diversity | 3,178-row descriptive union now includes the Naukri cohort. The corpus remains source-concentrated and unlabeled; additional collection should use the existing readiness gate and evidence-before-label protocol. |
| 2 | Job-description extraction | Structured ATS/JobPosting data, visible text, labeled fallback extraction, and warnings/conflicts are supported. Extraction quality has no independently labeled field-level benchmark. |
| 3 | Poster OCR | Multi-variant preprocessing and confidence-selected Tesseract OCR are implemented. Existing fixture checks do not establish accuracy on real posters, scripts, or difficult layouts. |
| 4 | Official employer sources | Stripe's official careers path is explicitly registered. No source authority is inferred for ATS platforms or other employers without a verified mapping. |
| 5 | Vacancy-to-source matching | Matches employer, title, description, ID, location, application URL, date, contact, salary, and employment type; stable query IDs are retained. Ambiguous correspondence abstains. |
| 6 | Duplicate/copied-posting detection | Candidate signals include text, URL/contact, and job IDs. Conflicting requisition IDs block copy candidacy. Similarity only proposes review; it does not confirm copying. |
| 7 | Evidence lineage | Retrieval/evidence IDs, source URL/family, timestamps, hashes where available, lineage candidates, review status, and rationale are retained. No machine candidate is marked human-confirmed. |
| 8 | Freshness and expiry | `datePosted`, `dateModified`, and `validThrough` are separate; expired, old, invalid, or future dates block current support. The 180-day window is policy-configured, not empirically calibrated. |
| 9 | False retrieval matches | Title alone cannot support; employer/title and vacancy correspondence are checked, and query IDs survive URL normalization. Matching thresholds have not been tuned against an independent gold set. |
| 10 | Conflicting evidence | Material field conflicts are surfaced; mixed support and contradiction resolves to unresolved in the final decision policy. Missing or inaccessible evidence is not treated as fraud. |
| 11 | Feature selection and validation | E2/E3 now use train-fitted chi-square feature selection; vacancy/lineage-group split checks and test-set warnings exist. The fixed 75% selector and other thresholds are not calibrated on an independent labeled validation cohort. |
| 12 | Leakage-safe testing | Evaluation checks vacancy and evidence-lineage groups across partitions; preprocessing is fit on training data. Employer-held-out testing is not available in the small provisional real review set. |
| 13 | Reliability and independence | Authority is explicit and source-family metadata is retained. Independent source counts require adjudicated lineage; hostname difference and similarity do not prove independence. |
| 14 | Decision thresholds | Live authorization requires two qualifying adjudicated independent groups, currentness, authority, vacancy correspondence, and no material conflicts. This is a conservative policy, not a learned/calibrated threshold. |
| 15 | Independent real-world validation | Not completed: there are no independently double-reviewed, adjudicated cases in the available package. Existing provisional annotations cannot establish real-world accuracy or false-assurance rates. |

## Review and validation boundary

The generated union is safe for descriptive analysis and sampling-frame development, not model fitting or accuracy claims. A confirmatory evaluation still requires independent reviewers, a frozen sample, evidence snapshots/references, adjudicated vacancy and lineage labels, and a group-separated test set. Do not tune thresholds on the test partition. Synthetic benchmarks remain controlled implementation checks only.

The verified Stripe career page used for the scoped mapping is [Stripe's public careers application page](https://stripe.com/careers/apply/backend-engineer-developer-end-user-experience-platform/7292520).


## Follow-up collection and validation (2026-11-17)

A separate discovery cohort now records ten public postings across five employers (Razorpay, Okta, Airbnb, Microsoft, BEML), including engineering, sales, data, product, design, and public-sector recruitment. Source URLs, official career entrypoints, observation time, and source status at observation are recorded in `research-data/real_world_discovery_v1/postings_v1.csv`. It is deliberately descriptive: no labels were inferred, and it is not evaluation-eligible.

The employer-source registry now contains narrowly scoped mappings for Cloudflare, Datadog, Okta, Airbnb, Microsoft, and Razorpay, plus a BEML recruitment-document path. Razorpay's careers page links directly to the specified Greenhouse account; the other ATS hosts remain excluded unless independently linked from the employer. These are host/path authority mappings, not a claim that every listed vacancy remains open.

A ten-case, two-slot review queue is prepared in `research-data/real_world_discovery_v1/double_review_queue_v1.csv`. Two independent AI review passes produced 20 separate judgments in `research-data/real_world_discovery_v1/ai_independent_reviews_v1.jsonl`; they agree on employer identity and vacancy authorization for all ten cases. This is preliminary AI review only: the project's human review slots remain empty and human double review/adjudication is not complete. A real BEML recruitment PDF was identified, but both standard and approved network downloads failed because the connection closed unexpectedly; the project OCR engine was not run and no real-poster OCR score exists. The local OCR dependencies and Tesseract executable are installed.

Threshold calibration and final real-world evaluation remain uncompleted. They must wait for blinded human annotations, adjudication, source/lineage review, and a frozen vacancy/lineage-group-separated split. The E1-E5 final real-world evaluation status report records N=0 eligible test cases and marks accuracy, macro F1, false assurance, and coverage not estimable. No threshold was adjusted on synthetic or unreconciled data.
