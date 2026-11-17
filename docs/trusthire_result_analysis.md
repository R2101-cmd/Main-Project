# 4. Result Analysis and Discussion

## 4.1 Experimental Setup

TrustHire was evaluated as a lineage-aware vacancy-authorization verification prototype. Five approaches were defined. E1 is a text-only baseline using the advertisement text. E2 combines text with serialized vacancy metadata. E3 adds employer-context features. E4 performs ordinary evidence aggregation, treating retrieved evidence items as appearance-level support. E5 performs lineage-aware aggregation: it distinguishes independent evidence from copied or derived evidence, tracks unknown relationships, applies freshness and authority checks, and can abstain when the evidence does not justify a supported or contradicted decision.

The available results come from separate experimental settings. Synthetic benchmark v2 contains 60 authored cases, balanced across contradicted, unresolved, and supported outcomes. Synthetic benchmark v3 contains 150 authored cases, with 50 cases in each of those three classes and additional duplicate, copied, unavailable, stale, and contradictory-evidence scenarios. These labels are controlled design labels and are useful for implementation checks, but they are not independently reviewed real-world ground truth. The collected real-world material consists of a 2,980-record main corpus, a separate 198-record Naukri cohort, a descriptive union of 3,178 records, and a later discovery cohort of ten public postings. The real-world records have not produced an eligible adjudicated test set.

All reported metrics are therefore benchmark-specific. Results from v2, v3, and the provisional real-world artifact are not pooled into a single accuracy estimate.

## 4.2 Dataset Analysis

The main research corpus contains 2,980 proposed advertisements from 18 employer identities and is concentrated in Greenhouse- and Lever-like source families. The 198-record Naukri cohort was retained separately because its source and field structure differ from the main corpus. A descriptive integration step produced a 3,178-record union while preserving cohort and source fields. This union expands the sampling frame, but it does not establish that each record is a genuine vacancy, that records are deduplicated across cohorts, or that labels are independently correct. It is therefore unsuitable as a supervised evaluation set.

Synthetic v2 provides a balanced 60-case implementation benchmark. Synthetic v3 broadens the scenario space to 150 cases and is the more demanding controlled benchmark because it includes copied evidence, conflicting requisition information, unavailable sources, and unresolved lineage. The two benchmarks are intentionally reported separately because their scenario compositions and generated labels differ.

The real-world discovery cohort contains ten postings from five employers: Razorpay, Okta, Airbnb, Microsoft, and BEML. It includes engineering, data, product, design, sales, and public-sector recruitment examples across several locations and source types. Two AI review passes produced 20 provisional judgments and agreed on employer identity and vacancy-authorization labels for all ten cases. Those judgments are explicitly AI-only; the 20 human review slots remain unfilled. Consequently, the discovery cohort is a sampling and workflow artifact, not ground truth.

## 4.3 Comparative Performance Analysis

### Synthetic benchmark v2

| Method | n | Accuracy | Macro F1 | False assurance | Coverage | Selective accuracy |
|---|---:|---:|---:|---:|---:|---:|
| E1 text-only | 60 | 55.00% | 54.9% | 25.0% (10/40) | 70.0% | 54.8% |
| E4 ordinary aggregation | 60 | 86.67% | 86.1% | 20.0% (8/40) | 80.0% | 83.3% |
| E5 lineage-aware aggregation | 60 | 100.00% | 100.0% | 0.0% (0/40) | 66.7% | 100.0% |

On v2, E4 improves substantially over E1, while E5 removes the observed false-assurance cases at the cost of lower decision coverage. This pattern is consistent with the intended role of lineage and conservative abstention, but the labels were authored for the benchmark and cannot support a deployment claim.

### Synthetic benchmark v3

| Method | n | Accuracy | Macro F1 | False assurance | Coverage | Selective accuracy |
|---|---:|---:|---:|---:|---:|---:|
| E1 text-only | 150 | 36.67% | 27.6% | 82.0% (82/100) | 90.7% | 35.3% |
| E4 ordinary aggregation | 150 | 80.00% | 77.5% | 25.0% (25/100) | 86.7% | 76.9% |
| E5 lineage-aware raw | 150 | 86.67% | 85.7% | 15.0% (15/100) | 80.0% | 83.3% |
| E5 lineage-aware live policy | 150 | 100.00% | 100.0% | 0.0% (0/100) | 66.7% | 100.0% |

