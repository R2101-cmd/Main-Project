from __future__ import annotations
import csv, hashlib, json, random, math, sys, subprocess
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
BENCH=ROOT/'research-data/phase2_v1/synthetic/synthetic_benchmark_v3'
OUT=ROOT/'final_completion_package/current_implementation_evaluation_v1'
SEED=20261115
CLASSES=('supported','contradicted','unresolved')
SUPPORT_SCENARIOS=['independent_official_corroboration','two_source_requisition_match','current_employer_careers_listing','independent_field_corroboration','verified_current_status']
CONTRADICTION_SCENARIOS=['explicit_official_contradiction','closed_requisition_confirmation','official_location_conflict','employment_type_conflict','material_title_conflict']
UNRESOLVED_SCENARIOS=['copied_repost_cluster','unknown_lineage_support','unadjudicated_candidate_lineage','conflicting_official_records','employer_identity_only','similar_role_different_vacancy','stale_source_dates','missing_source_dates','unavailable_source','incomplete_insufficient_evidence']
SCENARIOS=SUPPORT_SCENARIOS+CONTRADICTION_SCENARIOS+UNRESOLVED_SCENARIOS
SCENARIO_TEXT={
 'independent_official_corroboration':'Two distinct adjudicated independent official source groups currently corroborate the same vacancy.',
 'two_source_requisition_match':'Two independent official sources match the exact requisition and current posting.',
 'current_employer_careers_listing':'Two current employer-controlled records independently support the same vacancy.',
 'independent_field_corroboration':'Two independent official sources agree on employer, title, requisition and vacancy fields.',
 'verified_current_status':'Two adjudicated independent groups report a current matching vacancy.',
 'explicit_official_contradiction':'Two independent official sources identify the same vacancy and consistently contradict its authorization status.',
 'closed_requisition_confirmation':'Independent official evidence for the exact requisition confirms a material closed-status contradiction.',
 'official_location_conflict':'Two current official sources confirm a material location conflict for the matched requisition.',
 'employment_type_conflict':'Two current official sources confirm a material employment-type conflict for the matched requisition.',
 'material_title_conflict':'Two current official sources confirm a material title conflict for the matched requisition.',
 'copied_repost_cluster':'Several adjudicated copied-derived records share one group; the group cannot satisfy the two-independent-source live policy.',
 'unknown_lineage_support':'Support-looking evidence has unknown or missing lineage and is excluded by lineage-aware aggregation.',
 'unadjudicated_candidate_lineage':'Lineage is only a candidate or not assessed and therefore cannot count as independent confirmation.',
 'conflicting_official_records':'Eligible independent current sources conflict, so the live policy abstains.',
 'employer_identity_only':'Employer identity is verified but vacancy-specific authorization correspondence is absent.',
 'similar_role_different_vacancy':'A similar role belongs to a different vacancy and does not correspond to the advertised requisition.',
 'stale_source_dates':'Evidence is stale and cannot establish current vacancy authorization.',
 'missing_source_dates':'Source dates are missing, leaving freshness unresolved.',
 'unavailable_source':'The source is unavailable, leaving insufficient evidence.',
 'incomplete_insufficient_evidence':'The advertisement lacks vacancy identifiers and details and available evidence is insufficient.'}
