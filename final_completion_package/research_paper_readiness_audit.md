# TrustHire Research-Paper Readiness Audit

**Audit date:** 2026-11-16  
**Scope:** Read-only inspection of the repository, implementation, datasets, reports, evaluation artifacts, tests, and research documentation.  
**Protection status:** No source code, datasets, annotations, labels, benchmarks, configuration, or evaluation results were modified by this audit. This report is the only new deliverable.

## A. Executive summary

TrustHire is a substantially implemented and testable research prototype for vacancy-authorization verification. It has a working Streamlit application, public retrieval and extraction, OCR support, provenance fields, conservative authority handling, evidence aggregation, lineage-aware abstention, group-aware split checks, synthetic evaluation harnesses, and automated tests.

It is **not ready to claim real-world predictive accuracy or publication-grade validation**. The proposed 2,980-record main cohort and separate 198-record Naukri cohort do not have submitted human authorization labels, adjudicated lineage decisions, or confirmed fraud outcomes. The 687 lineage candidate pairs remain unreviewed. Consequently, no defensible real-world accuracy, precision, recall, F1, false-assurance rate, or superiority claim is currently available.

The most important scientific issue is not missing software. It is missing independent ground truth and independent lineage adjudication. The controlled synthetic results are useful as implementation and policy-conformance checks, but their labels are authored from the same evidence conditions exercised by the rules; they do not estimate deployment performance.

**Overall readiness:**

| Target | Assessment |
|---|---|
| Demonstrable college prototype | **COMPLETE / suitable with limitations** |
| Student research presentation | **PARTIAL / suitable if claims are carefully qualified** |
| Peer-reviewed conference | **NOT READY** |
| Journal submission | **NOT READY** |
| Real-world accuracy claim | **NOT AVAILABLE** |

## B. Overall research-paper readiness assessment

The engineering prototype is more complete than the research validation. The core separation between employer identity, vacancy authorization, and fraud outcome is represented in the code and documentation. Unresolved and unavailable evidence are treated conservatively rather than as fraud. The live policy preserves a two-independent-source minimum and does not promote unknown lineage.

The research package still lacks a frozen, independently adjudicated real benchmark. The main integration package is explicitly `proposed_not_approved`; all 2,980 main records are collected advertisements, not 2,980 unique verified vacancies. The 198 Naukri records are kept separate and have no main-cohort ID overlap. The project therefore supports a systems/protocol paper or carefully scoped prototype presentation, but not a claim that the proposed method improves real-world verification.

## C. Research contribution and novelty assessment

### Problem and research question

The problem is clearly defined as determining whether a **specific vacancy** is authorized by the claimed employer, distinct from generic fake-job classification. The research question is measurable in principle: compare text-only, ordinary aggregation, and lineage-aware aggregation on the same vacancy groups while measuring false assurance and abstention.

### Hypotheses

H1--H3 are explicit and testable. However, they are not yet tested on defensible real-world labels. Current results establish that the implementation behaves as designed in controlled scenarios; they do not establish generalization.

### Novelty

The potentially defensible contribution is the combination of vacancy-specific authorization, evidence provenance, source dependence/lineage, freshness, authority, explicit unresolved outcomes, and abstaining policy. The repository does not yet establish that this combination is novel relative to prior work. `docs/related_work_audit.md` correctly states that no verified bibliography or defensible novelty comparison is currently present.

Do not claim “the first” system, “novel” aggregation, or superiority over fake-job classifiers until a verified literature review compares the components and their combination.

### Output separation

The three outputs are conceptually and programmatically separated:

1. Employer identity.
2. Vacancy authorization.
3. Fraud outcome.

The fraud output has no defensible human ground truth in the current project and remains unresolved in the live policy. This is a correct limitation, not a missing fraud classifier.

## D. Dataset and ground-truth assessment

### Inventory verified from project artifacts

| Cohort/artifact | Records | Current interpretation |
|---|---:|---|
| Proposed main unified cohort | 2,980 | Collection/staging package; not approved ground truth |
| Stripe/Greenhouse cohort | 780 | Preserved collection/provenance cohort; no submitted human labels |
| Stage 4F expansion | 2,200 | Greenhouse/Lever collection cohort; lineage not assessed |
| Naukri cohort | 198 | Separate cohort; not merged into the main benchmark |
| Raw imported public job-posting dataset | 17,880 | Source fraud labels only; no vacancy-authorization labels |
| Provisional authorization evaluation artifact | 145 | Evidence-derived/provisional, not independent ground truth |
| Provisional independent-review artifact | 31 | Single-reviewer/provisional; no second-reviewer agreement |
| Pilot | 4 | Feasibility pilot only |
| Lineage candidate pairs | 687 | 21 original + 459 expansion + 207 Stripe; all pending |

### Quality findings

