# Final system workflow

1. **Intake:** Streamlit accepts pasted advertisement text, a public HTTP/HTTPS URL, or an uploaded recruitment poster. URL requests pass through public-address validation and pinned-IP transport. Poster text is extracted locally where OCR support is installed.
2. **Extraction:** The parser extracts employer, title, description, location, salary, requisition ID, application URL, employment type and distinct `date_posted`, `date_modified`, `valid_through` values. Missing or conflicting values remain missing/conflicted with provenance.
3. **Authority mapping:** The advertised employer name is matched to the operator-maintained mapping file. Only explicit verified mappings with provenance are considered. ATS entries must also scope to the verified tenant path. A hostname resemblance or user-entered link does not establish employer authority.
4. **Retrieval and comparison:** Candidate public pages are fetched, timestamped, extracted and compared field by field. Retrieval failure, stale or invalid dates, inadequate vacancy correspondence and missing fields remain unresolved.
5. **Lineage candidates:** Retrieved sources are compared for possible textual/metadata overlap. Candidate results are shown as candidates; the evidence relationship remains unknown and not assessed. No IDs/groups or adjudication are inferred.
6. **Research aggregation B:** Existing `naive()` counts eligible evidence appearances without dependency deduplication.
7. **Research aggregation C:** Existing `lineage_aware()` counts only explicit adjudicated independent/dependent relationships and consolidates confirmed copies by group. Missing/unknown/unassessed lineage is excluded.
8. **Final live decision:** A separate conservative policy requires two qualifying independent source groups, source authority, current evidence and vacancy correspondence. Conflicting evidence remains unresolved. The policy returns Supported, Contradicted or Unresolved independently from employer identity.
9. **Fraud outcome:** Always presented separately. Authorization evidence alone does not set `confirmed_fraudulent` or `confirmed_legitimate`; absent a separate fraud-outcome rule and evidence, it remains unresolved.

Research A remains the TF-IDF word unigram/bigram + Logistic Regression baseline trained only on training partition text and labels. A/B/C evaluation remains a separate CLI workflow; the Streamlit live path is not an evaluation harness.
