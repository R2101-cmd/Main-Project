# Phase 2 independent annotation guide v1

## Scope

Annotate two separate claims for each advertisement:

1. `employer_identity_label`: whether the named employer identity is supported, contradicted, or unresolved.
2. `vacancy_authorization_label`: whether the specific advertised vacancy is supported, contradicted, or unresolved.

Do not infer a vacancy authorization label from employer identity alone. Do not use a model prediction, E4/E5 output, or another reviewer's label when making an independent annotation.

## Authorization labels

### Supported

Use `supported` only when the available evidence directly supports authorization of this specific vacancy. The evidence should identify the same employer and vacancy-specific details such as title, requisition/job ID, location, posting details, or an employer-controlled application route. Record the evidence IDs and explain the matching facts.

A third-party listing by itself is not enough unless the protocol and evidence explicitly establish the employer's authorized relationship to that listing.

### Contradicted

Use `contradicted` only for affirmative evidence that conflicts with authorization of this specific vacancy. Examples include an official employer source explicitly denying the vacancy, a verified source identifying the same requisition as unauthorized, or a reliable source showing that the advertised vacancy details are false in a way that bears on authorization.

Do not use `contradicted` merely because a page is inaccessible, a job has expired or closed, an official listing cannot be found, a third-party page is incomplete, or a retrieval request failed. Those cases are normally `unresolved`.

### Unresolved

Use `unresolved` when evidence is insufficient, inaccessible, stale, incomplete, conflicting without an affirmative authorization contradiction, or limited to an unverified third-party source. `Unresolved` is an intentional reference outcome, not a claim of fraud.

## Required annotation record

Record the reviewer ID, protocol version, timestamp, employer identity label, vacancy authorization label, evidence IDs, rationale, information still needed, and adjudication status. Keep the original annotation immutable after submission. If reviewers disagree, preserve both originals and create a separate adjudication record.

## Blinding and independence

Reviewers must receive the advertisement and evidence packet without model predictions, E4/E5 outputs, another reviewer's label, adjudication notes, or test-error analysis. Repository access controls do not by themselves guarantee human blinding.

## Privacy

Redact unnecessary personal contact details. Preserve only the minimum information needed to audit the claim and record the privacy-review status.
