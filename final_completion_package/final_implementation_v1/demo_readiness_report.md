# Demonstration readiness

## Status

**Ready for an academic prototype demonstration with conservative unresolved outcomes.** Not ready to claim operational vacancy authorization performance or real-world accuracy.

## Demonstrated workflow

- Pasted-text, public-URL and poster-image modes render in Streamlit AppTest.
- A pasted-text case was submitted end-to-end without external network access; the result displayed separate employer identity, vacancy authorization and fraud outcome, all unresolved when evidence was absent.
- Evidence ledger and field comparison use source-provided values and explanations. Requisition/job ID, salary, employment type and all four date concepts are available when extraction finds them.
- The live app no longer displays synthetic reference labels or a benchmark case picker.

## Presenter guidance

Explain that a verified employer does not establish authorization for a particular vacancy. An empty employer authority configuration, unknown/unadjudicated source lineage, stale dates, incomplete fields or fewer than two qualifying independent groups will leave the final authorization unresolved. Fraud is a separate outcome and remains unresolved absent a separate fraud-evidence policy.

Use the existing historical synthetic evaluation only with its own methodology and limitations. Do not present its 100% C accuracy as current live-system or real-world accuracy.

## Commands (Windows PowerShell)

```powershell
streamlit run app.py
python scripts\smoke_test_streamlit.py
python -m pytest -q
```
