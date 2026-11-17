import csv, json, sys
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ml.text_classifier import TextBaseline
from src.aggregation.rules import naive, lineage_aware

SRC = ROOT / 'research-data/phase2_v1/synthetic/synthetic_benchmark_extended_v1.jsonl'
OUT = ROOT / 'final_completion_package' / 'automated_mode' / 'extended_synthetic_three_way'
OUT.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat()

rows = [json.loads(l) for l in open(SRC, encoding='utf-8') if l.strip()]
labels_order = ['supported', 'contradicted', 'unresolved']

def text_features(r):
    return '\n'.join(p for p in [r.get('text',''), r.get('job_title',''), r.get('employer_name',''), r.get('location','')] if p)

# train on all as controlled demo? better split deterministically: first half train, rest test by index for reproducibility (all synthetic)
split = int(len(rows)*0.6)
train, test = rows[:split], rows[split:]
model = TextBaseline.train([text_features(r) for r in train], [r.get('authorization_label') for r in train], seed=20261114)

def ordinary_pred(ev): return naive([dict(e) for e in ev]).state
def lineage_pred(ev):
    ev=[dict(e) for e in ev]
    groups={e.get('lineage_group') for e in ev if e.get('lineage_group')}
    return lineage_aware(ev, dependent_group_keys=groups).state

pred_rows=[]
for r in rows:
    ev=r.get('evidence') or []
    ta=model.predict(text_features(r))['label']
    ob=ordinary_pred(ev); lb=lineage_pred(ev); ref=r.get('authorization_label')
    pred_rows.append({'id':r.get('id'),'set':'train' if r in train else 'test','reference_label':ref,
        'text_only_prediction':ta,'ordinary_aggregation_prediction':ob,'lineage_aware_prediction':lb,
        'text_only_correct':ta==ref,'ordinary_correct':ob==ref,'lineage_aware_correct':lb==ref,
        'evidence_count':len(ev),
        'text_false_assurance':ta=='supported' and ref=='contradicted',
        'ordinary_false_assurance':ob=='supported' and ref=='contradicted',
        'lineage_false_assurance':lb=='supported' and ref=='contradicted'})

def metrics_for(key, subset):
    y_true=[r['reference_label'] for r in subset]; y_pred=[r[key] for r in subset]; total=len(subset)
    cm={t:{p:0 for p in labels_order} for t in labels_order}
    for t,p in zip(y_true,y_pred): cm[t][p]+=1
    per={}; f1s=[]
    for lab in labels_order:
        tp=cm[lab][lab]; fp=sum(cm[t][lab] for t in labels_order if t!=lab); fn=sum(cm[lab][p] for p in labels_order if p!=lab)
        prec=tp/(tp+fp) if (tp+fp) else 0.0; rec=tp/(tp+fn) if (tp+fn) else 0.0
        f1=2*prec*rec/(prec+rec) if (prec+rec) else 0.0; per[lab]={'precision':prec,'recall':rec,'f1':f1,'support':sum(cm[lab].values())}; f1s.append(f1)
    fa_num=sum(1 for t,p in zip(y_true,y_pred) if p=='supported' and t=='contradicted'); fa_den=sum(1 for t in y_true if t=='contradicted')
    correct=sum(1 for t,p in zip(y_true,y_pred) if t==p)
    return {'n':total,'accuracy':correct/total if total else None,'macro_f1':sum(f1s)/len(f1s),'confusion_matrix':cm,'per_class':per,
            'false_assurance_numerator':fa_num,'false_assurance_denominator':fa_den,'false_assurance_rate':(fa_num/fa_den if fa_den else None),
            'unresolved_rate':sum(1 for p in y_pred if p=='unresolved')/total if total else None}

methods={'A_text_only':'text_only_prediction','B_ordinary_aggregation':'ordinary_aggregation_prediction','C_lineage_aware_aggregation':'lineage_aware_prediction'}
subsets={'all':pred_rows,'test':test and [r for r in pred_rows if r['set']=='test'] or []}
if not subsets['test']: subsets['test']=pred_rows
res={s:{m:metrics_for(k,sub) for m,k in methods.items()} for s,sub in subsets.items()}

with open(OUT/'per_case_predictions.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(pred_rows[0].keys())); w.writeheader(); w.writerows(pred_rows)
for sname, sub in subsets.items():
    for mname, key in methods.items():
        cm=res[sname][mname]['confusion_matrix']; p=OUT/'confusion_matrices'/f'{sname}__{mname}.csv'; p.parent.mkdir(parents=True, exist_ok=True)
        with open(p,'w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f); w.writerow(['true\\pred']+labels_order); [w.writerow([t]+[cm[t][p_] for p_ in labels_order]) for t in labels_order]
mrows=[]
for sname in ['all','test']:
    for mname in methods:
        m=res[sname][mname]; mrows.append({'subset':sname,'approach':mname,'n':m['n'],'accuracy':m['accuracy'],'macro_f1':m['macro_f1'],'false_assurance_numerator':m['false_assurance_numerator'],'false_assurance_denominator':m['false_assurance_denominator'],'false_assurance_rate':m['false_assurance_rate'],'unresolved_rate':m['unresolved_rate']})
with open(OUT/'metrics_comparison.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(mrows[0].keys())); w.writeheader(); w.writerows(mrows)
summary={'generated_utc':NOW,'benchmark':str(SRC.relative_to(ROOT)),'records':len(rows),'synthetic':True,'not_real_world_ground_truth':True,'scenarios':'source dependence, copied evidence, contradictory evidence, unavailable sources, unknown lineage, independent support','results':res,'reproducibility':{'seed':20261114,'split':'first 60% train, rest test (deterministic order)','script':'scripts/run_extended_synthetic_three_way.py'}}
with open(OUT/'summary.json','w',encoding='utf-8') as f: json.dump(summary,f,indent=2)
print(json.dumps({s:{m:res[s][m]['accuracy'] for m in methods} for s in res}, indent=2))
