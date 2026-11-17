import json
from pathlib import Path

result_path = Path("artifacts/experiments/research_v1/aggregate_metrics.json")
out_path = Path("docs/research_evaluation_report_v1.md")
r = json.loads(result_path.read_text(encoding="utf-8"))

def metric(name, key):
    m = r["methods"][name]["classification"]
    if key == "macro_f1":
        return f"{m['macro']['f1']:.3f}"
    if key == "weighted_f1":
        return f"{m['weighted']['f1']:.3f}"
    return f"{m.get(key, 0):.3f}"

lines = [
    "# Research evaluation report v1", "", "## 1. Research objective", "",
    "This report evaluates vacancy authorization verification, not universal fake-job detection or final fraud outcomes.", "",
    "## 2. Research question and hypotheses", "",
    "Does lineage-aware aggregation improve vacancy authorization verification compared with text-only and ordinary evidence aggregation when advertisements are reposted or evidence is incomplete? The primary hypothesis is a reduction in false assurance.", "",
    "## 3. Architecture", "",
    "The system contains ingestion/extraction, claim-level evidence collection, SQLite persistence, candidate lineage similarity, naive and lineage-aware aggregation, abstention policy, TF-IDF/logistic-regression text baseline, and evaluation utilities.", "",
    "## 4. Dataset and annotation status", "",
    f"The evaluated artifact contains **{r['n']} records**, **{r['independent_vacancy_groups']} groups**, and **{r['test_records']} test records** across **{r['test_independent_vacancy_groups']} test groups**. The status is `{r['research_validity']}`. The provisional reference labels contain 12 supported and 19 unresolved records; no contradicted records.", "",
    "## 5. Annotation protocol", "",
    "Labels were assigned with the v2 protocol rules: direct role-specific employer/institutional evidence can support authorization; third-party-only, stale, inaccessible, or insufficient evidence remains unresolved; absence from a careers page is not contradiction. The current set has one protocol-based reviewer and no second-reviewer agreement or adjudication.", "",
    "## 6. Lineage methodology", "",
    "Lineage-aware aggregation consolidates only explicitly supplied dependent lineage keys. Text similarity, shared URLs, and shared contact details are candidate signals and require review. No source consolidation occurred in this test set.", "",
    "## 7. Leakage prevention", "",
    f"The split contains {r['partition_sizes'].get('train', 0)} training and {r['partition_sizes'].get('test', 0)} test records. Leakage groups: {len(r['leakage_groups'])}. All records from the same vacancy group remain in one partition.", "",
    "## 8. Experimental methods", "",
    "- E1: TF-IDF word unigrams/bigrams plus logistic regression, fitted on training text only.",
    "- E2: not run; the benchmark JSONL does not provide a frozen structured-feature training interface.",
    "- E3: not run; employer-context reference labels/features are not independently available.",
    "- E4: naive evidence aggregation.",
    "- E5: lineage-aware evidence aggregation.", "",
    "## 9. Results", "",
    "| Method | Accuracy | Balanced accuracy | Precision | Recall | F1 | Macro F1 | Weighted F1 |",
    "|---|---:|---:|---:|---:|---:|---:|---:|",
    f"| E1 text-only | {metric('text_only_baseline','accuracy')} | {metric('text_only_baseline','balanced_accuracy')} | {metric('text_only_baseline','precision')} | {metric('text_only_baseline','recall')} | {metric('text_only_baseline','f1')} | {metric('text_only_baseline','macro_f1')} | {metric('text_only_baseline','weighted_f1')} |",
    f"| E4 naive evidence | {metric('naive_evidence','accuracy')} | {metric('naive_evidence','balanced_accuracy')} | {metric('naive_evidence','precision')} | {metric('naive_evidence','recall')} | {metric('naive_evidence','f1')} | {metric('naive_evidence','macro_f1')} | {metric('naive_evidence','weighted_f1')} |",
    f"| E5 lineage-aware | {metric('lineage_aware_evidence','accuracy')} | {metric('lineage_aware_evidence','balanced_accuracy')} | {metric('lineage_aware_evidence','precision')} | {metric('lineage_aware_evidence','recall')} | {metric('lineage_aware_evidence','f1')} | {metric('lineage_aware_evidence','macro_f1')} | {metric('lineage_aware_evidence','weighted_f1')} |", "",
    "Confusion-matrix label order is `[contradicted, supported, unresolved]`.", "",
    f"- E1: `{r['methods']['text_only_baseline']['classification']['confusion_matrix']}`",
    f"- E4: `{r['methods']['naive_evidence']['classification']['confusion_matrix']}`",
    f"- E5: `{r['methods']['lineage_aware_evidence']['classification']['confusion_matrix']}`", "",
    "## 10. E4 versus E5 case comparison", "",
    f"{json.dumps(r['case_comparison'], indent=2)}", "",
    f"False assurance: E4 `{r['false_assurance']['E4_count']}` / {r['false_assurance']['denominator_non_supported']} non-supported cases; E5 `{r['false_assurance']['E5_count']}` / {r['false_assurance']['denominator_non_supported']}. Evidence coverage was {r['evidence_summary']['coverage']:.1%}; no source consolidation occurred.", "",
    "## 11. Error and abstention analysis", "",
    "The text baseline predicted the unresolved class for all test records, producing zero supported recall. E4 and E5 made identical decisions. Evidence methods abstained on unresolved cases; decision coverage and abstention must be read from the method-specific selective metrics in the JSON artifact, not confused with evidence coverage.", "",
    "## 12. Limitations and threats to validity", "",
    "The test set is small, has no contradicted class, and uses provisional single-reviewer labels whose provenance is tied to the collected evidence. This creates circularity risk for evidence methods. There is no inter-annotator agreement, no reviewed lineage gold standard, no fraud-outcome benchmark, and no statistically defensible superiority claim.", "",
    "## 13. Research contribution supported by results", "",
    "The implementation supports traceable evidence, unresolved outcomes, group-aware splitting, and a reproducible comparison pipeline. The current results do **not** establish that lineage-aware aggregation improves over naive aggregation.", "",
    "## 14. Conclusion and next experiments", "",
    "The finding is inconclusive. The next priority is independent double annotation of a larger fixed sample containing affirmative contradictions and reviewed repost families, followed by adjudication and a new frozen test set.", "",
    "## 15. Reproducibility", "",
    "```powershell\npython scripts\\build_independent_review.py\npython scripts\\run_research_evaluation.py\npython scripts\\render_research_report.py\npytest -q\n```", "",
    "Artifacts are saved under `artifacts/experiments/research_v1/`: aggregate metrics, predictions, split manifest, and experiment configuration.",
]
out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out_path)
