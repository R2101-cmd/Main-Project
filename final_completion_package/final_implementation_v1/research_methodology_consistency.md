# Research methodology consistency and result interpretation

## Research objective preserved

The research question remains whether lineage-aware evidence aggregation improves vacancy-authorization assessment over a text-only baseline and ordinary appearance-level aggregation, especially with copied, reposted, incomplete or contradictory evidence.

- **A:** the existing TF-IDF word-unigram/bigram Logistic Regression baseline remains unchanged.
- **B:** the existing production `naive()` appearance-level aggregation remains unchanged.
- **C:** the existing production `lineage_aware()` adjudication-aware deduplication remains unchanged.

The live decision policy is an additional conservative presentation/operational gate; it is not substituted for B or C and was not applied retrospectively to the frozen Stage 7B metrics. Fraud, employer identity and vacancy authorization remain separate.

## Historical Stage 7B results (earlier frozen implementation)

The existing synthetic test split contained 60 cases: 20 Supported, 20 Contradicted and 20 Unresolved. It included the same 15 scenario families present in train and validation, so it does not test unseen-scenario generalization. These results are retained as historical synthetic results, not as performance of the current live policy.

| Approach | Accuracy (95% Wilson CI) | Macro precision | Macro recall | Macro F1 | False assurance | Unresolved prediction rate | Coverage | Covered-case accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A Text-only | 55.00% (42.49–66.91%) | 0.5503 | 0.5500 | 0.5494 | 10/40 = 25.00% | 30.00% | 70.00% | 54.76% |
| B Ordinary aggregation | 86.67% (75.83–93.09%) | 0.9048 | 0.8667 | 0.8611 | 8/40 = 20.00% | 20.00% | 80.00% | 83.33% |
| C Lineage-aware aggregation | 100.00% (93.98–100.00%) | 1.0000 | 1.0000 | 1.0000 | 0/40 = 0.00% | 33.33% | 66.67% | 100.00% |

### Historical per-class test results

| Approach | Class | Precision | Recall | F1 | Support |
|---|---|---:|---:|---:|---:|
| A | Contradicted | 0.5714 | 0.6000 | 0.5854 | 20 |
| A | Supported | 0.5238 | 0.5500 | 0.5366 | 20 |
| A | Unresolved | 0.5556 | 0.5000 | 0.5263 | 20 |
| B | Contradicted | 1.0000 | 1.0000 | 1.0000 | 20 |
| B | Supported | 0.7143 | 1.0000 | 0.8333 | 20 |
| B | Unresolved | 1.0000 | 0.6000 | 0.7500 | 20 |
| C | Contradicted | 1.0000 | 1.0000 | 1.0000 | 20 |
| C | Supported | 1.0000 | 1.0000 | 1.0000 | 20 |
| C | Unresolved | 1.0000 | 1.0000 | 1.0000 | 20 |

False assurance denominator is the 40 test records whose expected class was Supported or Unresolved; a false assurance is a Supported prediction on a non-Supported record. Coverage is the fraction predicted Supported or Contradicted. Unresolved predictions count as uncovered for coverage and remain included in overall accuracy.

On this constructed test split, C exceeded B by 13.33 percentage points accuracy and 0.1389 macro-F1; coverage was 13.33 points lower. The paired test reported 8 B-wrong/C-correct cases and 0 B-correct/C-wrong cases (exact McNemar p=0.0078125; paired bootstrap C-minus-B accuracy 95% CI 0.05–0.2333). These results support only the behavior of this authored synthetic split and previous implementation. The scenarios intentionally encode lineage and do not establish that real source authority or lineage can be identified equally well.

Full per-class metrics and confusion matrices remain in the preserved `final_completion_package/synthetic_evaluation_v2/metrics_summary.json` and `confusion_matrices.json`. No Stage 7B metrics were recalculated or modified here.

## Real cohort: descriptive only

The existing real descriptive package reports 2,980 main advertisements: 780 Stripe and 2,200 Stage 4F; the unified file is the exact union, with no overlap or duplicate case IDs. The separate Naukri cohort has 198 advertisements and no overlap with the main cohort. Main records have 18 employer IDs, no missing job title/location/canonical vacancy ID, and 2,980 missing lineage group IDs. The Naukri set has 157 employer IDs and no missing job title/location. Main source-family distribution is 780 Stripe Greenhouse, 1,747 Greenhouse and 453 Lever. Source independence is recorded as 780 `separate_employer_controlled_page_and_official_greenhouse_api` and 2,200 `not_assessed`.

The 780-row evidence summary is 744 historical snapshot-only matches, 19 same-system retrieval/unverified, 16 unresolved and 1 unavailable; independent adjudicated authorization confirmations: 0. The lineage package reports 687 candidates/pairs, 0 confirmed relationships, and 666 candidate rows missing group IDs. The 192 candidate / 0 confirmed count from the disposable staging validation is a distinct staging-package count, not added to the 687 real lineage candidate-pair count.

These are descriptive machine/source states, not authorization ground truth. No real-world accuracy, precision, recall, F1 or fraud rate is available.

## Future evaluation

Because the prior Stage 7B test has been examined and the implementation has changed, current-system performance requires a new untouched test protocol. Freeze code/rules first, use independently established authorization labels, split by vacancy and lineage group, preserve unresolved cases, and report false-assurance/coverage together. Do not tune on the old test or call synthetic outcomes real-world accuracy.
