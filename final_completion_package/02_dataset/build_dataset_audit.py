import csv, json, hashlib
from collections import Counter
from pathlib import Path

ROOT = Path('.')
OUT = ROOT / 'final_completion_package' / '02_dataset'
OUT.mkdir(parents=True, exist_ok=True)

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

datasets = {
    'pilot_annotations': {'type': 'jsonl', 'path': 'data/annotations/pilot.jsonl'},
    'provisional_eval_annotations': {'type': 'jsonl', 'path': 'data/annotations/job_ad_authorization_evaluation.jsonl'},
    'provisional_independent_review_v1': {'type': 'jsonl', 'path': 'data/annotations/job_ad_independent_review_v1.jsonl'},
    'table_a_780': {'type': 'csv', 'path': 'DatasetCollection/processed/table_A_advertisements.csv', 'id': 'case_id'},
    'table_b_780': {'type': 'csv', 'path': 'DatasetCollection/processed/table_B_ground_truth.csv', 'id': 'case_id'},
    'table_c_snapshot_780': {'type': 'csv', 'path': 'DatasetCollection/processed/table_C_evidence_records.csv', 'id': 'case_id'},
    'stage4e_evidence_780': {'type': 'csv', 'path': 'DatasetCollection/processed/stage4e_evidence_records.csv', 'id': 'case_id'},
    'stage4f_expansion_2200': {'type': 'csv', 'path': 'DatasetCollection/processed/stage4f_expansion_records.csv', 'id': 'case_id'},
    'stripe_cohort_pkg': {'type': 'csv', 'path': 'DatasetCollection/final_research_package/stripe_cohort.csv', 'id': 'case_id'},
    'stage4f_cohort_pkg': {'type': 'csv', 'path': 'DatasetCollection/final_research_package/stage4f_expansion_cohort.csv', 'id': 'case_id'},
    'unified_proposed_pkg': {'type': 'csv', 'path': 'DatasetCollection/final_research_package/unified_proposed_dataset.csv', 'id': 'case_id'},
    'naukri_separate_pkg': {'type': 'csv', 'path': 'DatasetCollection/final_research_package/naukri_separate_cohort.csv', 'id': 'case_id'},
    'lineage_candidates_21': {'type': 'csv', 'path': 'DatasetCollection/processed/vacancyguard_table_d_lineage_candidates.csv', 'id': 'lineage_group_id'},
    'stripe_pair_review_207': {'type': 'csv', 'path': 'DatasetCollection/processed/stage5b_lineage_pair_review.csv', 'id': 'pair_id'},
    'stage4f_lineage_candidates': {'type': 'csv', 'path': 'DatasetCollection/processed/stage4f_lineage_candidates.csv', 'id': 'candidate_id'},
    'synthetic_benchmark_v1': {'type': 'jsonl', 'path': 'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl'},
}

manifest = {'generated_utc': __import__('datetime').datetime.utcnow().isoformat() + 'Z', 'datasets': {}, 'notes': []}
for name, spec in datasets.items():
    p = Path(spec['path'])
    info = {'name': name, 'path': spec['path'], 'exists': p.exists()}
    if p.exists():
        info['sha256'] = sha256(p)
        info['bytes'] = p.stat().st_size
        if spec['type'] == 'csv':
            with open(p, newline='', encoding='utf-8', errors='replace') as f:
                r = csv.DictReader(f)
                rows = list(r)
            info['records'] = len(rows)
            info['columns'] = r.fieldnames or []
            idc = spec.get('id')
            if idc and rows and idc in rows[0]:
                vals = [row.get(idc) for row in rows]
                info['unique_ids'] = len(set(vals))
                info['duplicate_ids'] = len(vals) - len(set(vals))
            for col in ['cohort_id','source_family_id','ats_platform','employer_id','employer_identity_label','vacancy_authorization_label','fraud_outcome_label','evidence_state','source_independence_status','vacancy_status_observation','adjudication_status','lineage_review_status','source_relationship','reviewer_decision','stage','platform_type']:
                if col in (r.fieldnames or []):
                    info.setdefault('distributions', {})[col] = dict(Counter((row.get(col) or '') for row in rows).most_common(15))
        else:
            rows = []
            with open(p, encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
            info['records'] = len(rows)
            keys = set()
            for row in rows[:10]:
                if isinstance(row, dict):
                    keys.update(row.keys())
            info['sample_keys'] = sorted(keys)
            if rows and isinstance(rows[0], dict):
                for col in ['authorization_label','employer_identity','fraud_outcome','label','split','synthetic','partition']:
                    if col in rows[0]:
                        info.setdefault('distributions', {})[col] = dict(Counter(str(r.get(col, '')) for r in rows).most_common(15))
    manifest['datasets'][name] = info

def load_ids(path, col):
    p = Path(path)
    ids = set()
    if not p.exists():
        return ids
    with open(p, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            v = row.get(col)
            if v:
                ids.add(v)
    return ids

stripe_ids = load_ids('DatasetCollection/final_research_package/stripe_cohort.csv', 'case_id')
exp_ids = load_ids('DatasetCollection/final_research_package/stage4f_expansion_cohort.csv', 'case_id')
unified_ids = load_ids('DatasetCollection/final_research_package/unified_proposed_dataset.csv', 'case_id')
naukri_ids = load_ids('DatasetCollection/final_research_package/naukri_separate_cohort.csv', 'case_id')
table_a_ids = load_ids('DatasetCollection/processed/table_A_advertisements.csv', 'case_id')
stage4f_ids = load_ids('DatasetCollection/processed/stage4f_expansion_records.csv', 'case_id')
manifest['overlaps'] = {
    'stripe_vs_expansion_case_id_overlap': len(stripe_ids & exp_ids),
    'stripe_vs_stage4f_processed_overlap': len(stripe_ids & stage4f_ids),
    'expansion_pkg_vs_processed_overlap': len(exp_ids & stage4f_ids),
    'stripe_in_unified': len(stripe_ids & unified_ids),
    'expansion_in_unified': len(exp_ids & unified_ids),
    'naukri_vs_unified_overlap': len(naukri_ids & unified_ids),
    'naukri_vs_stripe_overlap': len(naukri_ids & stripe_ids),
    'naukri_vs_expansion_overlap': len(naukri_ids & exp_ids),
    'table_a_vs_stripe_pkg_overlap': len(table_a_ids & stripe_ids),
    'counts': {'stripe': len(stripe_ids), 'expansion_pkg': len(exp_ids), 'expansion_processed': len(stage4f_ids), 'unified': len(unified_ids), 'naukri': len(naukri_ids), 'table_a': len(table_a_ids)}
}

with open(OUT / 'dataset_manifest.json', 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)
print(json.dumps(manifest['overlaps'], indent=2))
