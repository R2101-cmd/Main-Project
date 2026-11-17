# Annotation quality audit

Audit date: 2026-10-22.

## Provenance categories

| Category | Count | Interpretation |
|---|---:|---|
| Original pilot records | 4 | Single-reviewer records with written rationale |
| Provisional 145-record records | 145 | Labels generated from collected evidence and not independently adjudicated |
| Provisional review subset | 31 | One protocol-based review pass; no second reviewer or agreement statistic |
| Human-adjudicated records | 0 | None present |

## Validation findings

- Stable IDs are present in the JSONL artifacts.
- Source URLs and evidence IDs are present, but source snapshots are not collected for the workbook records.
- Collection timestamps exist for the generated records, but many publication/deadline dates remain unknown.
- The 31-record subset has 29 groups because two repost pairs are retained as shared groups.
- Authorization labels are valid values, but 19 of 31 provisional review labels are unresolved and none are contradicted.
- The 145-record artifact has 12 supported and 133 unresolved authorization labels; this imbalance prevents a useful fraud classifier.
- The current evidence-derived benchmark has a circularity risk: the same evidence used by E4/E5 informed provisional labels.

## Examples requiring care

- JA003/JA004 and JA012/JA013 are repost families and must remain group-bound.
- JA004 being closed is an application-status observation, not affirmative contradiction.
- Official-source records JA039–JA045 support a source-level vacancy observation, but final fraud outcomes remain unresolved.

## Required remediation

A second reviewer should independently review a fixed subset without seeing system predictions. Disagreements should be adjudicated, exact source records or permitted snapshots retained, and the final benchmark should carry reviewer IDs, timestamps, rationale, and annotation provenance.
