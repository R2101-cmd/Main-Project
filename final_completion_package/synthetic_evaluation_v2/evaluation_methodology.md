# Synthetic benchmark v2 A/B/C evaluation methodology

## Target and data use

The target is `vacancy_authorization_label`, with `supported`, `contradicted`, and `unresolved` outcomes. This controlled synthetic experiment evaluates the 60-case frozen test partition only. The benchmark inputs, expected labels, scenario metadata, and group-safe split remain separate. All three approaches receive the same test records. No case ID, scenario, expected label, or scenario metadata is passed to a predictor.

Training uses only the 180 train-partition texts and labels. A uses the existing `TextBaseline` (TF-IDF word unigrams/bigrams and logistic regression) with model seed 20261116; inference uses only the advertisement text. B calls production `naive()` on the evidence list. C calls production `lineage_aware()` on that same evidence, passing only explicitly adjudicated copied-derived group keys. No thresholds or aggregation rules were tuned. Validation data was not used for configuration. Test labels and scenario metadata were read only after all test predictions were fixed.

## Metrics

Accuracy includes all test cases, including unresolved predictions. Macro precision, recall, and F1 average the three classes with zero assigned to undefined class metrics. Coverage is the fraction predicted supported or contradicted; unresolved predictions count as abstentions. False assurance is a prediction of supported on an expected contradicted or unresolved case. Its denominator is all expected non-supported test cases, including unresolved. Accuracy and false-assurance intervals use 95% Wilson intervals. B versus C uses exact two-sided McNemar on paired correctness and paired percentile bootstrap intervals for C-minus-B accuracy and macro-F1 (10000 resamples; fixed seeds recorded in the manifest).

## Test-set scope and observed comparison

The test set has 60 cases and expected class distribution {'contradicted': 20, 'supported': 20, 'unresolved': 20}. It includes 15 scenario families, each represented in every split (4 test cases per family). It therefore measures held-out cases within known families; it is not an unseen-scenario generalization test.

Observed test accuracy: A 0.550, B 0.867, C 1.000. Paired B-versus-C exact McNemar p=0.0078; this small synthetic set does not justify broad superiority claims.

The benchmark's outcomes are synthetic scenario-construction labels, not independently adjudicated real-world ground truth. These values are controlled experimental results only.