- The unified 2,980-record package reconciles to 780 + 2,200 records and keeps the 198 Naukri records separate.
- The main cohort has 18 distinct employer IDs and is concentrated in Stripe plus a small number of expansion employers.
- Source diversity is limited to Greenhouse and Lever; third-party sources, Workday, SmartRecruiters, and Ashby are absent.
- The main package has no confirmed lineage groups; 666 records lack a lineage group ID and all 687 candidate relationships remain unreviewed.
- The collection artifact contains historical/provisional evidence classifications, including 744 `independent_official_confirmation` records, but the current live representation correctly maps these to snapshot-only/unresolved semantics unless authority and lineage are independently established.
- Reviewer worksheets exist, but submitted employer, authorization, fraud, and pair-decision counts are zero. `ground_truth_ready` is false.
- The 17,880-record imported dataset contains source `fraudulent` labels, but those labels cannot be used as vacancy-authorization ground truth.

### Leakage and splitting

The available reviewed 31-record split has 19 training records and 12 test records across 29 vacancy groups, with zero detected group leakage. The synthetic v2 split is group-separated and protected by hashes. This is a positive engineering control, but it does not solve the absence of real adjudicated labels or sparse employer-held-out evaluation.

## E. Methodology assessment

### Implemented approaches

- **E1:** TF-IDF word unigram/bigram text baseline with logistic regression, trained on the training partition.
- **E2:** Text plus serialized metadata tokens; implemented in `src/ml/experimental_models.py` and wired into `src/evaluation/runner.py`.
- **E3:** Employer-context token baseline using employer identity/context and evidence fields; implemented and wired.
- **E4:** Ordinary appearance-level evidence aggregation.
- **E5:** Lineage-aware aggregation with explicit adjudicated relationships and conservative exclusion of unknown lineage.

### Methodological strengths

- E1--E3 use training-fitted pipelines rather than fitting on the test partition.
- E4/E5 can be evaluated on the same records.
- Unknown, candidate, and unreviewed lineage are not treated as independent.
- Historical snapshots are not automatically promoted to current authorization support.
- Retrieval failure and missing evidence are not interpreted as fraud.
- The live policy adds authority, freshness, vacancy correspondence, conflict, and minimum independent-source gates.

### Important mismatches and limitations

1. The long-standing provisional report documents E2/E3 as not run, while current code now implements them. This is a historical-report mismatch that must be resolved by generating a new frozen evaluation artifact; old and new numbers must not be silently combined.
2. The current synthetic evaluation reports both raw E5 aggregation and live-policy E5. They are different outputs and must remain separately named in the paper.
3. The current 150-case synthetic suite constructs labels from evidence conditions that the policy itself checks. The perfect live-policy score is therefore policy conformance on authored inputs, not model accuracy.
4. `src/lineage/similarity.py` produces candidate relationship categories from similarity. The code comments and surrounding methodology correctly require manual review before adjudication, but the paper must explain that similarity is a candidate generator, not lineage ground truth.
5. The rule-based evidence aggregation is not calibrated probability and has no validation-derived threshold calibration.
6. Employer authority configuration currently contains zero mappings. This is safe, but it prevents real-world positive authorization decisions through the live policy.

## F. Experimental results assessment

### Current 150-case synthetic v3 implementation check

These values are **not real-world accuracy**. The benchmark contains 50 authored cases per class and its labels are synthetic design labels.

| Method | Accuracy | Macro F1 | False assurance | Coverage |
|---|---:|---:|---:|---:|
| E1 text-only | 0.367 | 0.276 | 82/100 = 0.820 | 0.907 |
| E4 ordinary aggregation | 0.800 | 0.775 | 25/100 = 0.250 | 0.867 |
| E5 lineage-aware raw | 0.867 | 0.857 | 15/100 = 0.150 | 0.800 |
| E5 lineage-aware live policy | 1.000 | 1.000 | 0/100 = 0.000 | 0.667 |

The E5 live-policy result is mechanically aligned with the authored policy conditions and should be described only as a controlled policy-conformance result. It must not be reported as operational accuracy.

### Synthetic v2 held-out test

On the 60-case synthetic v2 test partition, the reported values are:

| Method | Accuracy | 95% Wilson interval | Macro F1 | False assurance | Coverage |
|---|---:|---:|---:|---:|---:|
| E1 text-only | 0.550 | 0.425--0.669 | 0.549 | 10/40 = 0.250 | 0.700 |
| E4 ordinary aggregation | 0.867 | 0.758--0.931 | 0.861 | 8/40 = 0.200 | 0.800 |
| E5 lineage-aware aggregation | 1.000 | 0.940--1.000 | 1.000 | 0/40 = 0.000 | 0.667 |

