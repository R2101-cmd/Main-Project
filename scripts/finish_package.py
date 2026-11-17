import json, csv, datetime, shutil
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'final_completion_package'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

def read_json(p):
    return json.load(open(p, encoding='utf-8'))
def read_jsonl(p):
    out=[]
    with open(p, encoding='utf-8', errors='replace') as f:
        for l in f:
            l=l.strip()
            if l: out.append(json.loads(l))
    return out
def read_csv(p):
    with open(p, newline='', encoding='utf-8-sig', errors='replace') as f:
        return list(csv.DictReader(f))
def wj(p,o):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p,'w',encoding='utf-8',newline='\n') as f:
        json.dump(o,f,indent=2,ensure_ascii=False)

# 02 validation
recon = read_json(PKG/'02_dataset/dataset_reconciliation.json')
unified = read_csv(ROOT/'DatasetCollection/final_research_package/unified_proposed_dataset.csv')
ids=[r['case_id'] for r in unified]
val={
  'generated_utc': NOW,
  'checks': {
    'unified_unique_case_ids': len(ids)==len(set(ids)),
    'unified_record_count': len(unified),
    'unified_employers': len({r.get('employer_id') for r in unified if r.get('employer_id')}),
    'naukri_separate_count': len(read_csv(ROOT/'DatasetCollection/final_research_package/naukri_separate_cohort.csv')),
    'critical_missing_counts': {c: sum(1 for r in unified if not (r.get(c) or '').strip()) for c in ['case_id','cohort_id','employer_id','source_family_id']},
    'human_ground_truth_available': False,
    'confirmed_lineage_available': False,
  },
  'issues': ['No adjudicated human ground truth; no confirmed lineage relationships; proposed package remains collection/staging only.'],
  'selected_primary_verified_benchmark': None
}
wj(PKG/'02_dataset/dataset_validation.json', val)

# 05 annotations
(PKG/'05_annotations').mkdir(parents=True, exist_ok=True)
(PKG/'05_annotations/annotation_guidelines.md').write_text(
    '# Annotation guidelines (execution package)\n\n'
    '- Record evidence, not assumptions. Keep **employer identity**, **vacancy authorization**, and **fraud outcome** separate.\n'
    '- Labels: employer identity/vacancy authorization `supported|contradicted|unresolved`; fraud outcome `confirmed_legitimate|confirmed_fraudulent|unresolved` only with defensible basis.\n'
    '- Evidence states: `supported|contradicted|unverified|unavailable`. Missing/inaccessible evidence is **not** fraud or contradiction.\n'
    '- Capture per case: case/ad IDs, claims, checked official/ATS URLs, retrieval timestamps, matched/contradicted fields, source authority/lineage, reviewer decision, rationale, confidence, adjudication status (`pending_review|reviewed|disputed|adjudicated|insufficient_evidence`).\n'
    '- Require evidence references and rationale for non-unresolved decisions. Single-reviewer datasets must be marked provisional; do not claim inter-annotator agreement without independent overlapping reviews.\n'
    '- Preserve original evidence/annotations; resolve disagreements via adjudication records.\n', encoding='utf-8', newline='\n')

eval_ann = read_jsonl(ROOT/'data/annotations/job_ad_authorization_evaluation.jsonl')
queue = []
for i,r in enumerate(eval_ann,1):
    ev = r.get('evidence') or []
    states = [e.get('evidence_state') for e in ev]
    prio = 'high' if r.get('authorization_label')=='unresolved' or 'unavailable' in states or 'unverified' in states else 'medium'
    queue.append({'priority_rank': i, 'queue': 'provisional_eval_annotations', 'case_id': r.get('id') or r.get('advertisement_id',''), 'vacancy_group': r.get('vacancy_group',''), 'current_authorization_label': r.get('authorization_label',''), 'employer_identity': r.get('employer_identity',''), 'annotation_status': r.get('annotation_status',''), 'reason': f'{prio} - adjudicate employer identity, vacancy authorization, and fraud outcome with evidence references', 'review_status': 'pending_review'})
pairs = read_csv(ROOT/'DatasetCollection/processed/stage5b_lineage_pair_review.csv')
for r in pairs:
    queue.append({'priority_rank': '', 'queue': 'stripe_lineage_pair_review', 'case_id': r.get('pair_id',''), 'vacancy_group': '', 'current_authorization_label': '', 'employer_identity': '', 'annotation_status': r.get('adjudication_status','not_started'), 'reason': 'Review candidate pair relationship/direction/independence; similarity alone insufficient', 'review_status': r.get('adjudication_status','not_started')})
