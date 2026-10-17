# Research specification

Unit of analysis: one advertised vacancy, with source appearances and evidence items linked to it. The primary target is vacancy authorization (`supported`, `contradicted`, `unresolved`), not a universal fraud label. Employer identity is a separate dimension (`verified`, `contradicted`, `unresolved`).

Hypothesis: consolidating dependent/copying source appearances will reduce false assurance relative to naive source counting. This remains untested until a reviewed dataset exists.

The planned baseline ladder is TF-IDF/logistic regression on advertisement text, employer-context rules, naive evidence aggregation, and lineage-aware aggregation. Splits must be grouped by lineage group; synthetic demonstrations are excluded. Metrics include decision coverage, selective risk, false assurance, false alarm rate, evidence coverage, and reviewed lineage precision, always with denominators and sample sizes.

Sampling, annotation, and thresholds must be fixed before final testing. No result is reported from the empty repository dataset.
