# Collection-readiness report

This report is a pre-collection gate. It does not collect records, assign labels, or validate the research hypothesis.

- Configuration: `config/collection_config_v1.json`
- Configuration fingerprint: `b0182d5b4bc17b20f602797806752fda53d8c41f216682540e1d2f7e26b07bee`
- Frozen baseline checked: `artifacts/experiments/research_v1_frozen`
- Overall status: **NOT COLLECTION READY**

| Requirement | Status | Reason | Corrective action |
|---|---|---|---|
| Required schema/configuration versions | ready | All required versions are explicit. |  |
| Annotation protocol version | ready | Independent annotation protocol v2 is explicit. |  |
| Fixed 30-day collection window | pending | Start/end timestamps or the named timezone are unset. | Set explicit ISO 8601 start and end timestamps with timezone, exactly 30 days apart. |
| Geography and role scope | ready | India and the defined related-role scope are explicit. |  |
| Source strata and selection procedure | ready | 4 strata have documented selection procedures. |  |
| Non-biased selection policy | ready | Selection is not based on artificial class balancing or model predictions. |  |
| Sampling seed | pending | The source-frame sampling seed is unset. | Freeze the sampling seed before collection, or document why a deterministic non-random procedure is used. |
| 100–200 vacancy-group target | ready | The target is explicitly feasibility-only. |  |
| Reviewer and adjudicator setup | pending | Reviewer setup is not operationally authorized. | Assign two distinct reviewers and an adjudicator, then explicitly authorize the setup. |
| Privacy, access, and evidence-retention decisions | pending | Required privacy or retention decisions are not complete: privacy_decision, redaction_policy, snapshot_policy, retention_decision, access_control. | Document minimization, redaction, permitted snapshots, retention, and access controls before collection. |
| Collection log | ready | Collection events will be recorded at data/collection/collection_log.jsonl. |  |
| Frozen baseline integrity | ready | Frozen artifacts match their manifest. |  |
| Operational collection authorization | pending | Collection has not been explicitly authorized by a named operator. | After all safeguards are complete, record a real approver and timestamp. |

## Interpretation

`pending` means a human or operational decision is not yet supplied. `blocked` means the supplied configuration is invalid or contradictory. Collection must not begin unless every check is `ready`.

The 100–200 vacancy-group target is a feasibility target, not a guarantee of statistical power. Reviewer identities, independent annotation, adjudication, and a new frozen test set remain human-process requirements.
