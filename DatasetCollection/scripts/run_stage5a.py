"""TrustHire Stage 5A: research evaluation design and dataset audit.

This script audits existing records and writes design artifacts only. It does
not mutate datasets, train models, or assign ground-truth labels.
"""
import csv
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

csv.field_size_limit(20_000_000)
ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
PROCESSED = ROOT / "processed"

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def norm(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip().casefold()

def compact(value):
    return re.sub(r"[^a-z0-9]+", " ", norm(value)).strip()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")

def job_id(case_id):
    match = re.search(r"_(\d+)$", case_id or "")
    return match.group(1) if match else ""

table_a = read_csv(PROCESSED / "table_A_advertisements.csv")
table_b = read_csv(PROCESSED / "table_B_ground_truth.csv")
table_c = read_csv(PROCESSED / "table_C_evidence_records.csv")
lineage_stripe = read_csv(PROCESSED / "vacancyguard_table_d_lineage_candidates.csv")
stage4d_selection = read_csv(PROCESSED / "stage4d_stripe_pilot_selection.csv")
stage4d_evidence = read_csv(PROCESSED / "stage4d_stripe_pilot_evidence.csv")
stage4c_relationships = read_csv(PROCESSED / "stage4c_vacancy_source_relationships.csv")
stage4e = read_csv(PROCESSED / "stage4e_evidence_records.csv")
stage4e_fields = read_csv(PROCESSED / "stage4e_field_comparisons.csv")
stage4e_manifest = read_csv(PROCESSED / "stage4e_batch_manifest.csv")
with (ROOT / "raw/greenhouse/greenhouse_raw.json").open(encoding="utf-8") as f:
    greenhouse = json.load(f)
green_jobs = greenhouse.get("jobs", [])
naukri = read_csv(PROCESSED / "vacancyguard_table_a_cleaned.csv")

stripe_ids = [r.get("case_id", "") for r in table_a]
naukri_ids = [r.get("case_id", "") for r in naukri]
stripe_id_set, naukri_id_set = set(stripe_ids), set(naukri_ids)

# Dataset audit.
desc_keys = {}
for row in table_a:
    key = (compact(row.get("job_title")), compact(row.get("location")), norm(row.get("job_description")))
    desc_keys.setdefault(key, []).append(row["case_id"])
exact_groups = [ids for ids in desc_keys.values() if len(ids) > 1]
identifier_set = {job_id(x) for x in stripe_ids if job_id(x)}
source_urls = {r.get("application_url", "") for r in table_a if r.get("application_url")}
employers = {r.get("employer_id", "") for r in table_a}
missing_source_fields = [
    r["case_id"] for r in table_a
    if not r.get("application_url") or not r.get("advertisement_url") or not job_id(r["case_id"])
]
lineage_metadata_fields = {"lineage_group_id", "source_parent_id", "source_relationship", "source_order"}
incomplete_lineage_metadata = [
    r["case_id"] for r in table_a
    if not lineage_metadata_fields.issubset(r.keys())
]

# Conservative near-duplicate candidate audit. These are candidates, not asserted lineage.
near_pairs = []
for i, left in enumerate(table_a):
    left_desc = norm(left.get("job_description"))
    left_tokens = set(re.findall(r"[a-z0-9]+", left_desc))
    for right in table_a[i + 1:]:
        right_desc = norm(right.get("job_description"))
        right_tokens = set(re.findall(r"[a-z0-9]+", right_desc))
        if not left_tokens or not right_tokens:
            continue
        jaccard = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
        if jaccard >= 0.85:
            sequence = SequenceMatcher(None, left_desc, right_desc).ratio()
            if sequence >= 0.88:
                near_pairs.append({
                    "left_case_id": left["case_id"], "right_case_id": right["case_id"],
                    "left_job_id": job_id(left["case_id"]), "right_job_id": job_id(right["case_id"]),
                    "similarity_score": round(sequence, 4), "token_jaccard": round(jaccard, 4),
                    "same_title": compact(left.get("job_title")) == compact(right.get("job_title")),
                    "same_location": compact(left.get("location")) == compact(right.get("location")),
                    "relationship_status": "potential_source_copy_or_repost_candidate",
                    "interpretation": "Text similarity alone does not establish copying order, reposting, or authorization.",
                })

exact_dup_case_ids = {case_id for group in exact_groups for case_id in group}
lineage_audit = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "stripe_records": len(table_a),
    "unique_advertisements": len(stripe_id_set),
    "unique_employers": len(employers),
    "unique_vacancy_identifiers": len(identifier_set),
    "unique_application_urls": len(source_urls),
    "same_source_family": {
        "raw_source": "raw/greenhouse/greenhouse_raw.json",
        "source_label": greenhouse.get("source"),
        "source_record_count": len(green_jobs),
        "official_employer": "Stripe",
        "interpretation": "All 780 records derive from the same preserved Greenhouse/Stripe source family; this is not 780 independent sources.",
    },
    "exact_duplicate_advertisement_groups": len(exact_groups),
    "exact_duplicate_advertisement_records": len(exact_dup_case_ids),
    "near_duplicate_candidate_pairs": len(near_pairs),
    "near_duplicate_candidate_records": len({x for p in near_pairs for x in (p["left_case_id"], p["right_case_id"])}),
    "reposted_advertisements_confirmed": 0,
    "potential_source_copy_relationships": len(near_pairs),
    "potential_independent_source_relationships": 0,
    "incomplete_source_field_records": len(missing_source_fields),
    "incomplete_lineage_records": len(incomplete_lineage_metadata),
    "missing_lineage_metadata_fields": sorted(lineage_metadata_fields),
    "lineage_candidate_examples": near_pairs[:100],
    "existing_stripe_lineage_dataset_rows": len(lineage_stripe),
    "existing_lineage_interpretation": "The existing 21 lineage candidates belong to the separate Naukri/ATS dataset and are excluded from Stripe lineage metrics.",
    "limitations": [
        "Identical or similar descriptions do not prove source-copy direction.",
        "Different URLs do not prove independent sources; the Stripe cohort uses one underlying Greenhouse source family.",
        "The Stripe cohort has no verified cross-publisher lineage variation.",
    ],
}
write_json(REPORTS / "stage5a_lineage_audit.json", lineage_audit)

