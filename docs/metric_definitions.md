# Metric definitions

- Accuracy: proportion of test records whose predicted authorization label equals the reference label.
- Precision/recall/F1: reported for each authorization class and for the positive `supported` one-vs-rest view.
- Macro F1: unweighted mean of per-class F1; important under class imbalance.
- Weighted F1: support-weighted mean of per-class F1.
- Balanced accuracy: mean recall across classes present in the reference set.
- Evidence coverage: proportion of records with at least one evidence item.
- Decision coverage: proportion of test records for which a method returns a definitive state rather than unresolved/abstain.
- Abstention rate: one minus decision coverage.
- False assurance rate: definitive `supported` predictions on reference non-supported records divided by all eligible reference non-supported records, including non-supported records on which the method abstained. Report the definitive numerator, full reference denominator, decision coverage, and abstention rate together.
- False alarm rate: where defined, the proportion of non-contradicted records predicted `contradicted`.

Zero precision/recall/F1 is reported when a class is present but never predicted. Metrics are not interpreted as reliable generalization evidence when test size or class support is inadequate. PR-AUC and statistical superiority claims are not reported for the current small, two-class provisional test set.
