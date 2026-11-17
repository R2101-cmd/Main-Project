# Data integrity report

## Protected baseline

Before implementation, SHA-256 and byte-size values were recorded for 69 protected files in `protected_checksums_before.json`. The baseline includes the established 21-file protected-data checksum set, original research tables/cohorts and annotations covered by that set, synthetic benchmark v2 source and split files, the flat Stage 7B evaluation package, real descriptive outputs, and prior protected reports.

The post-implementation comparison is in `integrity_comparison.csv`; final values are in `protected_checksums_after.json`.

| Result | Count |
|---|---:|
| Protected files hashed | 69 |
| Byte-identical SHA-256 matches | 69 |
| Missing files | 0 |
| Changed files | 0 |

No benchmark generation, annotation, Stage 7B evaluation command, dataset export or database import was run. The split validator ran in validation-only mode; staging validation was read-only.

## Initial worktree state

The repository already had modified tracked files and extensive untracked research/data artifacts before this implementation. `initial_worktree_status.txt` records that state. Existing changes were preserved. `changed_files_manifest.json` distinguishes files touched for this task from files that were already dirty or untracked.

The 69-file comparison does not assert a before/after hash for every auxiliary/raw item under the large untracked research folders. During final review, five additional historical synthetic files were found outside that baseline: the extended 30-case JSONL and manifest, plus three `controlled_v2` files. Their current hashes are recorded in `supplemental_historical_artifact_hashes.json`, but no pre-implementation checksums for these five files were available in the repository, so a before/after comparison cannot be claimed for them.

The `DatasetCollection/raw` tree contains 3,841 files (590,657,824 bytes). Current hashes for all of them are recorded in `supplemental_raw_dataset_current_hashes.json`. A pre-implementation checksum baseline for that tree was not available, so these are preservation references rather than before/after comparisons. No dataset generator/export/import command was run, and the implementation only wrote code, tests, README/config and the new completion package.

The implementation did not run any benchmark writer or evaluator against the five historical synthetic files. These baseline gaps are reported rather than represented as verified matches.
