# Phase 2 quality-control and release gates

## Record checks

- advertisement IDs and evidence IDs are unique;
- required identifiers are present;
- every evidence record references an existing advertisement and matching vacancy group;
- timestamps are strict ISO-8601 date-times with timezone information;
- source URLs are retained when available and unavailable sources have a recorded reason;
- missing fields have explicit missing-data notes;
- privacy review status is present;
- no record is silently converted from unavailable to negative evidence.

## Annotation checks

- labels are limited to `supported`, `contradicted`, and `unresolved`;
- employer identity and vacancy authorization labels are separate;
- evidence references exist;
- reviewer IDs are actual assigned reviewer IDs, not placeholders;
- original annotations are immutable and fingerprinted;
- adjudications reference at least two originals and preserve their fingerprints;
- no adjudicator silently replaces the original annotations.

## Lineage checks

- lineage review references existing advertisement IDs;
- a lineage group has at least two advertisements;
- relationship and review status are valid;
- `copied_derived` is not assigned solely from automated similarity;
- unknown relationships remain unknown;
- shared vacancy or confirmed dependent lineage groups do not cross future partitions;
- shared source URLs are reviewed separately because the same archive page may contain distinct vacancies.

## Evaluation release gate

Do not create or freeze a final split until the collection and annotation gates pass. E4 and E5 must run on exactly the same eligible cases. The test set must include meaningful reviewed dependent and independent lineage variation, all relevant authorization classes, and enough cases to report uncertainty. Passing schema validation alone is not evidence of research effectiveness.
