# Explicitly synthetic benchmark v1

This directory contains controlled synthetic scenarios only. The records are not collected advertisements, the source URLs are `synthetic://` identifiers, the timestamps are intentionally null, and the labels are assigned by the scenario generator rather than by independent human reviewers.

The benchmark is balanced across `supported`, `contradicted`, and `unresolved` authorization scenarios. It includes single-source, copied/derived, independent, unknown-lineage, and unavailable-source patterns.

Use it only for:

- schema and validator smoke tests;
- checking that unavailable evidence does not become fraud;
- checking E4/E5 aggregation mechanics;
- exercising metrics and partition checks.

Do not use its accuracy as evidence that TrustHire works on real recruitment data. A high score is expected when the controlled evidence state and generated reference label agree.

The generator is deterministic and writes only new files in this directory. It does not read or modify the existing 31-record benchmark.
