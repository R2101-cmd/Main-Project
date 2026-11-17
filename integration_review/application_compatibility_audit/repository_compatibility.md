# Repository and database compatibility

## Findings

The current repository is write-oriented and generates UUIDs for advertisements, evidence, lineage relationships, claims, and source records. It has no read-only import method for `disposable_staging_import.csv`, no cohort-aware query, and no method for preserving an external `case_id` as a first-class key.

`schema.sql` lacks cohort, source-family, source-instance, retrieval-event, missingness, provenance-field-source, and confirmed-versus-candidate lineage separation. `annotations` stores one generic dimension and label, so it can technically store separate dimensions but does not enforce the three-claim protocol.

## Safety conclusion

The application must not import the staging CSV directly through the current repository. A future adapter should be read-only first, retain `case_id`, and write only to a versioned staging database. The production database must remain unchanged until migration design and tests are approved.

The proposed staging schema correctly leaves `retrieval_events` empty for all 780 records and records missingness separately. It also keeps the confirmed-lineage table empty and candidate lineage separate.
