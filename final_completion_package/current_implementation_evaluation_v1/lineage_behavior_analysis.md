# Lineage behavior analysis

C raw is the production aggregation result. C live is that result passed through the current app policy and is the deployment-facing authorization outcome. The two should not be conflated.

| Synthetic input key | Scenario | Expected design outcome | B ordinary | C raw | C live |
|---|---|---|---|---|---|
| `input-0100` | copied_repost_cluster | unresolved | supported | supported | unresolved |
| `input-0105` | unknown_lineage_support | unresolved | supported | unresolved | unresolved |
| `input-0110` | unadjudicated_candidate_lineage | unresolved | supported | unresolved | unresolved |
| `input-0115` | conflicting_official_records | unresolved | contradicted | contradicted | unresolved |
| `input-0120` | employer_identity_only | unresolved | unresolved | unresolved | unresolved |
| `input-0125` | similar_role_different_vacancy | unresolved | unresolved | unresolved | unresolved |
| `input-0130` | stale_source_dates | unresolved | supported | supported | unresolved |
| `input-0135` | missing_source_dates | unresolved | supported | supported | unresolved |
| `input-0140` | unavailable_source | unresolved | unresolved | unresolved | unresolved |
| `input-0145` | incomplete_insufficient_evidence | unresolved | unresolved | unresolved | unresolved |

Adjudicated copied-derived URLs in one group consolidate to one effective group. Raw C may return `supported` from that single group, but the live decision remains unresolved because the independent-group count is zero. Unknown, missing and unadjudicated candidate lineage are excluded by raw C; the live policy also abstains below two qualifying independent groups. In conflicting evidence, raw `naive()`/lineage aggregation favors the contradiction state under its existing rule, while the live policy returns unresolved when eligible support and contradiction coexist. Stale evidence may still yield a raw aggregate state, but freshness gates prevent current authorization. An employer identity match does not establish vacancy correspondence.

The live policy correctly enforces the two-independent-source minimum on the authored examples. The score is not evidence of external accuracy: the expected outcomes are expressly built from the same evidence conditions the policy checks. Synthetic records do not establish actual source authority.
