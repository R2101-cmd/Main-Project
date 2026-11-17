import csv
from src.datasets.descriptive_integration import load_and_summarize

FIELDS={"stripe":["case_id","employer_id","job_title","job_description","location"],"stage4f":["case_id","employer_id","job_title","job_description","location","canonical_vacancy_id","source_independence_status"],"unified":["case_id","cohort_id","employer_id","canonical_vacancy_id","evidence_state","lineage_group_id","confirmed_lineage_status","vacancy_authorization_label"],"naukri":["case_id","employer_id","job_title","job_description","location"]}
def write(path,kind,rows):
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=FIELDS[kind]);w.writeheader();w.writerows(rows)
def test_exact_reconciliation_separate_naukri_and_nulls(tmp_path):
 paths={k:tmp_path/f'{k}.csv' for k in FIELDS}
 write(paths['stripe'],'stripe',[dict(case_id='S1',employer_id='E',job_title='',job_description='d',location='L')])
 write(paths['stage4f'],'stage4f',[dict(case_id='F1',employer_id='E2',job_title='T',job_description='d',location='L',canonical_vacancy_id='cv',source_independence_status='not_assessed')])
 write(paths['unified'],'unified',[dict(case_id='S1',cohort_id='stripe',employer_id='E',canonical_vacancy_id='',evidence_state='independent_official_confirmation',lineage_group_id='',confirmed_lineage_status='',vacancy_authorization_label='') ,dict(case_id='F1',cohort_id='stage4f',employer_id='E2',canonical_vacancy_id='cv',evidence_state='',lineage_group_id='',confirmed_lineage_status='',vacancy_authorization_label='')])
 write(paths['naukri'],'naukri',[dict(case_id='N1',employer_id='NE',job_title='N',job_description='d',location='L')])
 r=load_and_summarize(stripe_path=paths['stripe'],stage4f_path=paths['stage4f'],unified_path=paths['unified'],naukri_path=paths['naukri'],evidence_path=None,lineage_candidate_paths=[])
 assert r['reconciliation']['unified_exact_union_match'] and r['reconciliation']['naukri_kept_separate']
 assert r['reconciliation']['main_advertisement_sum']==2
 assert next(x for x in r['descriptive_rows'] if x['dimension']=='missing_job_title')['count']==2
 assert r['descriptive_rows']

def test_duplicate_cross_cohort_ids_reconciliation_detected(tmp_path):
 paths={k:tmp_path/f'{k}.csv' for k in FIELDS}
 base=[dict(case_id='X',employer_id='E',job_title='T',job_description='D',location='L')]
 write(paths['stripe'],'stripe',base)
 write(paths['stage4f'],'stage4f',[{**base[0],"canonical_vacancy_id":"cv","source_independence_status":"not_assessed"}])
 write(paths['unified'],'unified',[dict(case_id='X',cohort_id='both',employer_id='E',canonical_vacancy_id='cv',evidence_state='',lineage_group_id='',confirmed_lineage_status='',vacancy_authorization_label='')])
 write(paths['naukri'],'naukri',base)
 r=load_and_summarize(stripe_path=paths['stripe'],stage4f_path=paths['stage4f'],unified_path=paths['unified'],naukri_path=paths['naukri'],evidence_path=None,lineage_candidate_paths=[])
 assert r['reconciliation']['stripe_stage4f_overlap']==1
 assert r['reconciliation']['naukri_overlap_main']==1
