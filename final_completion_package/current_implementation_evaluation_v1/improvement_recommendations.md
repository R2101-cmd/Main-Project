# Improvement recommendations from the C raw error audit

## Recommended actions

1. Keep raw aggregation and final authorization outcomes explicitly separate in evaluations and interfaces. Score C_lineage_aware_raw against an evidence-aggregation target only if that target is defined independently. Score final authorization labels against the integrated lineage_aware() plus live decision policy. This fixes the identified comparison mismatch without changing production rules or tuning on v3.
2. Keep the live policy as the authorization output. Its independent-source, authority, correspondence, freshness, and conflict gates are what turn raw evidence state into an authorization decision. The five copied-group rows, five mixed-conflict rows, and ten stale/undated rows all remain unresolved through that path.
3. Clarify raw aggregation semantics wherever exposed. State that supported means the included evidence appearances/groups carry support, not that the vacancy has passed final authorization checks. Retain counts and the downstream decision explanation alongside it.
4. For future independent evaluation, define labels before predictions and align the target with the method. If the research question is final authorization, evaluate each approach at its complete specified decision path. If raw aggregation behavior itself is the target, write separate expected aggregation-state labels. Do not alter v3 labels or reuse this test set to tune changes.
5. Add new, independently designed cases for any future change. In particular, test that a single adjudicated copied group cannot yield final supported authorization; mixed eligible evidence stays unresolved; and stale or missing dates do not establish current support. Use a new held-out version and report coverage with false assurance.

## Production change decision and trade-offs

The audit does not justify changing production aggregation rules. The five copied cases are consolidated into one group as intended; the live policy prevents that group from meeting the two-independent-source requirement. The five conflict cases and ten freshness cases are unresolved in the integrated policy. Changing raw lineage_aware() to return unresolved in these cases might make its output look more like the final authorization label, but would conflate aggregation with policy, alter the method's contract, and potentially reduce coverage. Conversely, letting raw supported stand alone would increase false-assurance risk. Neither should be done to optimize the v3 score.

The justified correction is to the interpretation and evaluation protocol, not the production classifier: do not call raw C an authorization verdict or compare it alone with final authorization labels. The current C live outcome remains the relevant integrated result for this suite, while its perfect synthetic score is not a real-world performance estimate.

| Potential action | Expected benefit | Main trade-off/risk |
|---|---|---|
| Report C raw separately from C live (recommended; already represented in the package) | Makes the metric match the actual output level and exposes policy abstention | Raw and live scores are not directly interchangeable |
| Make raw aggregation abstain on one copied group | Raw state may align more closely with authorization labels | Changes aggregation semantics and may reduce coverage; duplicates a live-policy gate |
| Let raw aggregation decide final authorization without policy | None for reliability | Raises false-assurance risk on copies, conflicts, and stale evidence |
| Expand independent external adjudication and test on a new locked set | Enables meaningful accuracy estimates | Requires new data collection and annotation; cannot be inferred from the current synthetic test |
