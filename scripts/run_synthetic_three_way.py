import csv, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ml.text_classifier import TextBaseline
from src.aggregation.rules import naive, lineage_aware

PKG = ROOT / 'final_completion_package' / '06_stage6_evaluation' / 'synthetic_three_way'
PKG.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat()

def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')

rows = [json.loads(l) for l in open(ROOT/'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl', encoding='utf-8') if l.strip()]
labels_order = ['supported', 'contradicted', 'unresolved']

def text_features(r):
    parts = [r.get('text','') or '', r.get('job_title','') or '', r.get('employer_name','') or '', r.get('location','') or '', r.get('salary_text','') or '']
    return '\n'.join(p for p in parts if p)

train = [r for r in rows if r.get('partition') == 'train']
train_texts = [text_features(r) for r in train]
train_y = [r.get('authorization_label') for r in train]
text_model = TextBaseline.train(train_texts, train_y, seed=20261022)

def ordinary_pred(evidence):
    # count every evidence appearance independently (ignore lineage dependence)
    ev = [dict(e) for e in evidence]
    return naive(ev).state

def lineage_pred(evidence):
    ev = [dict(e) for e in evidence]
    groups = {e.get('lineage_group') for e in ev if e.get('lineage_group')}
    # consolidate repeated appearances within same known lineage_group
    return lineage_aware(ev, dependent_group_keys=groups).state

pred_rows = []
for r in rows:
    ev = r.get('evidence') or []
    ta = text_model.predict(text_features(r))['label']
    ob = ordinary_pred(ev)
    lb = lineage_pred(ev)
    ref = r.get('authorization_label')
    # false assurance: predicted supported when reference contradicted
    pred_rows.append({
        'id': r.get('id'),
        'partition': r.get('partition'),
        'reference_label': ref,
        'text_only_prediction': ta,
        'ordinary_aggregation_prediction': ob,
        'lineage_aware_prediction': lb,
        'text_only_correct': ta == ref,
        'ordinary_correct': ob == ref,
        'lineage_aware_correct': lb == ref,
        'evidence_count': len(ev),
        'independent_group_count_ordinary': len(ev),
        'independent_group_count_lineage': len({(e.get('lineage_group') or e.get('id') or i) for i,e in enumerate(ev)}),
        'text_false_assurance': ta == 'supported' and ref == 'contradicted',
        'ordinary_false_assurance': ob == 'supported' and ref == 'contradicted',
        'lineage_false_assurance': lb == 'supported' and ref == 'contradicted',
        'text_unresolved': ta == 'unresolved',
        'ordinary_unresolved': ob == 'unresolved',
        'lineage_unresolved': lb == 'unresolved',
    })

# metrics helpers
def metrics_for(method_key, subset):
    y_true = [r['reference_label'] for r in subset]
    y_pred = [r[method_key] for r in subset]
    total = len(subset)
    correct = sum(1 for a,b in zip(y_true,y_pred) if a==b)
    acc = correct/total if total else None
    cm = {t: {p: 0 for p in labels_order} for t in labels_order}
    for t,p in zip(y_true,y_pred):
        cm[t][p] = cm[t].get(p,0)+1
    per = {}
    f1s=[]
    for lab in labels_order:
        tp = cm[lab][lab]
        fp = sum(cm[t][lab] for t in labels_order if t!=lab)
        fn = sum(cm[lab][p] for p in labels_order if p!=lab)
        prec = tp/(tp+fp) if (tp+fp) else 0.0
        rec = tp/(tp+fn) if (tp+fn) else 0.0
        f1 = 2*prec*rec/(prec+rec) if (prec+rec) else 0.0
        per[lab] = {'precision': prec, 'recall': rec, 'f1': f1, 'support': sum(cm[lab].values())}
        f1s.append(f1)
    fa_num = sum(1 for t,p in zip(y_true,y_pred) if p=='supported' and t=='contradicted')
    fa_den = sum(1 for t in y_true if t=='contradicted')
    unresolved_rate = sum(1 for p in y_pred if p=='unresolved')/total if total else None
    coverage = sum(1 for p in y_pred if p!='unresolved')/total if total else None
    return {
        'n': total,
        'accuracy': acc,
        'macro_f1': sum(f1s)/len(f1s) if f1s else None,
        'confusion_matrix': cm,
        'per_class': per,
        'false_assurance_numerator': fa_num,
        'false_assurance_denominator': fa_den,
        'false_assurance_rate': (fa_num/fa_den if fa_den else None),
        'unresolved_rate': unresolved_rate,
        'coverage': coverage,
        'correct': correct,
        'errors': total-correct,
    }

