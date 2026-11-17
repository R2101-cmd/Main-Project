# Integration risks

1. **Ground-truth leakage:** Stage 4E evidence classifications are not human ground truth. Loading them into `annotations` would create circular evaluation.
2. **Source independence inflation:** Greenhouse, employer pages, and copied postings may belong to one source family. Repeated retrievals are not independent authorization.
3. **Schema loss:** A direct import into the current SQLite tables would discard cohort, source-instance, response-hash, canonical-vacancy, freshness, and separate claim fields.
4. **Label collision:** Existing `supported` evidence states are not equivalent to adjudicated `vacancy_authorization_label=supported`.
5. **Lineage overclaim:** `src.lineage.similarity.candidate_relationship()` returns a candidate relationship; it does not establish human-confirmed lineage.
6. **Decision-policy limitation:** `src.decision.policy.assess()` treats any retrieval failure as a reason to abstain but does not model source independence, freshness, or explicit employer identity evidence.
7. **Batch-scale risk:** The UI has no pagination, cohort selector, package loader, or batch evidence ledger for approximately 3,000 records.
8. **Naukri contamination:** The 198-record Naukri cohort must not enter the main benchmark or be mixed with Stripe/Stage 4F metrics.
9. **Existing evaluation assumptions:** `src.evaluation.runner.run()` requires reviewed `authorization_label`, `partition`, and `vacancy_group`; the proposed CSV does not provide a valid frozen benchmark.
10. **Privacy/raw retention:** SQLite stores raw content blobs for poster/source records; any future batch import needs an explicit retention and access decision.
