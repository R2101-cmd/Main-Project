# UI compatibility

## Current support

The existing UI supports pasted text, public URL, and poster-image input. It displays extracted fields, evidence availability, field comparisons, evidence states, naive aggregation, lineage-aware aggregation, and unresolved warnings. It explicitly states that unavailable evidence is not fraud and that employer identity does not itself authorize a vacancy.

The existing single-vacancy workflow can be preserved unchanged if the staging dataset is used only by a separate read-only browser or as a fixture source.

## Missing UI capabilities

The UI has no batch-record loader, cohort selector, 780-record table, source-family/source-instance display, provenance-field-source display, explicit historical-versus-derived marker, or candidate-lineage review panel. It also does not display the proposed staging database claims as imported records.

Candidate lineage should be shown as “candidate/unadjudicated”; it must never be rendered as confirmed. Labels should remain blank or unresolved. A future UI must show employer identity and vacancy authorization as separate claims.
