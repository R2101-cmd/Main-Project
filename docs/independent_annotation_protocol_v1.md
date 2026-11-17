# Independent vacancy-authorization annotation protocol v1

## Scope

This benchmark evaluates vacancy authorization, not employer fraud or final fraud outcomes. Reviewers must not use predictions from the text baseline, naive aggregation, or lineage-aware aggregation when assigning the reference label.

## Labels

- `supported`: a source controlled by the employer or institution, or an official employer ATS, identifies the same employer, role, and relevant location/application route.
- `contradicted`: reliable evidence explicitly conflicts with authorization of the specific advertised vacancy. A closed or expired role alone is not contradictory and should be recorded as status evidence instead.
- `unresolved`: the source is an aggregator, social post, search result, repost, stale page, or otherwise insufficient to establish the specific vacancy authorization.

## Review procedure

1. Review the advertisement and its source records without viewing system predictions.
2. Check employer identity and vacancy authorization as separate claims.
3. Record the exact evidence identifiers and source URLs used.
4. Use `unresolved` when evidence is incomplete; do not infer fraud from missing evidence.
5. Keep all records in the same lineage group in one partition.
6. Adjudicate disagreements with a second reviewer before using the labels as a final benchmark.

## Metrics

Report accuracy, per-class precision/recall/F1, macro F1, weighted F1, confusion matrices, class counts, evidence coverage, abstention rate, and false assurance. A false-assurance event is a prediction of `supported` when the independent reference label is not `supported`.

## Current status

The generated benchmark is a provisional single-reviewer reference set. It is suitable for pipeline testing and exploratory comparison, but it is not a final publication-quality ground truth until a human reviewer independently confirms the records and disagreements are adjudicated.
