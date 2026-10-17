# Annotation guide

Annotators record evidence, not assumptions. Employer identity is verified only when an authoritative source supports the organization-domain relationship. Vacancy authorization is supported only by role-specific authorization evidence; a real employer or an absent careers listing is insufficient. Contradictory evidence must concern this vacancy or recruitment process.

Use `supported`, `contradicted`, `unverified`, or `unavailable` for claim-level evidence. Use `original`, `independent`, `copied_derived`, or `unknown` for source relationships. Retrieval failure is `unavailable`, not a negative finding. Expired or removed listings preserve observation and source timestamps and do not automatically imply fraud. Ambiguous cases remain unresolved.

Record rationale, source, timestamp, annotator, and disagreement resolution. Synthetic examples must be marked synthetic and never enter real evaluation metrics.

For each case, preserve the submitted source URL and final URL after redirects when available, a retrieval timestamp, a content hash or permitted snapshot reference, extracted claims, and OCR warnings. Record matched and conflicting fields explicitly. A public third-party posting may support vacancy existence while remaining unresolved for employer authorization. If more than one reviewer is available, annotate a fixed subset independently and adjudicate disagreements; with one reviewer, record that limitation rather than treating labels as independently validated.