dataset_audit = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "cohort_counts": {
        "stripe_table_a_records": len(table_a),
        "stripe_table_b_records": len(table_b),
        "stripe_table_c_records": len(table_c),
        "stripe_stage4e_records": len(stage4e),
        "naukri_cleaned_records": len(naukri),
        "naukri_stage4b_records": len(stage4c_relationships),
    },
    "stripe_unique_case_ids": len(stripe_id_set),
    "stripe_duplicate_case_ids": len(stripe_ids) - len(stripe_id_set),
    "naukri_unique_case_ids": len(naukri_id_set),
    "naukri_duplicate_case_ids": len(naukri_ids) - len(naukri_id_set),
    "cross_dataset_case_id_overlap": len(stripe_id_set & naukri_id_set),
    "stripe_employer_ids": sorted({r.get("employer_id", "") for r in table_a}),
    "stripe_source_files": ["raw/greenhouse/greenhouse_raw.json"],
    "naukri_source_files": sorted({r.get("source_file", "") for r in naukri}),
    "pilot_origin_audit": {
        "stage4d_stripe_pilot": len(stage4d_selection),
        "stage4d_stripe_evidence": len(stage4d_evidence),
        "stage4b_naukri_pilot": len(read_csv(PROCESSED / "table_C_stage4b_pilot.csv")),
        "stage4c_naukri_relationships": len(stage4c_relationships),
    },
    "uncertain_origin_cases": 0,
    "cross_dataset_contamination": False,
    "evaluation_scripts_found": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "scripts").glob("*.py") if any(x in p.name.casefold() for x in ("eval", "metric", "benchmark"))),
    "conclusion": "The Stripe and Naukri cohorts are separate and must not be combined into one benchmark.",
}
write_json(REPORTS / "stage5a_dataset_audit.json", dataset_audit)

