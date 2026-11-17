# Independent annotation protocol v2

## Review sequence

1. Freeze the advertisement text, claimed employer, role, location, application route, collection timestamp, and lineage candidates.
2. Review the advertisement and source records without viewing E1–E5 predictions.
3. Verify employer identity separately from vacancy authorization.
4. For each source, record URL, source type, retrieval time, publication time if known, final URL, relevant matched fields, and retrieval state.
5. Determine whether the source addresses this exact vacancy or only the employer generally.
6. Record whether the source is current enough for the claim and whether it appears copied or derived.
7. Assign one authorization label with a written rationale and evidence IDs.
8. Record what additional evidence would resolve an unresolved case.

## Decision rules

`supported` requires role-specific evidence from an employer-controlled source or an employer recruitment system that matches the employer, role, and relevant location or requisition/application route. `contradicted` requires affirmative reliable evidence that the specific vacancy or recruitment claim is false or unauthorized. Absence, expiry, redirect, blocked access, and third-party-only presence are not contradiction. `unresolved` is required when the available evidence is relevant but inconclusive, unavailable, stale, or only establishes employer existence.

## Relationship review

Record `original`, `independent`, `copied/derived`, or `unknown`, with observed signals and a confidence/review status. Text similarity is a candidate signal, not proof. Shared employer names alone do not establish copying; different URLs do not establish independence.

## Examples

- Hypothetical supported: an official employer ATS page identifies the exact requisition, title, location, employer, and application form.
- Hypothetical contradicted: an employer’s authenticated recruitment notice states that the exact requisition number was never issued and the advertised application route is fraudulent.
- Hypothetical unresolved: a third-party repost matches the title and employer but no official source or vacancy-specific authorization can be found.

## Agreement

Where feasible, two reviewers label the same fixed subset independently. Report raw agreement and an appropriate statistic only when class support permits interpretation. With one reviewer, label the result single-reviewer provisional and do not claim inter-annotator validation.

## Record forms and preservation

Each original decision is an `independent_original` record using `schemas/annotation_form_v1.schema.json`. It must include the reviewer ID, protocol version, annotation timestamp, authorization label, evidence IDs, vacancy-level rationale, and a request for additional information when needed. An adjudication is a separate record using `schemas/adjudication_form_v1.schema.json`; it references both original annotation IDs and their fingerprints, records the adjudicator and timestamp, and explains the outcome. Adjudication must never replace or edit the original decisions.

Reviewer identifiers are operational values, not placeholders. Until actual reviewers are assigned, the configuration gate remains pending and the project must not be described as independently annotated.
