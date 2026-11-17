# Dataset reconciliation

Generated: 2026-11-14T04:25:59.484552+00:00

## Decision
- **Verified evaluation benchmark:** none available (human adjudication/confirmed lineage incomplete).
- **Primary collection/staging reference:** proposed unified 2,980-record package (`final_research_package/unified_proposed_dataset.csv`) — structurally valid, not approved as verified benchmark or automatic replacement.
- **Snapshot/provenance cohort:** 780 Stripe/Greenhouse processed tables and Stage 4E evidence.
- **Controlled implementation checks:** synthetic benchmark v1 (60 records).
- **Kept separate:** Naukri 198-record cohort.

## Overlaps

```json
{
  "stripe_pkg_case_ids": 780,
  "table_a_case_ids": 780,
  "table_a_vs_stripe_pkg_case_id_overlap": 780,
  "table_a_vs_unified_case_id_overlap": 780,
  "expansion_vs_unified_case_id_overlap": 2200,
  "stripe_vs_expansion_case_id_overlap": 0,
  "naukri_vs_main_case_id_overlap": 0
}
```

## Key findings
- Table A (processed 780) and stripe package use different `case_id` namespaces (0 overlap by ID) but represent the same Stripe/Greenhouse cohort context; do not merge without explicit mapping.
- Expansion package equals processed stage4f expansion by IDs (2200/2200) and is fully contained in unified proposed package.
- Naukri has no case-ID overlap with unified main package and must remain separate.
- No dataset may be treated as adjudicated ground truth today; reviewer worksheets/pair decisions remain unsubmitted.


## Post-execution reconciliation updates (2026-11-14T04:34:24.145264+00:00)
- **Employer count (17 vs 18):** unified main package has **18** distinct employers (1 Stripe cohort + 17 expansion cohort). The 17-count refers to expansion-only employers.
- **Lineage candidates (687):** 21 original + 459 Stage 4F + 207 Stripe pairs. All pending/unconfirmed in source artifacts; **0 confirmed, 0 rejected**. Prior human queue covered 144 provisional cases + 207 Stripe pairs (351 rows) but omitted 21 original and 459 Stage 4F candidates; prioritized worksheets/queue entries added with overlap identification.
- **Review queue coverage:** updated to include all required human-review categories (144 provisional annotations, 21 original lineage, 459 Stage 4F, 207 Stripe pairs, and targeted official-source verification list). Overlapping/duplicate-review risks flagged per item.