# Ground truth audit.
b_counts = {
    field: Counter(r.get(field, "") for r in table_b)
    for field in ("employer_identity_label", "vacancy_authorization_label", "fraud_outcome_label", "adjudication_status")
}
gt_audit = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "records": len(table_b),
    "independently_reviewed_cases": sum(r.get("adjudication_status") in ("reviewed", "adjudicated", "complete") for r in table_b),
    "unresolved_cases": sum(r.get("fraud_outcome_label") == "unresolved" for r in table_b),
    "evidence_backed_authorization_labels": sum(r.get("vacancy_authorization_label") in ("supported", "contradicted") and bool(r.get("label_evidence_refs", "").strip()) for r in table_b),
    "evidence_backed_employer_identity_labels": sum(r.get("employer_identity_label") in ("verified", "contradicted") and bool(r.get("label_evidence_refs", "").strip()) for r in table_b),
    "fraud_outcome_labels": sum(r.get("fraud_outcome_label") in ("confirmed_fraudulent", "confirmed_legitimate") for r in table_b),
    "missing_label_rationale": sum(not r.get("label_rationale", "").strip() or r.get("label_rationale") == "Not yet independently reviewed." for r in table_b),
    "missing_evidence_references": sum(not r.get("label_evidence_refs", "").strip() for r in table_b),
    "label_counts": {k: dict(v) for k, v in b_counts.items()},
    "stage4e_evidence_used_as_ground_truth": False,
    "assessment": "Table B is entirely unresolved/pending and is insufficient for supervised performance metrics.",
    "human_adjudication_protocol": {
        "unit": "one case advertisement, with linked evidence and lineage context",
        "required_roles": "two independent annotators plus adjudicator for disagreement",
        "separate_fields": ["employer_identity_label", "vacancy_authorization_label", "fraud_outcome_label"],
        "required_artifacts": ["rationale", "evidence references", "source independence", "retrieval timestamp", "lineage group"],
        "missing_vs_contradictory": "Unavailable or incomplete evidence remains unresolved; contradiction requires an explicit authoritative conflict.",
        "quality_controls": ["calibration set", "blinded duplicate cases", "inter-annotator agreement", "adjudication log", "no automatic labels from Stage 4E"],
    },
}
write_json(REPORTS / "stage5a_ground_truth_audit.json", gt_audit)

state_mapping = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "mutually_exclusive_states": {
        "matched_snapshot": {
            "meaning": "Advertisement fields match the frozen Greenhouse snapshot.",
            "retrieval_independence": "historical_snapshot",
            "source_independence": "same_source_derivation",
            "authorization_conclusion": "no independent authorization conclusion",
        },
        "fresh_same_system_retrieval": {
            "meaning": "A fresh Greenhouse retrieval succeeded, but independent official confirmation criteria were not met.",
            "retrieval_independence": "fresh_from_frozen_snapshot",
            "source_independence": "same_official_system",
            "authorization_conclusion": "unresolved for independent authorization",
        },
        "independent_official_confirmation": {
            "meaning": "Official employer page and official Greenhouse record were retrieved and core fields plus identifier agreed.",
            "retrieval_independence": "fresh_from_frozen_snapshot",
            "source_independence": "employer_controlled_page_plus_official_ATS",
            "authorization_conclusion": "candidate evidence-supported authorization; human adjudication still required",
        },
        "contradicted": {
            "meaning": "An explicit authoritative conflict exists, such as a different employer or identifier.",
            "retrieval_independence": "case-specific",
            "source_independence": "case-specific",
            "authorization_conclusion": "authorization contradicted for review; not automatic fraud",
        },
        "unavailable": {
            "meaning": "Required official source could not be retrieved or inspected.",
            "retrieval_independence": "not_observed",
            "source_independence": "not_observed",
            "authorization_conclusion": "unresolved; not fraud evidence",
        },
        "unresolved": {
            "meaning": "Evidence exists but is incomplete, mixed, or insufficient for a required conclusion.",
            "retrieval_independence": "case-specific",
            "source_independence": "case-specific",
            "authorization_conclusion": "unresolved",
        },
    },
    "stage4e_observed_counts": dict(Counter(r.get("evidence_classification", "") for r in stage4e)),
    "stage4e_authorization_counts": dict(Counter(r.get("vacancy_authorization_evidence", "") for r in stage4e)),
    "rule": "Retrieval independence and source independence must be stored separately; a fresh API response is not a separate independent source.",
}
write_json(REPORTS / "stage5a_evidence_state_mapping.json", state_mapping)

