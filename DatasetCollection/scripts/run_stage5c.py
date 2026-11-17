import csv, json, math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
csv.field_size_limit(50_000_000)
ALLOWED={
 'employer_identity_label':{'verified','contradicted','unresolved'},
 'vacancy_authorization_label':{'supported','contradicted','unresolved'},
 'fraud_outcome_label':{'confirmed_legitimate','confirmed_fraudulent','unresolved'},
}
PAIR_ALLOWED={'confirmed_same_vacancy','confirmed_repost','probable_copy','template_similarity','unrelated','unresolved'}

def read(path):
    with (ROOT/path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(path,rows,fields):
    with (ROOT/path).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def kappa(xs,ys):
    n=len(xs)
    if not n:return None
    agree=sum(a==b for a,b in zip(xs,ys))/n
    ca,cb=Counter(xs),Counter(ys)
    pe=sum(ca[k]/n*cb[k]/n for k in set(ca)|set(cb))
    return None if pe==1 else (agree-pe)/(1-pe)
def main():
    r1=read(Path('processed/stage5b_reviewer1_worksheet.csv')); r2=read(Path('processed/stage5b_reviewer2_worksheet.csv'))
    pairs=read(Path('processed/stage5b_lineage_pair_review.csv'))
    ids1=[x.get('case_id','') for x in r1]; ids2=[x.get('case_id','') for x in r2]
    c1,c2=Counter(ids1),Counter(ids2); s1,s2=set(ids1),set(ids2)
    validation=[]; stats={}; disagreements=[]
    by1={x['case_id']:x for x in r1}; by2={x['case_id']:x for x in r2}
    for cid in sorted(s1|s2):
        a,b=by1.get(cid,{}),by2.get(cid,{})
        row={'case_id':cid,'reviewer1_present':cid in s1,'reviewer2_present':cid in s2,'same_case_id':cid in s1 and cid in s2,'duplicate_in_reviewer1':c1[cid]>1,'duplicate_in_reviewer2':c2[cid]>1,'evidence_reference_reviewer1':a.get('evidence_references',''),'evidence_reference_reviewer2':b.get('evidence_references',''),'validation_status':'valid' if cid in s1 and cid in s2 and c1[cid]==1 and c2[cid]==1 else 'invalid_or_missing'}
        for f,allowed in ALLOWED.items():
            v1=a.get(f,'');v2=b.get(f,''); row[f+'_reviewer1']=v1;row[f+'_reviewer2']=v2
            row[f+'_reviewer1_valid']=not v1 or v1 in allowed;row[f+'_reviewer2_valid']=not v2 or v2 in allowed
            if v1 and v2 and v1!=v2: disagreements.append({'case_id':cid,'field_name':f,'reviewer1_label':v1,'reviewer2_label':v2,'reviewer1_evidence_reference':a.get('evidence_references',''),'reviewer2_evidence_reference':b.get('evidence_references',''),'disagreement_type':'label_difference','adjudication_status':'not_started'})
        validation.append(row)
    for f,allowed in ALLOWED.items():
        complete=[cid for cid in sorted(s1&s2) if by1[cid].get(f) in allowed and by2[cid].get(f) in allowed]
        x=[by1[cid][f] for cid in complete];y=[by2[cid][f] for cid in complete]
        stats[f]={'n_common_cases':len(s1&s2),'n_complete_pairs':len(complete),'missing_reviewer1':sum(not by1.get(cid,{}).get(f,'') for cid in s1&s2),'missing_reviewer2':sum(not by2.get(cid,{}).get(f,'') for cid in s1&s2),'invalid_reviewer1':sum(bool(by1.get(cid,{}).get(f)) and by1[cid][f] not in allowed for cid in s1),'invalid_reviewer2':sum(bool(by2.get(cid,{}).get(f)) and by2[cid][f] not in allowed for cid in s2),'raw_agreement':sum(a==b for a,b in zip(x,y))/len(x) if x else None,'cohen_kappa':kappa(x,y),'reviewer1_class_distribution':dict(Counter(x)),'reviewer2_class_distribution':dict(Counter(y)),'interpretation':'Not interpretable: no complete human annotations.' if not x else ('Interpret cautiously because of class imbalance.' if max(Counter(x).values())/len(x)>.8 or max(Counter(y).values())/len(y)>.8 else 'Calculable on complete paired annotations.')}
    pair_valid=[]
    for p in pairs:
        d=p.get('reviewer_decision','');pair_valid.append({'pair_id':p.get('pair_id',''),'case_id_1':p.get('case_id_1',''),'case_id_2':p.get('case_id_2',''),'decision':d,'decision_valid':not d or d in PAIR_ALLOWED,'evidence_reference_present':bool(p.get('lineage_rationale','')),'adjudication_status':p.get('adjudication_status','')})
    vfields=['case_id','reviewer1_present','reviewer2_present','same_case_id','duplicate_in_reviewer1','duplicate_in_reviewer2','evidence_reference_reviewer1','evidence_reference_reviewer2','validation_status']+[f+s for f in ALLOWED for s in ['_reviewer1','_reviewer2','_reviewer1_valid','_reviewer2_valid']]
    write('processed/stage5c_annotation_validation.csv',validation,vfields)
    dfields=['case_id','field_name','reviewer1_label','reviewer2_label','reviewer1_evidence_reference','reviewer2_evidence_reference','disagreement_type','adjudication_status'];write('reports/stage5c_disagreement_report.csv',disagreements,dfields)
    afields=['case_id','disputed_fields','reviewer1_labels','reviewer2_labels','evidence_references','adjudicator_label','adjudicator_rationale','adjudicator_id','adjudication_timestamp','adjudication_status'];
    adjud=[]
    for cid in sorted({d['case_id'] for d in disagreements}):
        ds=[d for d in disagreements if d['case_id']==cid]; adjud.append({'case_id':cid,'disputed_fields':';'.join(d['field_name'] for d in ds),'reviewer1_labels':';'.join(d['reviewer1_label'] for d in ds),'reviewer2_labels':';'.join(d['reviewer2_label'] for d in ds),'evidence_references':';'.join(set(d['reviewer1_evidence_reference']+';'+d['reviewer2_evidence_reference'])),'adjudication_status':'not_started'})
    write('processed/stage5c_adjudication_worksheet.csv',adjud,afields)
    now=datetime.now(timezone.utc).isoformat(); common=len(s1&s2)
    agreement={'stage':'5C','reviewer1_rows':len(r1),'reviewer2_rows':len(r2),'same_case_id_set':s1==s2,'common_case_ids':common,'reviewer1_duplicate_ids':[k for k,v in c1.items() if v>1],'reviewer2_duplicate_ids':[k for k,v in c2.items() if v>1],'missing_from_reviewer1':sorted(s2-s1),'missing_from_reviewer2':sorted(s1-s2),'missing_evidence_references_reviewer1':sum(not x.get('evidence_references','') for x in r1),'missing_evidence_references_reviewer2':sum(not x.get('evidence_references','') for x in r2),'missing_reviewer_ids_reviewer1':sum(not x.get('reviewer_id','') for x in r1),'missing_reviewer_ids_reviewer2':sum(not x.get('reviewer_id','') for x in r2),'missing_rationales_reviewer1':sum(not x.get('annotation_rationale','') for x in r1),'missing_rationales_reviewer2':sum(not x.get('annotation_rationale','') for x in r2),'fields':stats,'overall_interpretation':'Agreement cannot be calculated meaningfully because both worksheets contain no submitted labels. Blank values are missing annotations, not agreement.','benchmark_frozen':False,'adjudication_complete':False}
    (ROOT/'reports/stage5c_interannotator_agreement.json').write_text(json.dumps(agreement,indent=2),encoding='utf-8')
    summary={'pair_rows':len(pairs),'valid_pair_decisions':sum(x['decision_valid'] and bool(x['decision']) for x in pair_valid),'missing_pair_decisions':sum(not x['decision'] for x in pair_valid),'invalid_pair_decisions':sum(not x['decision_valid'] for x in pair_valid),'rationale_present':sum(x['evidence_reference_present'] for x in pair_valid),'confirmed_reposts':sum(x['decision']=='confirmed_repost' for x in pair_valid),'probable_copy':sum(x['decision']=='probable_copy' for x in pair_valid),'unresolved':sum(x['decision']=='unresolved' for x in pair_valid),'automatic_lineage_conversion':False,'interpretation':'Lineage decisions are not available; no candidates were converted automatically.'}
    (ROOT/'reports/stage5c_lineage_review_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    log={'stage':'5C','created_utc':now,'inputs':['stage5b_reviewer1_worksheet.csv','stage5b_reviewer2_worksheet.csv','stage5b_lineage_pair_review.csv'],'outputs':['stage5c_annotation_validation.csv','stage5c_interannotator_agreement.json','stage5c_disagreement_report.csv','stage5c_adjudication_worksheet.csv','stage5c_lineage_review_summary.json'],'reviewer_submissions_complete':False,'adjudication_complete':False,'benchmark_frozen':False,'previous_outputs_modified':False,'automated_predictions_used_as_ground_truth':False}
    (ROOT/'reports/stage5c_execution_log.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
    print(json.dumps({'common_cases':common,'disagreements':len(disagreements),'pairs':len(pairs),'benchmark_frozen':False},indent=2))
if __name__=='__main__':main()
