# C raw lineage-aware aggregation: error analysis

## Scope and result

This audit compares C_lineage_aware_raw in case_level_comparison.csv against the separate synthetic expected authorization labels. It finds 20 incorrect rows out of 150 (86.7% accuracy): 15 expected unresolved but predicted supported, and 5 expected unresolved but predicted contradicted. All 20 expected labels are unresolved. No supported or contradicted expected case was missed by raw C.

The important distinction is that raw lineage_aware() returns an aggregate evidence state; it does not apply the live authorization gates for independent-source count, authority, vacancy correspondence, freshness, or conflicting evidence. The expected labels here describe authorization outcomes. Comparing raw C states directly with authorization labels therefore mixes two decision levels. C live applies the production policy and correctly returns unresolved for these same 20 authored cases. This identifies an evaluation endpoint mismatch, not evidence that the live production path made these 20 errors.

## All incorrect cases

| Input key | Expected | C raw | Scenario family | Evidence condition and cause |
|---|---|---|---|---|
| input-0100 | unresolved | supported | copied_repost_cluster | Three available supported appearances; all adjudicated copied_derived, same group copy-100. Raw C deduplicates to one group then reports its support state. |
| input-0101 | unresolved | supported | copied_repost_cluster | Three available supported appearances; all adjudicated copied_derived, same group copy-101. One dependent group is not two independent confirmations. |
| input-0102 | unresolved | supported | copied_repost_cluster | Three available supported appearances; all adjudicated copied_derived, same group copy-102. |
| input-0103 | unresolved | supported | copied_repost_cluster | Three available supported appearances; all adjudicated copied_derived, same group copy-103. |
| input-0104 | unresolved | supported | copied_repost_cluster | Three available supported appearances; all adjudicated copied_derived, same group copy-104. |
| input-0115 | unresolved | contradicted | conflicting_official_records | One current adjudicated independent supported group and one current adjudicated independent contradicted group; both correspond to the vacancy. Raw aggregation resolves any contradiction as contradicted; live policy treats mixed evidence as unresolved. |
| input-0116 | unresolved | contradicted | conflicting_official_records | Same pattern: one independent support and one independent contradiction, with job_location conflict. |
| input-0117 | unresolved | contradicted | conflicting_official_records | Same pattern: two distinct current independent groups with opposite states. |
| input-0118 | unresolved | contradicted | conflicting_official_records | Same pattern: two distinct current independent groups with opposite states. |
| input-0119 | unresolved | contradicted | conflicting_official_records | Same pattern: two distinct current independent groups with opposite states. |
| input-0130 | unresolved | supported | stale_source_dates | Two adjudicated independent support groups, both marked stale; raw aggregation does not consume freshness. |
| input-0131 | unresolved | supported | stale_source_dates | Two adjudicated independent support groups, both marked stale. |
| input-0132 | unresolved | supported | stale_source_dates | Two adjudicated independent support groups, both marked stale. |
| input-0133 | unresolved | supported | stale_source_dates | Two adjudicated independent support groups, both marked stale. |
| input-0134 | unresolved | supported | stale_source_dates | Two adjudicated independent support groups, both marked stale. |
| input-0135 | unresolved | supported | missing_source_dates | Two adjudicated independent support groups; freshness is unresolved on both because dates are absent. |
| input-0136 | unresolved | supported | missing_source_dates | Two adjudicated independent support groups; freshness is unresolved on both. |
| input-0137 | unresolved | supported | missing_source_dates | Two adjudicated independent support groups; freshness is unresolved on both. |
| input-0138 | unresolved | supported | missing_source_dates | Two adjudicated independent support groups; freshness is unresolved on both. |
| input-0139 | unresolved | supported | missing_source_dates | Two adjudicated independent support groups; freshness is unresolved on both. |

The detailed evidence fields are preserved in research-data/phase2_v1/synthetic/synthetic_benchmark_v3/model_inputs.jsonl; label rationales and scenario names are in the evaluation-only files. The rows above were checked against both files and the stored case-level predictions.

## Error categories

Categories overlap because each error has both a triggering evidence condition and a comparison-design cause.

- Evidence lineage handling (5): copied appearances are consolidated correctly, but raw C reports the remaining group's evidence state. A dependent group cannot satisfy the live policy's two-independent-group condition; raw aggregation itself has no such final threshold.
- Contradiction handling (5): raw aggregation's existing contradiction precedence returns contradicted when any eligible contradiction exists. The live decision policy separately recognizes mixed support and contradiction and abstains.
- Freshness handling (10): raw aggregation does not inspect freshness. Stale and unknown freshness are authorization-policy concerns, and the live path withholds a current authorization result.
- Insufficient or ambiguous evidence (20): all 20 cases lack sufficient conditions for a definitive authorization outcome under the documented synthetic rationales.
- Synthetic benchmark/evaluation design issue (20): raw aggregation states were scored as though they were final authorization predictions. The expected labels encode the live policy gates; raw C does not apply those gates.
- Authority verification and vacancy correspondence (0 observed errors): these gates were not the cause in the 20 cases; copied cases were current and matching in the fixture. Raw C does not test these gates, which is an interface limitation, not a failure triggered by these rows.

## Methodology consistency and production assessment

The v3 scenario definitions explicitly say the copied-only case cannot satisfy the live two-independent-source policy; conflicting records should abstain; and stale or undated records cannot establish current authorization. Those are valid expected authorization outcomes. However, C_lineage_aware_raw is only lineage_aware(evidence).state, which intentionally does not enforce those policy conditions. Thus the labels do not conflict with the intended authorization methodology, but the raw-C metric is not a like-for-like measure of final authorization decisions. C live is the corresponding policy-level output.

No evidence in these 20 rows demonstrates a defect in the integrated production decision path. A real product risk would arise if a consumer displayed or acted on raw C's state as a final authorization decision without the existing policy gates. The application path inspected for this evaluation applies those gates. The 86.7% raw-C figure is primarily an endpoint mismatch in the synthetic comparison, not a finding that the final production path has 86.7% authorization accuracy.
