import csv, json, random, re, html
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
csv.field_size_limit(50_000_000)
SEED=20261113

def read_csv(name):
    with (ROOT/name).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def write_csv(name, rows, fields):
    p=ROOT/name; p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def clean(s):
    s=html.unescape(str(s or '')); s=re.sub(r'<[^>]+>',' ',s)
    return re.sub(r'\s+',' ',s).strip().casefold()
def norm(s): return re.findall(r'[a-z0-9]+',clean(s))
def sim(a,b):
    x,y=norm(a),norm(b)
    return len(set(x)&set(y))/max(1,len(set(x)|set(y)))
def textsim(a,b): return SequenceMatcher(None,' '.join(norm(a)),' '.join(norm(b))).ratio()
def pick_period(s):
    return (s or '')[:7] or 'unknown'

def main():
    a=read_csv('processed/table_A_advertisements.csv')
    e=read_csv('processed/stage4e_evidence_records.csv')
    by={r['case_id']:r for r in e}
    assert len(a)==780 and all(r['employer_id']=='EMP_STRIPE' for r in a)
    # Reproduce Stage 5A candidate rule; candidates remain unconfirmed.
    pairs=[]
    desc=[(clean(r.get('job_description')),set(norm(r.get('job_description')))) for r in a]
    for i in range(len(a)):
        for j in range(i+1,len(a)):
            d1,d2=a[i],a[j]; x, sx=desc[i]; y, sy=desc[j]
            jac=len(sx&sy)/max(1,len(sx|sy))
            if jac>=.85:
                ds=SequenceMatcher(None,x,y).ratio()
                if ds>=.88:
                    ts=textsim(d1.get('job_title'),d2.get('job_title'))
                    ls=textsim(d1.get('location'),d2.get('location'))
                    pairs.append((d1,d2,ds,ts,ds,ls))
    assert len(pairs)==207, len(pairs)
    involved={x for p in pairs for x in (p[0]['case_id'],p[1]['case_id'])}
    # Greedy stratified selection, then seeded fill to exactly 100.
    rng=random.Random(SEED)
    rows=[]
    for r in a:
        q=by.get(r['case_id'],{})
        fields={'evidence_state':q.get('evidence_classification','unknown'), 'vacancy_status':q.get('vacancy_status','unknown'), 'match_quality':q.get('source_record_match_state','unknown'), 'period':pick_period(q.get('publication_date') or r.get('observed_at')), 'description_completeness':'complete' if len(r.get('job_description','').strip())>=500 else 'short_or_incomplete', 'near_duplicate_involvement':'candidate_pair' if r['case_id'] in involved else 'no_candidate_pair'}
        rows.append({**r,**fields})
    targets={k:set(x) for k,x in {'evidence_state':set(x['evidence_state'] for x in rows),'vacancy_status':set(x['vacancy_status'] for x in rows),'match_quality':set(x['match_quality'] for x in rows),'period':set(x['period'] for x in rows),'description_completeness':set(x['description_completeness'] for x in rows),'near_duplicate_involvement':{'candidate_pair','no_candidate_pair'}}.items()}
    chosen=[]; remaining=rows[:]
    while len(chosen)<100 and targets:
        best=[]; score=-1
        for r in remaining:
            s=sum(r[k] in vals for k,vals in targets.items())
            if s>score: best=[r]; score=s
            elif s==score: best.append(r)
        if not best: break
        r=rng.choice(best); chosen.append(r); remaining.remove(r)
        for k in list(targets):
            targets[k].discard(r[k])
            if not targets[k]: del targets[k]
    rng.shuffle(remaining); chosen += remaining[:100-len(chosen)]
    chosen=sorted(chosen[:100], key=lambda r:r['case_id'])
    sample_fields=['case_id','employer_id','job_title','location','observed_at','evidence_state','vacancy_status','match_quality','period','description_completeness','near_duplicate_involvement','selection_seed','selection_reason']
    sample=[]
    for r in chosen:
        reason=';'.join(k+'='+r[k] for k in ['evidence_state','vacancy_status','match_quality','period','description_completeness','near_duplicate_involvement'])
        sample.append({**{k:r.get(k,'') for k in sample_fields[:-2]},'selection_seed':SEED,'selection_reason':reason})
    write_csv('processed/stage5b_human_review_sample.csv',sample,sample_fields)
    wf=['case_id','employer_identity_label','vacancy_authorization_label','fraud_outcome_label','evidence_references','annotation_rationale','reviewer_id','reviewer_confidence','adjudication_status']
    work=[]
    for r in chosen:
        q=by.get(r['case_id'],{})
        work.append({'case_id':r['case_id'],'evidence_references':q.get('evidence_id',''),'adjudication_status':'not_started'})
    write_csv('processed/stage5b_reviewer1_worksheet.csv',work,wf); write_csv('processed/stage5b_reviewer2_worksheet.csv',work,wf)
    pf=['pair_id','case_id_1','case_id_2','similarity_score','title_similarity','description_similarity','location_similarity','source_family','publication_time_comparison','reviewer_decision','copy_direction','lineage_rationale','confidence','adjudication_status']
    prows=[]
    for n,(x,y,o,t,d,l) in enumerate(pairs,1):
        p1,p2=by.get(x['case_id'],{}),by.get(y['case_id'],{})
        prows.append({'pair_id':f'S5B-PAIR-{n:03d}','case_id_1':x['case_id'],'case_id_2':y['case_id'],'similarity_score':f'{o:.6f}','title_similarity':f'{t:.6f}','description_similarity':f'{d:.6f}','location_similarity':f'{l:.6f}','source_family':'Stripe/Greenhouse','publication_time_comparison':(p1.get('publication_date','')+' vs '+p2.get('publication_date','')),'adjudication_status':'not_started'})
    write_csv('processed/stage5b_lineage_pair_review.csv',prows,pf)
    now=datetime.now(timezone.utc).isoformat()
    guidelines='''# Stage 5B Annotation Guidelines\n\n## Scope\nReviewers annotate evidence, not intuition. Stripe/Greenhouse and Naukri/ATS are separate cohorts. Missing or inaccessible evidence is not contradiction. Every non-unresolved decision requires source references and a written rationale.\n\n## Labels\n- Employer identity: `verified`, `contradicted`, `unresolved`. Verify the employer as the named organization; do not use ATS hosting alone.\n- Vacancy authorization: `supported`, `contradicted`, `unresolved`. Supported requires vacancy-level evidence sufficient to connect the employer, exact/identifiable vacancy, and authorization. Employer identity alone is insufficient.\n- Fraud outcome: `confirmed_legitimate`, `confirmed_fraudulent`, `unresolved`. Use only direct, adequate evidence. Missing URLs, unavailable/removed pages, incomplete descriptions, partial matches, and absent independent evidence do not establish fraud. A removed vacancy is not automatically fraudulent.\n\n## Evidence and provenance\nRecord URLs or evidence IDs, retrieval dates, and relevant excerpts or fields. Keep source independence separate from retrieval independence; a fresh Greenhouse response is same-system evidence, not independent confirmation. Check response provenance, case ID, source URL, hashes, and whether evidence belongs to this case.\n\n## Workflow\nReview independently. Select unresolved when evidence is insufficient or contradictory without a reliable resolution. Submit rationale and confidence. Do not change Table B. A lead adjudicator resolves disagreements after both initial worksheets are frozen; adjudication must cite the decisive evidence and preserve both original labels.\n\n## Pair review\nAllowed decisions: `confirmed_same_vacancy`, `confirmed_repost`, `probable_copy`, `template_similarity`, `unrelated`, `unresolved`. Similarity alone never proves copy direction or reposting.\n\n## Agreement\nAfter both reviewers submit, report class distributions and Cohen's kappa for each nominal label when two complete, independent ratings exist; use prevalence-aware interpretation and do not calculate agreement on blank/unsubmitted rows. Analyze disagreements by evidence state and provenance, then adjudicate.\n'''
    (ROOT/'reports/stage5b_annotation_guidelines.md').write_text(guidelines,encoding='utf-8')
    protocol={'stage':'5B','seed':SEED,'cohort':{'name':'Stripe/Greenhouse','records':780,'employer_ids':['EMP_STRIPE'],'excluded_dataset':'Naukri/ATS 198'},'sample_size':100,'selection_dimensions':['vacancy_status','evidence_state','field_match_quality','publication_period','description_completeness','near_duplicate_involvement'],'candidate_pairs':len(prows),'pair_rule':'Reproduced Stage 5A thresholds; candidates are not confirmed lineage.','labels':{'employer_identity':['verified','contradicted','unresolved'],'vacancy_authorization':['supported','contradicted','unresolved'],'fraud_outcome':['confirmed_legitimate','confirmed_fraudulent','unresolved']},'pair_decisions':['confirmed_same_vacancy','confirmed_repost','probable_copy','template_similarity','unrelated','unresolved'],'reviewer_workflow':['independent annotation','freeze initial copies','compare distributions and Cohen kappa where appropriate','lead adjudication','provenance audit'],'agreement_not_yet_calculated':True,'created_utc':now}
    (ROOT/'reports/stage5b_annotation_protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    log={'stage':'5B','created_utc':now,'script':'scripts/run_stage5b.py','inputs':['table_A_advertisements.csv','stage4e_evidence_records.csv','stage5a_lineage_audit.json'],'outputs':['stage5b_human_review_sample.csv','stage5b_reviewer1_worksheet.csv','stage5b_reviewer2_worksheet.csv','stage5b_lineage_pair_review.csv','stage5b_annotation_guidelines.md','stage5b_annotation_protocol.json'],'stripe_records':len(a),'selected_records':len(chosen),'candidate_pairs':len(prows),'seed':SEED,'previous_files_modified':False,'review_labels_filled':False}
    (ROOT/'reports/stage5b_execution_log.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
    print(json.dumps({'selected':len(chosen),'pairs':len(prows),'seed':SEED},indent=2))
if __name__=='__main__': main()