The v3 results show the same directional ordering but make the trade-off clearer. E5 raw improves accuracy by 6.67 percentage points over E4 and reduces false assurance by ten percentage points, while coverage falls by 6.67 points. The live-policy E5 result is a mechanical policy-conformance result: the authored labels were constructed around the policy conditions. It is not independent predictive validation and must not be interpreted as real-world accuracy.

E2 and E3 are implemented in the current evaluation stack. In the available provisional 16-case artifact, E2 and E3 each report 93.75% accuracy and 0.323 macro F1, but that artifact contains 15 unresolved and one supported case, no contradicted case, and evidence-derived labels. The metrics are therefore reported for transparency only and are not comparable confirmation of E1--E5 performance.

### Provisional real-world artifact

| Method | n | Accuracy | Macro F1 | False assurance | Coverage | Selective accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Text-only, E2, E3, E4, or E5 artifact summaries | 16 | 93.75% | 0.323 | 0/15 where defined | 0.0% | Not estimable |

This table is not a real-world performance result. The labels are evidence-derived, the contradicted class is absent, and every recorded prediction is unresolved for the coverage calculation. It cannot establish that any approach is accurate in deployment.

### Eligible real-world E1--E5 evaluation

| Measure | E1 | E2 | E3 | E4 | E5 |
|---|---:|---:|---:|---:|---:|
| Eligible test cases | 0 | 0 | 0 | 0 | 0 |
| Accuracy | Not estimable | Not estimable | Not estimable | Not estimable | Not estimable |
| Macro F1 | Not estimable | Not estimable | Not estimable | Not estimable | Not estimable |
| False assurance | Not estimable | Not estimable | Not estimable | Not estimable | Not estimable |
| Coverage | Not estimable | Not estimable | Not estimable | Not estimable | Not estimable |

The zero count is a data-readiness result, not a zero-performance result. A valid comparison requires the same independently reviewed vacancy and lineage groups, a frozen group-separated split, and labels that were not derived from the evaluated system's evidence.

## 4.4 Lineage-Aware Evidence Analysis

Ordinary aggregation can over-count repeated evidence. If several job-board pages reproduce the same employer notice, their agreement is not equivalent to several independent confirmations. E5 assigns evidence to lineage groups and gives copied or derived records less evidential independence. Direct requisition identifiers act as important guards: conflicting identifiers prevent similar text from being treated as a copy candidate, while low similarity or insufficient metadata remains unknown rather than being asserted independent.

Unknown lineage is handled conservatively. It is neither automatically independent nor automatically copied. This matters when a source is inaccessible, when only a generic contact detail is shared, or when a repost lacks enough information to establish its origin. The system records candidate relationships and review status instead of converting similarity into a definitive fraud label.

The synthetic results demonstrate the practical effect. In v3, E4 has 25 false-assurance cases, E5 raw has 15, and E5 live policy has none on the authored scenarios. E5 also abstains more often: its raw coverage is 80.0%, compared with 86.7% for E4, and its live-policy coverage is 66.7%. The improvement is therefore attributable to evidence quality and independence controls together with conservative abstention, rather than to text similarity alone.

Freshness is represented separately from lineage. `datePosted`, `dateModified`, and `validThrough` are not collapsed into one date; expired, future, or otherwise stale evidence cannot silently support a current vacancy. Missing evidence and contradictory evidence are also distinct states. A closed posting may show that a historical vacancy existed without proving that the original advertisement was fraudulent.

## 4.5 False Assurance and Coverage Analysis

False assurance is especially consequential in this task because the harmful error is a confident supported or legitimate conclusion when the evidence does not justify it. The synthetic v3 false-assurance rate falls from 82.0% for E1 to 25.0% for E4 and 15.0% for raw E5. The live-policy E5 path records 0/100 on the authored non-supported cases, but this result is policy-conformance on constructed data.

The reductions are accompanied by lower coverage. E1 covers 90.7% of v3 cases, E4 covers 86.7%, raw E5 covers 80.0%, and live-policy E5 covers 66.7%. In an authorization setting, an unresolved decision is a valid safety outcome: it indicates that the available sources do not meet the evidence standard and should trigger additional review or evidence collection. Treating every abstention as a failure would reward unsupported certainty and obscure the main operational risk.

Selective accuracy further separates correctness on decided cases from willingness to decide. E5's 83.3% raw selective accuracy and 100% live-policy selective accuracy are conditional on covered cases in the synthetic benchmark; they do not describe all cases and do not replace full accuracy or false-assurance reporting.