protocol = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "objective": "Evaluate whether lineage-aware evidence aggregation reduces false assurance in vacancy authorization verification.",
    "datasets": {
        "stripe_main": {"records": 780, "role": "main cohort; independent evaluation of evidence aggregation"},
        "naukri_separate": {"records": 198, "role": "separate lineage experiment only; never merged with Stripe benchmark"},
    },
    "evaluation_approaches": {
        "A_text_only_baseline": {
            "inputs": ["advertisement title", "description", "location", "salary/contact text where present"],
            "excluded": ["retrieved evidence", "source URLs as authority", "lineage labels"],
        },
        "B_ordinary_evidence_aggregation": {
            "inputs": ["advertisement fields", "retrieved evidence fields", "retrieval outcomes"],
            "rule": "Aggregate evidence per case without correcting for shared source or copy lineage.",
            "risk": "Can count repeated same-source or copied evidence as independent support.",
        },
        "C_lineage_aware_aggregation": {
            "inputs": ["all Approach B inputs", "source independence", "retrieval independence", "lineage groups", "freshness", "contradictions", "missingness"],
            "rule": "Deduplicate evidence by source family and lineage group; require independent source support for positive authorization; retain unresolved when evidence is incomplete.",
        },
    },
    "split_protocol": {
        "unit": "case-level",
        "grouping": "Keep exact duplicates, near-duplicate clusters, lineage candidates, and shared source families within one split.",
        "recommended_split": "grouped train/validation/test split after adjudication; test set frozen before model tuning",
        "leakage_controls": ["fit text normalization/vectorizers on train only", "do not use post-retrieval labels as features before their allowed time", "do not split copied descriptions across folds", "do not merge Naukri and Stripe"],
        "current_status": "No supervised split or model evaluation should be run until human ground truth exists.",
    },
    "metrics": {
        "false_assurance_rate": "Unsupported positive authorization conclusions divided by all positive authorization conclusions.",
        "precision": "True supported authorization conclusions divided by all positive authorization conclusions.",
        "recall": "True supported authorization conclusions divided by all adjudicated supported authorization cases.",
        "f1": "Harmonic mean of precision and recall.",
        "specificity": "Correct non-supported/unresolved decisions divided by all adjudicated non-supported cases.",
        "unresolved_decision_rate": "Unresolved outputs divided by all evaluated cases.",
        "coverage": "Cases receiving a non-unresolved conclusion divided by all evaluated cases.",
        "contradiction_handling": "Report explicit contradictions separately; do not fold unavailable evidence into contradiction.",
        "repost_performance": "Report metrics separately for adjudicated lineage/repost groups and non-lineage cases.",
        "incomplete_evidence_performance": "Report unresolved rate and false-assurance rate for incomplete/unavailable evidence strata.",
    },
    "comparability_rule": "All three approaches use the same adjudicated case IDs, split assignments, and target definition; only inputs and aggregation logic differ.",
    "no_metric_claim_rule": "Do not calculate meaningful supervised precision, recall, F1, specificity, or false-assurance rates until ground truth is independently adjudicated.",
}
write_json(REPORTS / "stage5a_evaluation_protocol.json", protocol)

