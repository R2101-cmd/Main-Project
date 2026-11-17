# Stage 4 independent official-source verification (artifact-based execution)

Generated: 2026-11-14T04:25:59.484552+00:00

## What was executed
- Audited existing Stage 4E evidence records (780 Stripe/Greenhouse cohort) and produced per-case verification classifications without modifying original artifacts.
- Preserved distinction between retrieved/snapshot evidence and human-adjudicated independent authorization.
- No CAPTCHA/auth bypass, no private/local targets, no unsafe crawling; **no new live network retrieval** was performed in this run.

## State mapping (conservative)
- `snapshot_match_only`: collected retrieval/same-system evidence exists (including official-confirmation/fresh-same-system classes) but employer-vacancy authorization is not human-adjudicated as independently verified.
- `inaccessible`: retrieval failed/unavailable in collected evidence.
- `independently_unresolved`: insufficient collected evidence for determination.
- `independently_supported` / `independently_contradicted`: reserved for future human-adjudicated outcomes with authority-confirmed evidence (0 in this artifact-based pass).

## Coverage and blocker
- Classified records: 780 / 780 collected stage4e records.
- Live independent re-verification of public official sources remains required for higher-assurance claims; prioritize cases in `verification_failures.csv` and any human-review queue.
