# Application model mapping

## Existing application model

`app.py` is a single-vacancy Streamlit workflow. `_assess_input()` extracts one advertisement, obtains permitted public sources, calls `collect_vacancy_evidence()`, then sends the observations to `naive()`, `lineage_aware()`, and `assess()`. The result is held in Streamlit session state and rendered by `_render_assessment()`.

The SQLite model contains `advertisements`, `claims`, `evidence`, `lineage_relationships`, `annotations`, `source_records`, and `model_runs`. `Repository.add_advertisement()`, `add_evidence()`, `add_lineage_relationship()`, `add_claim()`, and `add_source_record()` write individual workflow records.

## Proposed staging mapping

| Proposed staging concept | Existing application representation | Compatibility |
|---|---|---|
| 780 advertisements | `advertisements` row per record | Possible, but no batch CSV loader or cohort field |
| cohort identity | None | Missing |
| employer identity claim | Generic `annotations` dimension or `claims` | Possible but not enforced separately |
| vacancy authorization claim | `evidence.evidence_state` plus generic annotation | Possible, but evidence is not ground truth |
| evidence observation | `evidence` | Partial; source hashes/independence fields are missing |
| source family/instance | None | Missing |
| retrieval event | `source_records.observed_at` only | Partial; no event ID or event table |
| response hash | `source_records.content_hash` | Partial; not linked to a retrieval-event model |
| candidate lineage | `lineage_relationships` | Partial; current table does not enforce candidate-only state |
| confirmed lineage | Same `lineage_relationships` table | Unsafe without status constraints |
| provenance field source/missingness | None | Missing |

The disposable schema can represent the proposed data safely. The current application model cannot represent all provenance semantics without an adapter or versioned migration.