qfields = ['priority_rank','queue','case_id','vacancy_group','current_authorization_label','employer_identity','annotation_status','reason','review_status']
with open(PKG/'05_annotations/human_review_queue.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=qfields); w.writeheader(); w.writerows(queue)
adj = {'generated_utc': NOW, 'submitted_reviewer1_labels': 0, 'submitted_reviewer2_labels': 0, 'adjudicated_cases': 0, 'disputed_cases': 0, 'pending_cases_total': len(queue), 'status': 'no_completed_independent_adjudication', 'note': 'Inter-annotator agreement cannot be claimed; existing annotations/worksheets are provisional or blank.'}
wj(PKG/'05_annotations/adjudication_summary.json', adj)

# 06 evaluation - reference existing provisional results and record synthetic status
(PKG/'06_stage6_evaluation').mkdir(parents=True, exist_ok=True)
# copy/reference existing research_v1 outputs as provisional
src_metrics = ROOT/'artifacts/experiments/research_v1/metrics.json'
src_comp = ROOT/'artifacts/experiments/research_v1/case_comparison.csv'
src_config = ROOT/'artifacts/experiments/research_v1/config.json'
if src_metrics.exists():
    wj(PKG/'06_stage6_evaluation/provisional_research_v1_metrics.json', read_json(src_metrics))
if src_comp.exists():
    shutil.copy2(src_comp, PKG/'06_stage6_evaluation/provisional_case_level_comparison.csv')
if src_config.exists():
    wj(PKG/'06_stage6_evaluation/provisional_research_v1_config.json', read_json(src_config))
# metrics comparison summary
prov = read_json(src_metrics) if src_metrics.exists() else {}
methods = prov.get('methods', {}) if isinstance(prov, dict) else {}
rows=[]
for m,vals in methods.items():
    if isinstance(vals, dict):
        rows.append({'approach': m, 'dataset': 'provisional_independent_review_v1_exploratory', **{k:v for k,v in vals.items() if not isinstance(v,(dict,list))}})
mfields=sorted({k for r in rows for k in r.keys()}) if rows else ['approach','dataset']
with open(PKG/'06_stage6_evaluation/metrics_comparison.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=mfields); w.writeheader(); w.writerows(rows)
# false assurance and synthetic status
fa = {'generated_utc': NOW, 'definition': 'False assurance = system returns supported authorization for a case whose independently adjudicated reference label is contradicted (or otherwise non-supported per frozen protocol).', 'real_data': {'status': 'BLOCKED', 'reason': 'No independently adjudicated contradicted/supported authorization ground truth; provisional single-reviewer labels are not defensible for hypothesis proof.', 'numerator': None, 'denominator': None, 'rate': None}, 'synthetic_data': {'status': 'AVAILABLE_FOR_CONTROLLED_CHECKS', 'benchmark': 'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl', 'records': 60, 'seed': 20261022, 'note': 'Not real-world ground truth; use to validate implementation behavior only.'}}
wj(PKG/'06_stage6_evaluation/false_assurance_analysis.json', fa)
wj(PKG/'06_stage6_evaluation/synthetic_results.json', {'generated_utc': NOW, 'status': 'not_executed_as_separate_stage6_runner', 'reason': 'No dedicated three-approach Stage 6 script found for synthetic schema in this pass; benchmark manifest/records present and pytest suite passed.', 'benchmark_path': 'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl', 'records': 60, 'distribution_expected': {'supported':20,'contradicted':20,'unresolved':20}})
with open(PKG/'06_stage6_evaluation/evaluation_report.md','w',encoding='utf-8',newline='\n') as f:
    f.write('# Stage 6 evaluation report\n\n')
    f.write(f'Generated: {NOW}\n\n')
    f.write('## Real-data evaluation\n- **BLOCKED for defensible hypothesis testing.** No adjudicated human ground truth or confirmed lineage benchmark is available; existing provisional single-reviewer results (`artifacts/experiments/research_v1`) are exploratory only and must not be interpreted as proof.\n- Included: provisional metrics/config/case comparison copies for transparency.\n\n')
    f.write('## Synthetic benchmark\n- 60-record synthetic benchmark (20/20/20, seed 20261022) is available for controlled implementation checks, not real-world ground truth. Full three-approach synthetic runner output was not produced in this execution pass.\n\n')
    f.write('## False assurance\n- Defined and reported as blocked for real data (numerator/denominator unavailable without adjudicated labels).\n\n')
    f.write('## Limitations\n- Leakage-safe employer/lineage-group splits and fair three-approach comparison on real data require adjudicated labels, confirmed lineage, and sufficient independent groups.\n')
print('eval ok')
