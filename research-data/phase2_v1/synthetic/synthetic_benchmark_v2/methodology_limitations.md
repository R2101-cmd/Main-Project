# Synthetic benchmark v2: methodology and limits

This package contains 300 generated cases, balanced across supported, contradicted,
and unresolved expected outcomes (100 each). It contains no real advertisements,
employers, URLs, retrieval events, or independent observations. The fixed generation
seed is 20261114. The expected outcomes are design labels justified by the explicit
synthetic evidence scenario and are not human-reviewed ground truth.

## Separation and mapping

`model_inputs.jsonl` contains only an opaque `input_key`, synthetic advertisement
fields, and synthetic evidence. It omits case IDs, scenario names, expected labels,
and scenario notes. `expected_labels.jsonl` maps every input key to a unique case ID
and expected outcome. `scenario_metadata.jsonl` maps the same key to its scenario and
vacancy group. Both latter files are evaluation-only and must not be supplied to an
approach. `manifest.json` records counts and hashes.

## Scenario construction

Each of 15 scenario families has 20 distinct synthetic vacancies. Support labels
require a current synthetic employer-controlled matching source explicitly marked
independently supported. Contradiction labels require a material, specific current
synthetic employer-controlled denial or mismatch. Unresolved labels represent
conflicting independent reports without resolution, unverified claims with unknown
or absent lineage, stale snapshot-only evidence plus unavailable current sources,
or incomplete records without decisive evidence. Copied reports are assigned one
adjudicated dependent group and cannot be interpreted as multiple independent
confirmations. These conventions make the constructed outcome traceable; they do not
simulate a validated real-world source authorization process.

## Historical artifacts

The 60-record `synthetic_benchmark_v1.jsonl`, the 30-record
`synthetic_benchmark_extended_v1.jsonl`, and the provisional 60-record
`controlled_v2` directory are historical files and remain unchanged. The first two
are retained as historical experiments; their prior splits and metrics are not
reused here. The provisional controlled_v2 manifest records 10 supported, 15
contradicted, and 35 unresolved records, so it is not this balanced benchmark and
its exposed case/scenario fields are not reused as model inputs.

## Limits

This package is for a later controlled software comparison only. No A/B/C inference,
accuracy, precision, recall, F1, calibration, or real-world performance was measured
when generating it. Synthetic coverage is intentionally finite and cannot establish
generalization, fraud prevalence, or operational suitability. Inspect construction
and validation before any later evaluation; freeze the test protocol before viewing
test results.