subsets = {
    'all_cases': pred_rows,
    'train': [r for r in pred_rows if r['partition']=='train'],
    'validation': [r for r in pred_rows if r['partition']=='validation'],
    'test': [r for r in pred_rows if r['partition']=='test'],
}
methods = {
    'A_text_only': 'text_only_prediction',
    'B_ordinary_aggregation': 'ordinary_aggregation_prediction',
    'C_lineage_aware_aggregation': 'lineage_aware_prediction',
}
all_metrics = {}
for sname, subset in subsets.items():
    all_metrics[sname] = {}
    for mname, key in methods.items():
        all_metrics[sname][mname] = metrics_for(key, subset)

# comparison/error analysis
def case_compare(r):
    ref=r['reference_label']; a=r['text_only_prediction']; b=r['ordinary_aggregation_prediction']; c=r['lineage_aware_prediction']
    tags=[]
    if c==ref and b!=ref: tags.append('ordinary_wrong_lineage_correct')
    if c==ref and a!=ref: tags.append('text_wrong_lineage_correct')
    if c!=ref and b==ref: tags.append('lineage_wrong_ordinary_correct')
    if r['lineage_false_assurance']==False and r['ordinary_false_assurance']==True: tags.append('lineage_avoided_false_assurance_vs_ordinary')
    if r['lineage_false_assurance']==True and r['ordinary_false_assurance']==False: tags.append('lineage_introduced_false_assurance_vs_ordinary')
    if a!=ref and b!=ref and c!=ref: tags.append('all_wrong')
    if a==ref and b==ref and c==ref: tags.append('all_correct')
    if a=='unresolved' and b=='unresolved' and c=='unresolved': tags.append('all_unresolved')
    return '|'.join(tags)

for r in pred_rows:
    r['comparison_tags'] = case_compare(r)

