# Application integration test plan

Run only in a disposable copy or against the disposable staging database.

1. Import exactly 780 records and assert 780 unique external case IDs.
2. Assert cohort is exclusively `stripe_greenhouse_780`; reject Stage 4F and Naukri IDs.
3. Assert all original/recovered fields round-trip without changes.
4. Assert missing `retrieval_event_id` remains missing and creates no synthetic event rows.
5. Assert source-family/source-instance metadata remains marked derived where applicable.
6. Assert evidence observations do not populate authorization or fraud ground-truth labels.
7. Assert employer identity and vacancy authorization are separate claims.
8. Assert 192 candidate-involved records and 207 candidate-pair references remain candidate-only.
9. Assert confirmed-lineage count is zero.
10. Assert unavailable, unverified, unresolved, and contradicted states remain distinct.
11. Assert the existing single-vacancy workflow still handles pasted text, URL, and poster fixtures.
12. Assert no production database path is opened and no production tables are written.
13. Run the existing regression suite with cache and bytecode disabled; expected baseline is 65 passed, 2 warnings.
14. Test UI pagination/filtering only after the read-only loader is validated.

The integration test should fail closed on cohort contamination, duplicate external IDs, invalid labels, fabricated retrieval events, or candidate-to-confirmed lineage conversion.
