# Dataset import guide

Place the original file at:

`data/raw/fake_job_postings.csv`

The original file is preserved. Run:

```powershell
python scripts\import_job_dataset.py
```

Outputs:

- `data/processed/fake_job_postings_imported.jsonl`: one normalized raw record per retained input row after exact-duplicate removal.
- `data/processed/fake_job_postings_import_report.json`: columns, missing values, duplicates, source-label counts, and repost-candidate counts.

The importer preserves original values under `original`, adds normalized title/location/company-profile matching fields, and keeps `source_fraud_label` separate from `authorization_label`. Every imported authorization label is `unresolved`; no official source, URL, requisition ID, employer verification, or evidence is invented.

Exact duplicate rows are reported and removed from the processed output, while the original CSV remains untouched; the retained record lists duplicate source IDs. Potential reposts are candidate relationships only; records are not merged. Conservative candidate components are used as `split_group` values so related records cannot leak across train, validation, and test partitions. Singleton records receive their own split group.

The dataset is not directly suitable for authorization evaluation until a reviewer attaches vacancy-specific evidence and assigns reviewed authorization labels according to `docs/annotation_guide.md`.