# write outputs
pred_fields = ['id','partition','reference_label','text_only_prediction','ordinary_aggregation_prediction','lineage_aware_prediction','text_only_correct','ordinary_correct','lineage_aware_correct','evidence_count','independent_group_count_ordinary','independent_group_count_lineage','text_false_assurance','ordinary_false_assurance','lineage_false_assurance','text_unresolved','ordinary_unresolved','lineage_unresolved','comparison_tags']
with open(PKG/'per_case_predictions.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f, fieldnames=pred_fields); w.writeheader(); w.writerows(pred_rows)

# confusion matrices
for sname, subset in subsets.items():
    for mname, key in methods.items():
        m = metrics_for(key, subset)
        cm = m['confusion_matrix']
        p = PKG/'confusion_matrices'/f'{sname}__{mname}.csv'
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p,'w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f); w.writerow(['true\\pred']+labels_order)
            for t in labels_order: w.writerow([t]+[cm[t][p_] for p_ in labels_order])

# metrics comparison csv
mrows=[]
for sname in ['all_cases','test']:
    for mname in methods:
        m=all_metrics[sname][mname]
        mrows.append({
            'subset': sname,'approach': mname,'n': m['n'],'accuracy': m['accuracy'],'macro_f1': m['macro_f1'],
            'false_assurance_numerator': m['false_assurance_numerator'],'false_assurance_denominator': m['false_assurance_denominator'],'false_assurance_rate': m['false_assurance_rate'],
            'unresolved_rate': m['unresolved_rate'],'coverage': m['coverage'],'correct': m['correct'],'errors': m['errors']
        })
with open(PKG/'metrics_comparison.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f, fieldnames=list(mrows[0].keys())); w.writeheader(); w.writerows(mrows)

# false assurance comparison
fa_rows=[]
for sname in ['all_cases','test']:
    for mname in methods:
        m=all_metrics[sname][mname]
        fa_rows.append({'subset':sname,'approach':mname,'numerator':m['false_assurance_numerator'],'denominator':m['false_assurance_denominator'],'rate':m['false_assurance_rate']})
with open(PKG/'false_assurance_comparison.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f, fieldnames=list(fa_rows[0].keys())); w.writeheader(); w.writerows(fa_rows)

# unresolved comparison
ur_rows=[]
for sname in ['all_cases','test']:
    for mname in methods:
        m=all_metrics[sname][mname]
        ur_rows.append({'subset':sname,'approach':mname,'unresolved_rate':m['unresolved_rate'],'coverage':m['coverage']})
with open(PKG/'unresolved_decision_comparison.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f, fieldnames=list(ur_rows[0].keys())); w.writeheader(); w.writerows(ur_rows)

# error analysis
err = [r for r in pred_rows if not (r['text_only_correct'] and r['ordinary_correct'] and r['lineage_aware_correct'])]
with open(PKG/'error_analysis.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f, fieldnames=pred_fields); w.writeheader(); w.writerows(err)

summary = {
    'generated_utc': NOW,
    'benchmark': 'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl',
    'records_total': len(rows),
    'partitions': dict(Counter(r.get('partition') for r in rows)),
    'labels': dict(Counter(r.get('authorization_label') for r in rows)),
    'approaches': {
        'A_text_only': 'TF-IDF + LogisticRegression trained on train-partition text/metadata fields only (seed=20261022), no external authorization/lineage features.',
        'B_ordinary_aggregation': 'Naive evidence-state aggregation counting every evidence appearance independently (ignores lineage-group dependence).',
        'C_lineage_aware_aggregation': 'Lineage-aware aggregation consolidating repeated evidence appearances within the same known lineage_group (dependent group keys from evidence.lineage_group).'
    },
    'identical_cases_and_rules': True,
    'metrics': all_metrics,
    'notes': [
        'Synthetic benchmark only; NOT real-world validation and NOT proof of hypothesis.',
        'False assurance defined as prediction == supported when reference_label == contradicted (numerator/denominator reported).',
        'Train partition used only to fit text model; aggregation methods are rule-based on provided evidence.'
    ],
    'reproducibility': {
        'random_seed': 20261022,
        'train_partition_records': len(train),
        'script': 'scripts/run_synthetic_three_way.py',
        'python_dependencies': ['scikit-learn (TF-IDF, LogisticRegression)', 'project src.ml.text_classifier', 'project src.aggregation.rules']
    }
}
write_json(PKG/'synthetic_experiment_summary.json', summary)
# also update top-level synthetic_results.json to point to this
write_json(ROOT/'final_completion_package/06_stage6_evaluation/synthetic_results.json', {
    'generated_utc': NOW,
    'status': 'completed_controlled_synthetic_three_way',
    'benchmark_path': 'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl',
    'records': 60,
    'distribution': {'supported':20,'contradicted':20,'unresolved':20},
    'seed': 20261022,
    'outputs_dir': 'final_completion_package/06_stage6_evaluation/synthetic_three_way/',
    'real_world_validation': False
})
# copy key files upward for convenience
for name in ['metrics_comparison.csv','per_case_predictions.csv','false_assurance_comparison.csv','unresolved_decision_comparison.csv','error_analysis.csv','synthetic_experiment_summary.json']:
    (ROOT/'final_completion_package/06_stage6_evaluation'/name).write_bytes((PKG/name).read_bytes())

print(json.dumps({'all_accuracy': {k: all_metrics['all_cases'][k]['accuracy'] for k in methods}, 'all_false_assurance': {k: all_metrics['all_cases'][k]['false_assurance_rate'] for k in methods}}, indent=2))
