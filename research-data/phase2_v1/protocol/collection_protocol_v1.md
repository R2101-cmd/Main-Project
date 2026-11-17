# Phase 2 real-record collection protocol v1

## Sampling frame

Before collection begins, document the collection period, permitted source classes, geographic or occupational scope, inclusion rules, exclusion rules, and target number of vacancy groups. Do not change these rules after looking at test errors without creating a new confirmatory set.

## Collection unit

Keep each advertisement instance as a separate record. Assign a vacancy-group ID only when the relationship is supported by documented evidence or a reviewed lineage decision. Do not merge records because their text looks similar.

For each advertisement, retain the original input form, original source URL where available, source type, observed timestamp, publication timestamp when available, source snapshot reference, and privacy status. Missing values must be recorded as missing with a reason.

## Evidence collection

Collect evidence before assigning the reference authorization label. Keep separate evidence records for:

- official employer or institutional sources;
- third-party listings;
- independent sources;
- copied or derived sources;
- unavailable, blocked, empty, or failed retrievals.

Record the submitted URL, retrieval status, retrieval timestamp when a request was attempted, HTTP status when available, extracted-content status, relevant excerpt, matched and contradicted fields, rationale, and snapshot reference. Do not treat unavailable evidence as negative evidence.

## Lineage review

Use text similarity, shared URLs, shared contact details, common requisition IDs, and publication context only as signals. A reviewer must decide whether a relationship is `independent`, `copied_derived`, or `unknown`. Similarity alone must not establish copying. Unknown relationships must not be consolidated by E5.

For confirmed dependent advertisements, keep the same vacancy/lineage component in one future partition. Do not create the final train/validation/test split during this preparation phase.

## Independent labels

Two reviewers independently annotate the same cases using the annotation guide. They must not see each other's labels or model outputs. Record inter-annotator agreement, preserve both originals, and have an adjudicator resolve disagreements. A confirmed label is not available until the required review state is complete.

## Access and privacy

Use only permitted public access. Do not bypass authentication, robots restrictions, CAPTCHAs, paywalls, or rate limits. A failed or restricted request is an evidence-availability result, not a fraud label. Redact unnecessary personal data and record privacy review decisions.