The paired B-versus-C test is reported as McNemar p=0.0078 with eight discordant pairs, but the set is small, synthetic, and contains held-out cases from known scenario families. It is not evidence of population-level superiority.

### Real/provisional benchmark metrics

The 31-record provisional evaluation has only 12 test records, 12 supported and 19 unresolved labels overall, no contradicted records, and circularity risk because the evidence and labels are not independent. It is unsuitable for a real-world performance claim. The historical provisional report gives E1 accuracy 0.500 and E4/E5 accuracy 0.833, but these must be labeled exploratory and not compared with the synthetic results or treated as confirmatory.

### Missing evaluation elements

- No defensible real-world accuracy or confidence interval.
- No affirmative, independently adjudicated contradiction class in the reviewed real benchmark.
- No independent fraud-outcome benchmark.
- No multi-reviewer agreement or adjudication statistics.
- No reliable employer-held-out real evaluation.
- No completed validation-based freshness or aggregation calibration.
- No trustworthy estimate of performance on unique vacancies rather than collected advertisements.
- No independently established case-level E4/E5 superiority on real cases.

## G. Real-world validation gaps

The Stripe/Greenhouse investigation and correction are useful evidence of engineering integrity. Structured Greenhouse JSON extraction now populates job ID, title, employer, location, description, posting/modification dates, and application URL. Collection-to-live mapping is explicit and conservative. The final case remains unresolved because the shipped authority configuration is empty, lineage is unadjudicated, and the two-source policy is preserved. This is the intended safety behavior.

The same pattern may affect many of the 780 Stripe/Greenhouse records and any collected ATS record: a matching official snapshot is not equivalent to independently authorized current evidence. Before real validation, authority relationships and lineage pairs must be reviewed and frozen. No verified employer-domain or ATS mappings should be added without external documentation.

## H. Prototype and reproducibility assessment

### Complete or substantially complete

- Streamlit application with pasted text, public URL, and poster OCR intake.
- OCR dependency checks, preprocessing, extraction warnings, and editable/correctable workflow.
- Vacancy field extraction and evidence display with unresolved/unavailable handling.
- Explicit evidence representation conversion layer.
- Greenhouse structured JSON normalization.
- Authority configuration schema and conservative empty default.
- Ordinary and lineage-aware aggregation.
- Decision policy with minimum two independent sources and abstention.
- E1--E3 executable baseline implementations and E4/E5 production paths.
- Group-aware split validation and protected benchmark manifests.
- Extensive automated test suite.
- Reproducibility documentation and versioned artifacts.

### Incomplete or requiring verification

- Full real-data integration into a frozen, approved adjudication benchmark.
- Human annotation and adjudication workflow completion.
- Review of all 687 lineage candidate pairs.
- Verified authority mappings with documented provenance.
- Real-world E1--E5 comparison on identical adjudicated groups.
- Independent validation of freshness and aggregation thresholds.
- Full literature review with verified references.
- Paper-ready diagrams, equations, algorithm descriptions, and final result tables.
- Security/deployment review beyond the current prototype-level controls.

## I. Paper section-by-section readiness checklist

| Section | Status | Evidence and required work |
|---|---|---|
| Abstract | Partially ready | Scope is clear; final claims/results must wait for adjudicated evaluation. |
| Introduction | Partially ready | Motivation exists; add verified problem importance and bounded claims. |
| Related work | Missing | `docs/related_work_audit.md` has no verified bibliography. Search and verify literature. |
| Research gap | Partially ready | Plausible but not established against literature. |
| Problem formulation | Ready with minor revision | Separate targets and unresolved state are specified. |
| Proposed methodology | Partially ready | Add formal notation, algorithm, gate definitions, and data flow. |
| System architecture | Partially ready | Implementation exists; add one accurate architecture figure. |
| Implementation | Ready with verification | Code and tests are present; freeze commit/version and environment. |
| Dataset description | Partially ready | Inventory is strong; ground truth, sampling, uniqueness, licensing, and bias remain incomplete. |
| Experimental setup | Partially ready | Synthetic setup is documented; real adjudicated setup is missing. |
| Results and discussion | Not ready | Current real metrics are unavailable; synthetic results need strict limitation labels. |
| Limitations/threats | Ready with revision | Strong limitations exist; expand external validity, source drift, and authority coverage. |
| Conclusion/future work | Partially ready | Safe conclusion can discuss prototype and protocol, not effectiveness. |
| References | Missing | Build from verified publisher/DOI sources; do not use invented citations. |

## J. Missing items ranked by priority

### Critical

1. Obtain two independent annotations for a frozen real sample and adjudicate disagreements.
2. Complete and freeze the vacancy-authorization ground truth, including affirmative contradiction cases.
3. Review and adjudicate all relevant lineage candidates, or explicitly define a defensible sampled subset.
4. Freeze group-aware train/validation/test partitions after annotation and lineage review.
5. Re-run E1--E5 on the same real eligible test groups with a frozen implementation and report confidence intervals, confusion matrices, coverage, abstention, and false assurance.
6. Do not claim real-world accuracy or method superiority until items 1--5 are complete.