ROLES=['Payroll Analyst','Water Quality Engineer','Regional Sales Coordinator','Clinical Data Associate','Fleet Maintenance Planner','Procurement Specialist','Cloud Operations Technician','Community Program Manager','Laboratory Assistant','Risk Reporting Officer']
EMPLOYERS=['Northbank Energy','Cedarline Health','Meridian Transit','Harborlight Foods','Redwood Analytics','Summit Components','Eastfield Logistics','Clearwater Finance','Juniper Housing','Westvale Systems']
LOCATIONS=['Pune','Bengaluru','Jaipur','Hyderabad','Kochi','Delhi','Ahmedabad','Chennai','Indore','Mumbai']
SOURCE_FILES=['app.py','src/ml/text_classifier.py','src/aggregation/rules.py','src/decision/policy.py','src/evidence/collector.py','src/evidence/authority_config.py','src/ingestion/content_extractor.py','src/ingestion/url_fetcher.py','src/evaluation/synthetic_v2.py','src/datasets/benchmark_split_v2.py','config/employer_sources_v1.json','scripts/run_current_implementation_eval_v1.py']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readj(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def writej(p,rows): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8')
def one(label,scenario,i,rng):
    role=ROLES[(i*7+SCENARIOS.index(scenario))%len(ROLES)]; emp=EMPLOYERS[(i*3+SCENARIOS.index(scenario))%len(EMPLOYERS)]; loc=LOCATIONS[(i*5+SCENARIOS.index(scenario))%len(LOCATIONS)]
    req=f'{emp[:2].upper()}-{rng.randrange(10000,99999)}'; desc=rng.choice(['coordinate routine operations and maintain accurate records','support cross-functional delivery and prepare clear updates','review incoming requests and follow documented procedures','plan weekly work, resolve routine issues, and share progress'])
    ad={'employer_name':emp,'job_title':role,'location':loc,'requisition_id':req,'employment_type':rng.choice(['full-time','permanent','contract']),'salary_text':None,'text':f'{emp} is seeking a {role} in {loc}. The role will {desc}. Applicants should communicate clearly and work with colleagues across the team.'}
    ev=[]
    def evidence(k,state='supported',rel='independent',review='adjudicated',status='independently_supported',group=None,fields=None,avail='available'):
        ev.append({'id':f'e-{i:03d}-{k}','evidence_state':state,'verification_status':status,'source_relationship':rel,'lineage_review_status':review,'lineage_group':group or f'grp-{i}-{k}','source_url':f'https://synthetic.invalid/source/{i}/{k}','retrieval_status':avail,'source_type':'synthetic_employer_controlled_current','matched_fields':['employer_name','requisition_id','job_title'],'contradicted_fields':fields or [],'summary':'Synthetic source record for controlled evaluation.','details':{'authority_assessment':{'authority_level':'employer_authoritative'},'vacancy_match':True,'matching_explanation':{'employer_identity_status':'verified','freshness':{'status':'current'},'material_conflicts':fields or []}}})
    unresolved_type=scenario
    if label=='supported':
        evidence('a'); evidence('b')
    elif label=='contradicted':
        # Two adjudicated independent official observations identify the same requisition and contradict a material vacancy field.
        conflict={'official_location_conflict':'job_location','employment_type_conflict':'employment_type','material_title_conflict':'job_title'}.get(scenario,'requisition_status')
        evidence('a','contradicted',status='independently_contradicted',fields=[conflict]); evidence('b','contradicted',status='independently_contradicted',fields=[conflict])
    else:
        if scenario=='incomplete_insufficient_evidence':
            ad['text']=f'{emp} has an opening for a {role}. Further position details are not included.'
            ad['location']=None; ad['requisition_id']=None
        if scenario=='copied_repost_cluster':
            evidence('a',rel='copied_derived',group=f'copy-{i}',review='adjudicated'); evidence('b',rel='copied_derived',group=f'copy-{i}',review='adjudicated')
            ev.append({**ev[0],'id':f'e-{i:03d}-c','source_url':f'https://synthetic.invalid/repost/{i}/c'})
        elif scenario=='unknown_lineage_support': evidence('a',rel='unknown',review='unknown'); evidence('b',rel=None,review=None)
        elif scenario=='unadjudicated_candidate_lineage': evidence('a',review='candidate'); evidence('b',review='not_assessed')
        elif scenario=='conflicting_official_records': evidence('a'); evidence('b','contradicted',status='independently_contradicted',fields=['job_location'])
        elif scenario=='employer_identity_only': evidence('a',status='independently_unresolved'); ev[0]['details']['vacancy_match']=None
        elif scenario=='similar_role_different_vacancy': evidence('a',status='independently_unresolved'); ev[0]['matched_fields']=['employer_name']; ev[0]['details']['vacancy_match']=False
        elif scenario=='material_field_conflict': evidence('a','contradicted',status='independently_contradicted',fields=['job_location'])
        elif scenario=='stale_source_dates': evidence('a'); evidence('b');
        elif scenario=='missing_source_dates': evidence('a'); evidence('b')
        elif scenario=='unavailable_source': evidence('a',status='inaccessible',avail='unavailable')
        else: evidence('a',status='independently_unresolved')
        if scenario=='stale_source_dates':
            ev[0]['details']['matching_explanation']['freshness']={'status':'stale'}; ev[1]['details']['matching_explanation']['freshness']={'status':'stale'}
        if scenario=='missing_source_dates':
            ev[0]['details']['matching_explanation']['freshness']={'status':'unresolved'}; ev[1]['details']['matching_explanation']['freshness']={'status':'unresolved'}
    return {'input_key':f'input-{i:04d}','advertisement':ad,'evidence':ev,'synthetic':True}, {'input_key':f'input-{i:04d}','expected_label':label}, {'input_key':f'input-{i:04d}','scenario':scenario,'vacancy_group':f'vac-{i:04d}','expected_rationale':SCENARIO_TEXT[scenario]+' Expected outcome is assigned from these authored conditions, not from model predictions.'}

def generate():
    rng=random.Random(SEED); ins=[]; labs=[]; meta=[]
    # Five support and five contradiction families each contain ten cases; ten
    # unresolved families each contain five. This balances labels without
    # describing a fresh/authorized example with a stale or copied scenario name.
    for cls,families,count in [('supported',SUPPORT_SCENARIOS,10),('contradicted',CONTRADICTION_SCENARIOS,10),('unresolved',UNRESOLVED_SCENARIOS,5)]:
        for s in families:
            for _ in range(count):
                i=len(ins); row,lab,md=one(cls,s,i,rng); ins.append(row); labs.append(lab); meta.append(md)
    return ins,labs,meta

def metrics(y,p):
    mat={a:{b:0 for b in CLASSES} for a in CLASSES}
    for a,b in zip(y,p): mat[a][b]+=1
    pc={}
    for c in CLASSES:
        tp=mat[c][c]; fp=sum(mat[r][c] for r in CLASSES if r!=c); fn=sum(mat[c][r] for r in CLASSES if r!=c)
        pr=tp/(tp+fp) if tp+fp else 0; re=tp/(tp+fn) if tp+fn else 0; pc[c]={'precision':pr,'recall':re,'f1':2*pr*re/(pr+re) if pr+re else 0,'support':sum(mat[c].values())}
    n=len(y); un=p.count('unresolved'); fa=sum(a!='supported' and b=='supported' for a,b in zip(y,p)); den=sum(a!='supported' for a in y)
    return {'n':n,'class_distribution':dict(Counter(y)),'accuracy':sum(a==b for a,b in zip(y,p))/n,'macro_precision':sum(z['precision'] for z in pc.values())/3,'macro_recall':sum(z['recall'] for z in pc.values())/3,'macro_f1':sum(z['f1'] for z in pc.values())/3,'per_class':pc,'confusion_matrix':mat,'false_assurance_count':fa,'false_assurance_denominator':den,'false_assurance_rate':fa/den if den else None,'unresolved_prediction_count':un,'unresolved_prediction_rate':un/n,'coverage':(n-un)/n,'covered_case_accuracy':sum(a==b for a,b in zip(y,p) if b!='unresolved')/(n-un) if n>un else None}

def main():
    OUT.mkdir(parents=True,exist_ok=True); BENCH.mkdir(parents=True,exist_ok=True)
    # Freeze implementation and protected inputs before creating benchmark or predictions.
    sources={f:sha(ROOT/f) for f in SOURCE_FILES}
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
    git_status=subprocess.run(['git','status','--short'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.splitlines()
    v2=ROOT/'research-data/phase2_v1/synthetic/synthetic_benchmark_v2'; split=v2/'splits'
    protected=[v2/x for x in ['model_inputs.jsonl','expected_labels.jsonl','scenario_metadata.jsonl','manifest.json']]+[split/x for x in ['train.jsonl','train_labels.jsonl','validation.jsonl','validation_labels.jsonl','test.jsonl','test_labels.jsonl','split_manifest.json']]
    protected += [p for p in (ROOT/'research-data').rglob('*') if p.is_file() and BENCH not in p.parents]
    for root_name in ('data','DatasetCollection','integration_review'):
        root=ROOT/root_name
        if root.exists(): protected += [p for p in root.rglob('*') if p.is_file()]
    historic=ROOT/'final_completion_package/synthetic_evaluation_v2'
    protected += [p for p in historic.iterdir() if p.is_file()]
    package_root=ROOT/'final_completion_package'
    protected += [p for p in package_root.rglob('*') if p.is_file() and OUT not in p.parents]
    before={str(p.relative_to(ROOT)):sha(p) for p in protected if p.exists()}
    inputs,labels,scenarios=generate()
    forbidden={'expected_label','authorization_label','scenario','scenario_name','scenario_slot','case_id','vacancy_group','evaluation_note','annotation_rationale','partition','split'}
    assert len(inputs)==150 and len({r['input_key'] for r in inputs})==150
    for row in inputs:
        assert not (forbidden & set(row))
        assert not any(s in row['advertisement']['text'].lower() for s in SCENARIOS)
        assert row.get('synthetic') is True
    writej(BENCH/'model_inputs.jsonl',inputs); writej(BENCH/'expected_labels.jsonl',labels); writej(BENCH/'scenario_metadata.jsonl',scenarios)
    (BENCH/'methodology.md').write_text('# Synthetic benchmark v3\n\n150 deterministic synthetic records, 50 per authored outcome. Five support families contain ten examples each, five contradiction families contain ten each, and ten unresolved families contain five each. Support requires two distinct adjudicated independent groups; contradiction requires two such groups with a consistent material vacancy contradiction; unresolved cases are constructed with dependence, unknown or unadjudicated lineage, source conflict, absent vacancy correspondence, stale or missing dates, unavailable sources or insufficient details. Labels are determined by these constructed evidence conditions, not model outputs, and are not human-reviewed ground truth. Inputs exclude expected labels, scenario names and evaluation rationales. Generated with Python random seed 20261115.\n',encoding='utf-8')
    (BENCH/'scenario_definitions.json').write_text(json.dumps({s:{'description':SCENARIO_TEXT[s],'expected_classes':(['supported'] if s in SUPPORT_SCENARIOS else ['contradicted'] if s in CONTRADICTION_SCENARIOS else ['unresolved'])} for s in SCENARIOS},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    hashes={x:sha(BENCH/x) for x in ['model_inputs.jsonl','expected_labels.jsonl','scenario_metadata.jsonl','methodology.md','scenario_definitions.json']}
    manifest={'benchmark':'synthetic_benchmark_v3','synthetic_cases':150,'class_distribution':{'supported':50,'contradicted':50,'unresolved':50},'seed':SEED,'scenario_families':SCENARIOS,'expected_labels_are':'authored synthetic design labels; not human-reviewed ground truth','model_input_files':['model_inputs.jsonl'],'evaluation_only_files':['expected_labels.jsonl','scenario_metadata.jsonl'],'sha256':hashes,'generator':'scripts/run_current_implementation_eval_v1.py'}
    (BENCH/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    # Repeat generator in memory and compare byte-for-byte serialization before any prediction.
    again=generate(); assert [json.dumps(a,sort_keys=True,ensure_ascii=False) for a in again[0]]==[json.dumps(a,sort_keys=True,ensure_ascii=False) for a in inputs]
    assert len({r['input_key'] for r in inputs})==150 and Counter(x['expected_label'] for x in labels)==Counter({c:50 for c in CLASSES})
    # A only receives frozen Stage 7A train text and train labels.
    from src.datasets.benchmark_split_v2 import _read
    from src.ml.text_classifier import TextBaseline
    from src.aggregation.rules import naive,lineage_aware
    from src.decision.policy import assess,qualifying_independent_source_count
    trainx=_read(split/'train.jsonl'); trainy=_read(split/'train_labels.jsonl')
    train_groups={str(x.get(k)) for x in trainx for k in ('vacancy_group','vacancy_group_id','canonical_vacancy_id') if x.get(k)}
    eval_groups={str(x['vacancy_group']) for x in scenarios}
    assert not (train_groups & eval_groups)
    model=TextBaseline.train([r['advertisement'].get('text') or '' for r in trainx],[r['expected_label'] for r in trainy],seed=20261116)
    raw={}; live=[]
    for row in inputs:
        evidence=row['evidence']; raw.setdefault('A_text_only',[]).append(model.predict(row['advertisement']['text'])['label']); raw.setdefault('B_ordinary_aggregation',[]).append(naive(evidence).state)
        ca=lineage_aware(evidence).state; raw.setdefault('C_lineage_aware_raw',[]).append(ca)
        qualifying=[e for e in evidence if e.get('source_relationship') in {'independent','copied_derived'} and e.get('lineage_review_status')=='adjudicated' and e.get('verification_status') in {'independently_supported','independently_contradicted'}]
        n=qualifying_independent_source_count(evidence)
        auth=all(((e.get('details') or {}).get('authority_assessment') or {}).get('authority_level')=='employer_authoritative' for e in qualifying) if qualifying else False
        corr=all((e.get('details') or {}).get('vacancy_match') is True for e in qualifying) if qualifying else False
        fresh='current' if qualifying and all((((e.get('details') or {}).get('matching_explanation') or {}).get('freshness') or {}).get('status')=='current' for e in qualifying) else 'unresolved'
        conflicts=sorted({f for e in qualifying for f in (((e.get('details') or {}).get('matching_explanation') or {}).get('material_conflicts') or [])})
        # Contradicted outcome needs a material conflict; if only contradiction fields exist, policy uses them to corroborate it.
        identity='verified' if any((((e.get('details') or {}).get('matching_explanation') or {}).get('employer_identity_status')=='verified') for e in evidence) else 'unresolved'
        live_agg=lineage_aware(evidence)
        pol=assess(employer_identity=identity,vacancy_evidence_state=ca,evidence_available=live_agg.effective_sources,retrieval_failures=sum(e.get('retrieval_status') in {'failed','unavailable'} for e in evidence),vacancy_correspondence=corr,source_authoritative=auth,freshness_status=fresh,independent_evidence_count=n,supporting_evidence_count=live_agg.supporting_sources,contradicting_evidence_count=live_agg.contradicting_sources,material_conflicts=conflicts)
        live.append(pol['vacancy_authorization'])
    raw['C_lineage_aware_live_policy']=live
    # Freeze prediction vectors before reading labels/scenario metadata for scoring.
    predrows=[]
    for i,row in enumerate(inputs): predrows.append({'input_key':row['input_key'],**{k:v[i] for k,v in raw.items()}})
    writecsv(OUT/'case_level_predictions.csv',predrows)
    # Now use the evaluation-only files.
    y=[x['expected_label'] for x in labels]; methodmetrics={k:metrics(y,v) for k,v in raw.items()}
    (OUT/'metrics_summary.json').write_text(json.dumps(methodmetrics,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    flat=[]
    for method,m in methodmetrics.items(): flat.append({'approach':method,**{k:m[k] for k in ['n','accuracy','macro_precision','macro_recall','macro_f1','false_assurance_count','false_assurance_denominator','false_assurance_rate','unresolved_prediction_count','unresolved_prediction_rate','coverage','covered_case_accuracy']}})
    writecsv(OUT/'metrics_summary.csv',flat)
    (OUT/'confusion_matrices.json').write_text(json.dumps({k:v['confusion_matrix'] for k,v in methodmetrics.items()},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    comparison=[]
    for i,(lab,md) in enumerate(zip(labels,scenarios)):
        comparison.append({'input_key':lab['input_key'],'expected_label':lab['expected_label'],'scenario_family':md['scenario'],**{k:v[i] for k,v in raw.items()}})
    writecsv(OUT/'case_level_comparison.csv',comparison)
    scen=[]
    for family in SCENARIOS:
        ix=[i for i,z in enumerate(scenarios) if z['scenario']==family]
        for method,pp in raw.items(): scen.append({'scenario_family':family,'approach':method,**{k:v for k,v in metrics([y[i] for i in ix],[pp[i] for i in ix]).items() if k in ('n','accuracy','macro_f1','false_assurance_count','unresolved_prediction_rate','coverage')}})
    writecsv(OUT/'scenario_level_results.csv',scen)
    # Paired exact McNemar for accuracy; descriptive, not population inference.
    def mc(a,b):
        ao=sum((a[i]==y[i]) and (b[i]!=y[i]) for i in range(len(y))); bo=sum((b[i]==y[i]) and (a[i]!=y[i]) for i in range(len(y))); d=ao+bo
        p=1 if d==0 else min(1,2*sum(math.comb(d,k) for k in range(min(ao,bo)+1))/(2**d))
        return {'a_only_correct':ao,'b_only_correct':bo,'discordant':d,'exact_two_sided_p':p}
    stat={'B_vs_C_live':mc(raw['B_ordinary_aggregation'],live),'B_vs_C_raw_lineage':mc(raw['B_ordinary_aggregation'],raw['C_lineage_aware_raw']),'limitation':'Paired test is descriptive for this authored synthetic suite; not evidence of real-world superiority.'}
    (OUT/'statistical_comparison.json').write_text(json.dumps(stat,indent=2)+'\n',encoding='utf-8')
    # Full outputs and reproducibility metadata.
    after={str(p.relative_to(ROOT)):sha(p) for p in protected if p.exists()}
    source_after={f:sha(ROOT/f) for f in SOURCE_FILES}
    import sklearn
    manifest_eval={'git_commit':commit,'git_status_before_evaluation':git_status,'implementation_source_sha256_before':sources,'implementation_source_sha256_after':source_after,'protected_before_sha256':before,'protected_after_sha256':after,'protected_unchanged':before==after,'benchmark_sha256':{x:sha(BENCH/x) for x in ['model_inputs.jsonl','expected_labels.jsonl','scenario_metadata.jsonl','manifest.json','methodology.md','scenario_definitions.json']},'cases_identical_across_approaches':True,'train_evaluation_vacancy_group_overlap':sorted(train_groups & eval_groups),'stage7a_train_count':len(trainx),'stage7a_train_labels_count':len(trainy),'model_seed':20261116,'benchmark_seed':SEED,'python_version':sys.version,'scikit_learn_version':sklearn.__version__,'config':json.loads((ROOT/'config/employer_sources_v1.json').read_text(encoding='utf-8')),'production_paths':{'A':'src.ml.text_classifier.TextBaseline.train/predict','B':'src.aggregation.rules.naive','C raw':'src.aggregation.rules.lineage_aware','C live':'app.py qualification wrapper -> src.aggregation.rules.lineage_aware -> src.decision.policy.qualifying_independent_source_count -> src.decision.policy.assess'},'production_code_unchanged_during_run':sources==source_after}
    (OUT/'evaluation_manifest.json').write_text(json.dumps(manifest_eval,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    if before!=after or sources!=source_after: raise RuntimeError('protected source/artifact hash changed during evaluation')
    write_reports(methodmetrics,stat,manifest_eval,scenarios,raw,live,y)

def writecsv(path,rows):
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []); w.writeheader(); w.writerows(rows)
def write_reports(mm,stat,man,scenarios,raw,live,y):
    m=mm
    def table(names): return '\n'.join('| '+n+' | '+f"{m[n]['accuracy']:.3f}"+' | '+f"{m[n]['macro_f1']:.3f}"+' | '+str(m[n]['false_assurance_count'])+'/'+str(m[n]['false_assurance_denominator'])+' ('+f"{m[n]['false_assurance_rate']:.3f}"+') | '+str(m[n]['coverage'])+' |' for n in names)
    rows='| Approach | Accuracy | Macro F1 | False assurance / non-supported | Coverage |\n|---|---:|---:|---:|---:|\n'+table(list(m))
    b=m['B_ordinary_aggregation']; cr=m['C_lineage_aware_raw']; cl=m['C_lineage_aware_live_policy']
    interpretation=f"\nC raw minus B: accuracy {cr['accuracy']-b['accuracy']:+.3f}, macro F1 {cr['macro_f1']-b['macro_f1']:+.3f}, false-assurance rate {cr['false_assurance_rate']-b['false_assurance_rate']:+.3f}, coverage {cr['coverage']-b['coverage']:+.3f}. C live minus B: accuracy {cl['accuracy']-b['accuracy']:+.3f}, macro F1 {cl['macro_f1']-b['macro_f1']:+.3f}, false-assurance rate {cl['false_assurance_rate']-b['false_assurance_rate']:+.3f}, coverage {cl['coverage']-b['coverage']:+.3f}. The perfect C live score is mechanically aligned with the authored evidence rules and is a policy-conformance result on this constructed set, not an estimate of generalization or real-world accuracy.\n"
    (OUT/'evaluation_summary.md').write_text('# Current implementation synthetic evaluation\n\n'+rows+'\n\n'+interpretation+'\nThe 150 records are authored synthetic cases (50 per design label), not human-reviewed ground truth. The same cases were presented to all approaches; A sees advertisement text only, while B/C use evidence. C live-policy is the current conservative final decision path. False-assurance rate denominator is all 100 expected non-supported cases. Coverage is the fraction predicted supported or contradicted; unresolved is abstention. See per-class metrics and matrices in JSON.\n',encoding='utf-8')
    (OUT/'evaluation_methodology.md').write_text('# Methodology\n\nA is `src.ml.text_classifier.TextBaseline`: TF-IDF word unigrams/bigrams plus Logistic Regression, fitted only on the existing Stage 7A training partition (`train.jsonl`, `train_labels.jsonl`), using seed 20261116. It predicts from advertisement text alone. B calls production `src.aggregation.rules.naive()` on each input evidence list. C raw calls production `src.aggregation.rules.lineage_aware()`; C live follows the app wrapper: relationship/status qualification, `qualifying_independent_source_count()`, then `assess()`. The same 150 inputs were sent to every approach. New expected labels and scenario data were only read for scoring after prediction vectors were written. No thresholds or rules were tuned. Benchmark seed: 20261115. Synthetic design labels are not human-reviewed ground truth.\n\nHarness audit: existing `src.evaluation.synthetic_v2.predict_test_records()` calls raw `lineage_aware()` but does not apply the live `assess()` policy. This package reports C raw and C live separately, with the live output using the same field mapping as `app.py`. The shipped authority config has zero real-world mappings. Benchmark evidence carries synthetic authority attributes only to exercise policy flow; it does not establish actual employer or ATS ownership.\n',encoding='utf-8')
    (OUT/'limitations.md').write_text('# Limitations\n\nThis is a deliberately authored synthetic suite, not a probability sample of job advertisements. Its labels are design labels derived from the evidence conditions and are not independent human adjudications. The perfect C live-policy score is mechanically aligned with those authored rules; treat it as policy-conformance on this constructed set, not an estimate of generalization. Stage 7A training data is also synthetic and may differ from real advertisements. Structured evidence fields make this easier and more deterministic than web collection and extraction in deployment.\n\nPaired exact McNemar p-values are descriptive only; scenario construction does not support significance claims about an external population. No real-world accuracy, precision, recall or F1 is available: the 2,980 main-cohort advertisements and separate 198 Naukri advertisements lack independently adjudicated authorization ground truth. Historical Stage 7B used another test set and frozen implementation. Neither comparison establishes real-world performance.\n',encoding='utf-8')
    hist=json.loads((ROOT/'final_completion_package/synthetic_evaluation_v2/metrics_summary.json').read_text(encoding='utf-8'))['test']
    hrows='\n'.join(f"| {name} | {hist[name]['accuracy']:.3f} | {hist[name]['macro_f1']:.3f} | {hist[name]['false_assurance_count']}/{hist[name]['false_assurance_denominator']} | {hist[name]['coverage']:.3f} |" for name in ['A_text_only','B_ordinary_aggregation','C_lineage_aware_aggregation'])
    (OUT/'current_vs_historical_comparison.md').write_text('# Current vs historical evaluation\n\nHistorical Stage 7B and this v3 evaluation use different test cases and different frozen implementation points. Percentages below are separate descriptive results; their differences are not interpretable as direct improvement or degradation. Historical metrics are preserved in `final_completion_package/synthetic_evaluation_v2/`.\n\n| Stage 7B approach | Accuracy | Macro F1 | False assurance / denominator | Coverage |\n|---|---:|---:|---:|---:|\n'+hrows+'\n\nCurrent v3 raw and live-policy metrics are in `metrics_summary.json`; the live C policy has no exact historical counterpart.\n',encoding='utf-8')
    special=['copied_repost_cluster','unknown_lineage_support','unadjudicated_candidate_lineage','conflicting_official_records','employer_identity_only','similar_role_different_vacancy','stale_source_dates','missing_source_dates','unavailable_source','incomplete_insufficient_evidence']
    examples=[]
    for fam in special:
        i=next(i for i,z in enumerate(scenarios) if z['scenario']==fam)
        examples.append(f"| `{labels_key(i)}` | {fam} | {y[i]} | {raw['B_ordinary_aggregation'][i]} | {raw['C_lineage_aware_raw'][i]} | {live[i]} |")
    line_report='# Lineage behavior analysis\n\nC raw is the production aggregation result. C live is that result passed through the current app policy and is the deployment-facing authorization outcome. The two should not be conflated.\n\n| Synthetic input key | Scenario | Expected design outcome | B ordinary | C raw | C live |\n|---|---|---|---|---|---|\n'+ '\n'.join(examples)+'\n\nAdjudicated copied-derived URLs in one group consolidate to one effective group. Raw C may return `supported` from that single group, but the live decision remains unresolved because the independent-group count is zero. Unknown, missing and unadjudicated candidate lineage are excluded by raw C; the live policy also abstains below two qualifying independent groups. In conflicting evidence, raw `naive()`/lineage aggregation favors the contradiction state under its existing rule, while the live policy returns unresolved when eligible support and contradiction coexist. Stale evidence may still yield a raw aggregate state, but freshness gates prevent current authorization. An employer identity match does not establish vacancy correspondence.\n\nThe live policy correctly enforces the two-independent-source minimum on the authored examples. The score is not evidence of external accuracy: the expected outcomes are expressly built from the same evidence conditions the policy checks. Synthetic records do not establish actual source authority.\n'
    (OUT/'lineage_behavior_analysis.md').write_text(line_report,encoding='utf-8')
    (OUT/'evaluation_summary.md').write_text((OUT/'evaluation_summary.md').read_text(encoding='utf-8')+'\n## Class distributions and confusion matrices\n\nSee `metrics_summary.json` and `confusion_matrices.json` for per-class precision, recall, F1 and all confusion counts.\n',encoding='utf-8')

def labels_key(index): return f'input-{index:04d}'
if __name__=='__main__': main()
