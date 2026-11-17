# Integration readiness report

## What works

- The application launches as a Streamlit evidence-review interface.
- Pasted text, public URL, and poster-image input paths exist.
- Public URL safety checks and bounded retrieval are implemented.
- HTML/JSON-LD/meta extraction exists.
- Evidence ledger, field comparison, unresolved handling, and retrieval warnings exist.
- Naive and lineage-aware aggregation are both displayed.
- Existing tests and schemas cover the current application workflow.

## Implemented completion

- A read-only staging loader validates the packaged CSV and preserves raw/provenance fields (`src/datasets/staging.py`).
- Cohort filtering and a default Naukri exclusion boundary are available in the staging CLI; the interactive UI remains scoped to one submitted vacancy.
- Source-family/source-instance/retrieval-event identity, response hashes, timestamps, and official URLs are retained by the staging adapter.
- No explicit freshness, response-hash, official-employer URL, or canonical-vacancy display in the application schema.
- No separate persisted employer-identity and vacancy-authorization evidence model for imported package rows.
- Candidate and confirmed lineage are represented separately; candidates remain candidates until adjudication.
- No valid frozen human-ground-truth benchmark; Stage 5B reviewer labels and lineage decisions were inspected as blank.
- `scripts/validate_staging_package.py` provides a no-write validation pass; batch database import remains intentionally out of scope.

## Safety decision

**GO for read-only staging validation; NO-GO for automatic dataset replacement, production integration, supervised evaluation, or merging Naukri.**

**NO-GO for automatic dataset replacement, production integration, supervised evaluation, or merging Naukri.**

## Recommended tests before integration

- Schema and allowed-value validation, including explicit missingness.
- 780-record Stripe import dry run with zero writes to the current database.
- Stage 4F import dry run with employer/source-family counts preserved.
- Naukri exclusion test proving it cannot enter the main cohort query.
- Stable-ID and URL/job-identifier duplicate tests.
- Evidence-state test proving unavailable/unresolved are never converted into fraud.
- Source-independence test proving same-ATS retrieval is not independent authorization.
- Lineage test proving candidates remain candidates until adjudication.
- Group-aware split leakage test.
- Poster/PDF fixture tests preserving input type and provenance.
- Existing regression suite run in a disposable environment.

No existing application file was modified during this review. The exact modifications listed in `proposed_integration_plan.md` should be approved separately before implementation.