### High

7. Establish documented employer-domain and ATS authority mappings through external verification.
8. Reconcile historical reports with the current E2/E3 implementation and preserve separate versioned results.
9. Validate freshness and aggregation thresholds on validation data without tuning against the final test set.
10. Add employer-held-out evaluation if the reviewed sample permits it.
11. Complete a verified literature review across fake-job detection, information extraction, entity resolution, provenance, lineage, independent evidence, abstention, and open-world verification.

### Medium

12. Add paper-ready formal equations, algorithm pseudocode, and a single accurate architecture diagram.
13. Report sampling bias, employer concentration, source coverage, and unique-vacancy versus advertisement counts prominently.
14. Add case-level real error analysis after adjudication.
15. Freeze environment/package versions and provide a clean reproduction command sequence.

### Low

16. Improve presentation formatting and consolidate historical reports after the scientific artifacts are frozen.
17. Add optional qualitative examples of unresolved and copied-source cases with provenance-safe redaction.

## K. Exact recommended next steps

1. Freeze the current code and all protected inputs under a new version identifier.
2. Define the annotation sampling frame and reviewer-blinding procedure.
3. Independently annotate a representative, stratified sample of unique vacancy groups.
4. Adjudicate authorization, employer identity, fraud outcome, and lineage disagreements separately.
5. Add only authority mappings with documented provenance and verification dates.
6. Freeze group-aware partitions and validation-only calibration settings.
7. Execute E1--E5 on identical eligible real test groups.
8. Produce metrics and confidence intervals with missing-class warnings; report coverage and false assurance alongside accuracy.
9. Perform paired E4/E5 case analysis and qualitative error analysis.
10. Write the paper using only claims supported by the resulting frozen artifacts.

## L. Claims that are safe to make

- TrustHire is a working research prototype for vacancy-authorization verification.
- Employer identity, vacancy authorization, and fraud outcome are modeled as separate outputs.
- The system preserves provenance and source lineage metadata and treats unknown lineage conservatively.
- Missing or inaccessible evidence is unresolved/unavailable rather than fraud.
- The application supports pasted text, public URLs, and poster OCR with correction workflow.
- E1--E5 paths and evaluation tooling are implemented, subject to benchmark availability.
- Synthetic controlled tests demonstrate expected behavior under authored evidence scenarios.
- The current project provides a reproducible framework and identifies the data needed for valid real-world evaluation.

## M. Claims that must not be made

- Do not claim a real-world accuracy, precision, recall, F1, or false-assurance rate for the 2,980-record cohort.
- Do not claim the 2,980 records are 2,980 unique verified vacancies.
- Do not claim the source fraud labels are vacancy-authorization ground truth.
- Do not claim the 1.000 synthetic E5 live-policy accuracy is operational accuracy.
- Do not claim lineage-aware aggregation improves real-world performance from synthetic results or provisional circular labels.
- Do not claim the 687 candidate pairs are confirmed copied relationships.
- Do not claim employer or ATS authority merely from hostname resemblance or a matching snapshot.
- Do not claim the current system detects fraud generally.
- Do not claim novelty or “first” status without a verified literature comparison.
- Do not claim publication readiness while labels, lineage decisions, and independent evaluation remain incomplete.

## N. Final recommendation

### College paper presentation: READY WITH QUALIFICATIONS

The project is demonstrably implemented and testable. Present it as a prototype and methodology contribution. Show the unresolved safety behavior and clearly label synthetic metrics as controlled implementation checks.

### Student research conference: PARTIAL / POSSIBLE AFTER CLAIMS ARE NARROWED

A systems/prototype paper may be viable if it emphasizes architecture, provenance, abstention, and reproducibility, while openly stating that real-world validation is pending. A performance-improvement paper is not yet supported.

### Peer-reviewed conference: NOT READY

The absence of independently adjudicated real ground truth, lineage decisions, multi-reviewer agreement, and a frozen real E1--E5 test set prevents a defensible empirical claim.

### Journal submission: NOT READY

The same issues apply, with additional requirements for verified literature, stronger statistical analysis, dataset documentation, and external validity.

## Verification and integrity result

- Full automated test suite: **175 passed, 7 warnings**.
- Python compilation: **passed**.
- Protected hashes checked: **6 protected files unchanged** (three annotation artifacts and three synthetic split files).
- Existing project datasets, labels, annotations, benchmarks, configuration, and evaluation outputs were not modified by this audit.
- This audit created only `final_completion_package/research_paper_readiness_audit.md`.

