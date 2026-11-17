# Real-world follow-up: OCR, review, calibration, and evaluation

Prepared: 2026-11-17. This report records task completion status and metric availability; it does not turn unreviewed discovery records into ground truth.

## BEML OCR attempt

Target: BEML, Advertisement KP/S/09/2026, official PDF: https://www.bemlindia.in/wp-content/plugins/career/WCP/DATA/Writereaddata/Career/KP_S_09_2026.pdf. Two attempts to download the public PDF with PowerShell (the second with elevated network permissions and the apex hostname) failed because the connection was closed unexpectedly. The browser search index exposes parsed text, but it did not expose PDF bytes or a raster page; TrustHire's `extract_image_text` accepts image bytes, so its OCR function could not be run. Consequently there is no OCR output to compare against a visual gold transcription, no error count/rate, and no claim of real-poster OCR accuracy. The URL, visible ad date, failed retrieval, and review state are tracked in `research-data/real_world_discovery_v1/poster_ocr_eval_v1.csv`.

## Independent reviews

The discovery queue has 10 cases and 20 reviewer slots. Two separate AI reviewers completed 10 judgments each in `research-data/real_world_discovery_v1/ai_independent_reviews_v1.jsonl`; the comparison is in `ai_review_comparison_v1.json`. They agree on employer identity and vacancy authorization labels for all 10 cases (0 categorical disagreements). Both identify RW08 as closed/historical; both note RW05's requisition token is not visible in the retrieved page text. RW05 application-control and RW09 URL-access observations differed, which are evidence completeness caveats rather than categorical label disagreements. These are explicitly AI reviews and do not substitute for the protocol's two human reviewers or adjudication. The 20 human review slots remain blank; no human annotations have been supplied, and the repository's audit reports zero human-adjudicated records.

## E1-E5 final comparison

| Measure | E1 | E2 | E3 | E4 | E5 |
|---|---:|---:|---:|---:|---:|
| Eligible real-world test cases | 0 | 0 | 0 | 0 | 0 |
| Accuracy | NA | NA | NA | NA | NA |
| Macro F1 | NA | NA | NA | NA | NA |
| False assurance (numerator / denominator) | NA | NA | NA | NA | NA |
| Evidence/decision coverage | NA | NA | NA | NA | NA |

All five approaches must be scored on the same independently reviewed vacancy/lineage-group test records. There are none. Ten discovered records have provisional AI review only; they are not human-reviewed ground truth, and no frozen test split or adjudicated evidence set exists. Existing exploratory and synthetic metrics are not mixed into this table.

## Calibration and limitations

No decision threshold was calibrated or changed. Threshold fitting requires independently reviewed validation cases and a separately held-out test group; using the test cases to tune policy would invalidate the final estimate. Current real-world accuracy, macro F1, false-assurance rate, and coverage are therefore **not estimable**. The principal limitations are blocked binary access to the poster, missing human reviewers/adjudication, AI-only review judgments, small discovery cohort, no evidence snapshots, uncertain currentness for some rows, and no frozen group-separated split.

## Historical synthetic results (context only)

The existing synthetic 150-case comparison reports: E1 accuracy 0.367 / macro F1 0.276 / false assurance 82 of 100 / coverage 0.907; E4 ordinary aggregation 0.800 / 0.775 / 25 of 100 / 0.867; E5 lineage-aware raw 0.867 / 0.857 / 15 of 100 / 0.800; E5 live policy 1.000 / 1.000 / 0 of 100 / 0.667. These authored scenarios are controlled implementation checks, not reviewed real-world performance. E2 and E3 were not represented in that specific comparison, so it is not the requested E1-E5 comparison. Source artifact: `final_completion_package/current_implementation_evaluation_v1/metrics_summary.csv`.