## 4.6 Prototype and OCR Evaluation

TrustHire supports three input routes: pasted advertisement text, a public URL, and a poster upload. The text and URL workflows preserve extracted fields, retrieval status, source authority, matched fields, contradictions, timestamps, and unresolved explanations. Inaccessible or empty evidence is recorded as unavailable rather than treated as fraud.

The poster pipeline now performs EXIF-aware loading, grayscale conversion, upscaling, denoising, contrast enhancement, adaptive and Otsu thresholding, conservative deskewing, orientation detection, multiple Tesseract page segmentation modes, and confidence-based attempt selection. OCR text remains editable before it is submitted to the verification workflow.

The controlled OCR harness evaluated five generated fixtures: clear, low-resolution/noisy, coloured-background, multi-column, and rotated posters. All recovered the five expected tokens, with selected confidence values between 95.40 and 95.60. These are controlled fixture checks, not estimates of field accuracy. No real poster was available to the repository harness. The official BEML PDF could not be downloaded in the restricted environment, so no real-poster OCR result, character error rate, or error inventory is claimed.

## 4.7 Real-World Evaluation Limitations

The 3,178-record descriptive corpus is not independently labelled ground truth. The ten-posting discovery cohort has two AI review passes, with complete categorical agreement, but AI review is not independent human annotation. The 20 human review slots remain unfilled and no human adjudication has been recorded. Accordingly, there are currently zero eligible real-world test cases for final E1--E5 evaluation.

The following real-world quantities are therefore not estimable: accuracy, macro F1, false assurance, coverage, and calibrated decision thresholds. Additional limitations include source concentration, uncertain vacancy currentness for some records, absent evidence snapshots for the discovery cohort, unresolved lineage relationships, and the inability to retrieve the BEML binary poster asset. The provisional artifact is also severely class-imbalanced and circular because evidence-derived labels overlap with evidence used by the methods.

## 4.8 Discussion

The central contribution of TrustHire is a verification model in which evidence quality, source authority, freshness, and lineage determine whether a vacancy claim can be supported. This moves the task beyond classifying advertisement text as “fake” or “real.” A text-only model can recognize plausible language while missing that several apparently separate pages are copied, that a requisition identifier conflicts, or that an official source is stale. E5 makes those relationships explicit and can abstain when the available evidence is insufficient.

The controlled experiments support this design rationale. Across both synthetic benchmarks, ordinary evidence aggregation performs better than the text-only baseline, and lineage-aware aggregation further reduces false assurance. The cost is reduced coverage, which is appropriate for a system whose primary safety objective is to avoid unsupported assurance. The result is best understood as evidence that the implemented mechanisms behave as intended under controlled scenarios, not as proof of generalization.

The prototype also makes uncertainty inspectable. It preserves evidence identifiers, source families, retrieval timestamps, matching fields, contradiction details, lineage candidates, and review status. This supports human follow-up and auditability. The design is strongest when official employer sources and vacancy-specific identifiers are available. It is weaker when pages are inaccessible, source relationships are unknown, dates are missing, or OCR must interpret multilingual or highly stylized posters.

The main empirical limitation is the absence of independently adjudicated real-world labels. Until two human reviewers assess a frozen sample, disagreements are adjudicated, lineage groups are confirmed, and a group-separated test set is held out, threshold tuning would risk circularity. Future work should therefore prioritize evidence snapshots, diverse real posters, human review operations, and a preregistered calibration and evaluation split before making deployment-level claims.

## 4.9 Summary

TrustHire's synthetic evaluations indicate that lineage-aware evidence aggregation can improve controlled vacancy-authorization decisions and reduce false assurance relative to text-only and ordinary aggregation baselines. In v3, raw E5 reaches 86.67% accuracy and 85.7% macro F1 with 15.0% false assurance and 80.0% coverage, compared with 80.0%, 77.5%, 25.0%, and 86.7% for E4. The live-policy E5 result reaches 100% on the authored benchmark while covering 66.7%; it is a policy-conformance result, not independent validation.

The real-world evidence currently supports implementation and workflow claims only. The collected corpora and ten-case discovery cohort expand coverage and expose review requirements, but no human-adjudicated test set exists. Real-world accuracy, macro F1, false assurance, coverage, and calibrated thresholds therefore remain open research questions. The principal contribution is a conservative, lineage-aware evidence framework that makes uncertainty and dependence visible rather than converting incomplete evidence into false confidence.
