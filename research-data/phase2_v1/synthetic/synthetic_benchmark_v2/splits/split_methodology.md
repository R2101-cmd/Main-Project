# Synthetic benchmark v2 split methodology

This package partitions the existing synthetic benchmark without changing its source files. The fixed split seed is `20261115` and target proportions are 60% train, 20% validation, and 20% test. Assignment is deterministic and stratified by the evaluation-only expected class and scenario family, after creating connected components from vacancy identifiers and shared evidence/lineage identifiers. A connected component is assigned wholly to one partition. A component spanning expected classes or scenario families causes generation to stop rather than split related records.

## Field mapping used

- Source model records use `input_key`; it is removed from partition model inputs.
- Evaluation label rows use `input_key`, `case_id`, and `expected_label`.
- Scenario rows use `input_key`, `case_id`, `vacancy_group`, `scenario`, and `scenario_slot`.
- Nested evidence has `lineage_group`, `source_relationship`, `lineage_review_status`, and source URLs. Shared lineage groups and exact repeated source URLs are included in connected-group construction.
- Per-partition evaluation mappings use `record_ordinal` to join rows by file order. Those mappings are not part of the model input files.

## Split counts and scenario overlap

Train: 180 records, classes {'contradicted': 60, 'supported': 60, 'unresolved': 60}.

Validation: 60 records, classes {'contradicted': 20, 'supported': 20, 'unresolved': 20}.

Test: 60 records, classes {'contradicted': 20, 'supported': 20, 'unresolved': 20}.

All 15 scenario families occur in every partition. Thus the test partition evaluates held-out cases drawn from known scenario families. It cannot support a claim of generalization to unseen scenario families.

## Leakage and limits

The source contains 300 connected components; largest size is 1. No vacancy or evidence/lineage group crosses partitions. The inputs omit expected labels, case IDs, scenario names, scenario slots, and evaluation-only vacancy grouping fields. Evidence lineage and evidence-state fields remain in inputs because they are part of the information available to an evidence aggregation approach. This is a synthetic split only; it does not establish real-world accuracy or generalization. No A/B/C evaluation or accuracy metric was run while creating this split.
