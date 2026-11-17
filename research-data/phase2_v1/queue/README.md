# Manual review queue

`manual_review_queue_v1.jsonl` contains references to existing benchmark IDs only. It is a work queue, not a replacement annotation file. The `current_reference_label` field records the existing value for audit traceability; it is not a proposed correction.

Reviewers must create independent annotation records using the Phase 2 schema. They must not edit the queue to overwrite labels, and they must not mark a relationship as copied solely because two records share a URL.
