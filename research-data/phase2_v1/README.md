# TrustHire Phase 2 research-data workflow

This directory is a separate preparation area for independently reviewed vacancy-authorization data. It is not the active benchmark and must not be used as an evaluation set until human annotation, adjudication, provenance review, lineage review, and a new frozen split are complete.

## Safety boundary

- The existing benchmark is preserved byte-for-byte at `working/current_benchmark_copy_read_only.jsonl`.
- The source file is `data/annotations/job_ad_independent_review_v1.jsonl`.
- No label in the working copy is a proposed replacement label.
- No records, evidence, timestamps, snapshots, reviewers, or lineage relationships have been invented here.
- The collection files are intentionally empty until real records and human decisions are supplied.
- Do not place synthetic examples in the collection files.

## Layout

| Path | Purpose |
|---|---|
| `schemas/` | Phase 2 JSON Schemas for advertisements, evidence, annotations, lineage review, and adjudication |
| `protocol/annotation_guide_v1.md` | Human annotation rules |
| `protocol/collection_protocol_v1.md` | Real-record collection and provenance procedure |
| `protocol/quality_control_v1.md` | Validation and release gates |
| `queue/manual_review_queue_v1.jsonl` | Review-only queue referencing existing record IDs |
| `working/current_benchmark_copy_read_only.jsonl` | Byte-for-byte copy of the current 31-record benchmark |
| `scripts/validate_phase2_dataset.py` | Read-only validator for future Phase 2 records |

Recommended future collection files are separate JSONL tables:

- `advertisements_v1.jsonl`
- `evidence_v1.jsonl`
- `independent_annotations_v1.jsonl`
- `lineage_reviews_v1.jsonl`
- `adjudications_v1.jsonl`

These files should remain empty until real observations and human review decisions exist.

## Release rule

The Phase 2 data is not evaluation-ready while any required field is missing, any reviewer is provisional or unidentified, any disagreement is unadjudicated, any lineage relationship is unresolved for a claimed dependent group, or any vacancy/lineage group crosses a future partition.