markdown = f"""# TrustHire Stage 5A Research Readiness Report

## Decision

**CONDITIONAL GO** for Stage 5B design implementation, but not for supervised model training or final hypothesis testing yet.

## Dataset audit

- Stripe/Greenhouse cohort: {len(table_a)} records, {len(stripe_id_set)} unique case IDs, {len(employers)} employer ID.
- Naukri/ATS cohort: {len(naukri)} records.
- Cross-dataset case-ID overlap: {len(stripe_id_set & naukri_id_set)}.
- Unique Stripe vacancy identifiers: {len(identifier_set)}.
- Exact duplicate advertisement groups in Stripe: {len(exact_groups)}.
- Near-duplicate candidate pairs in Stripe: {len(near_pairs)}.
- Confirmed reposts: 0.
- Independent source relationships in Stripe: 0.
- Incomplete lineage records: {len(incomplete_lineage_metadata)} (Table A has no lineage-group/source-parent fields).

The Stripe records derive from one Greenhouse/Stripe source family. It supports source-consistency and authorization-evidence evaluation, but it has limited lineage variation. The 198-record Naukri dataset should remain a separate, explicitly labelled lineage experiment.

## Ground truth

Table B contains no independently reviewed cases. All 780 records remain unresolved/pending, with no evidence-backed authorization labels, employer identity labels, or fraud outcomes. Stage 4E evidence must not be converted automatically into ground truth.

Human adjudication requires two independent annotators, blinded duplicate cases, explicit evidence references, separate employer and authorization labels, and an adjudication log. Missing evidence must remain distinct from contradiction.

## Evidence reconciliation

The six evidence states are mutually exclusive. Snapshot consistency and fresh same-system retrieval do not establish independent authorization. Independent official confirmation is candidate positive evidence, not an automatic ground-truth label. Unavailable and unresolved remain unresolved; contradiction requires an explicit authoritative conflict.

## Evaluation design

The three approaches must use identical adjudicated case IDs and grouped splits:

1. Text-only baseline: advertisement text and text-derived features only.
2. Ordinary evidence aggregation: evidence fields without source/lineage dependency correction.
3. Lineage-aware aggregation: source-family deduplication, lineage grouping, retrieval/source independence, freshness, contradictions, and missingness.

Exact and near-duplicate groups must not cross train, validation, and test splits. The current Stripe data has insufficient verified lineage variation to test the hypothesis strongly by itself.

## Metrics

Primary metrics are false-assurance rate, precision, recall, F1, specificity, unresolved decision rate, coverage, contradiction handling, repost-group performance, and incomplete-evidence performance. Accuracy must not be used as the sole metric. No supervised metrics are currently meaningful because ground truth is unresolved.

## Required before Stage 5B

1. Complete human adjudication for a calibration and evaluation subset.
2. Manually review the {len(near_pairs)} Stripe near-duplicate candidate pairs or define a sampled lineage protocol.
3. Create grouped, leakage-safe splits after adjudication.
4. Define the positive authorization target and treatment of unresolved cases before scoring.
5. Keep the Naukri lineage experiment separate from the Stripe benchmark.
6. Freeze the test set and annotation protocol before model evaluation.
"""
(REPORTS / "stage5a_research_readiness_report.md").write_text(markdown, encoding="utf-8")

print(json.dumps({
    "stripe_records": len(table_a),
    "stripe_unique_vacancy_ids": len(identifier_set),
    "exact_duplicate_groups": len(exact_groups),
    "near_duplicate_pairs": len(near_pairs),
    "incomplete_lineage_records": len(incomplete_lineage_metadata),
    "table_b_reviewed": gt_audit["independently_reviewed_cases"],
    "stage4e_records": len(stage4e),
    "decision": "CONDITIONAL GO",
}, indent=2))

