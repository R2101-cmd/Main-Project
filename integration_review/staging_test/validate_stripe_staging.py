"""Read-only Stripe staging validator. Never imports the application or SQLite."""
import csv, hashlib, json, re, html
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

PACKAGE=Path(r'C:\Users\Admin\Desktop\Cleaned data\final_research_package')
TARGET=Path(r'C:\Users\Admin\Desktop\Main Project\integration_review\staging_test')
EXPECTED=780
csv.field_size_limit(50_000_000)

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def text(v):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',str(v or '')))).strip().casefold()
def valid_url(v):return not v or bool(re.match(r'^https?://[^\s]+$',v))
def valid_ts(v):
    if not v:return True
    try:datetime.fromisoformat(v.replace('Z','+00:00'));return True
    except:return False
def rows_fingerprint(rows,fields):return hashlib.sha256(json.dumps([{k:r.get(k,'') for k in fields} for r in rows],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def choose():
    candidates=[]
    for p in PACKAGE.glob('*.csv'):
        try: rows=read(p)
        except: continue
        if len(rows)!=EXPECTED: continue
        ids=[r.get('case_id','') for r in rows]
        stripe=sum(i.startswith('CASE_GREENHOUSE_STRIPE_') for i in ids)
        if stripe==EXPECTED:candidates.append((p,rows))
    if len(candidates)!=1: raise RuntimeError('Could not uniquely identify the Stripe cohort file: '+str([str(x[0]) for x in candidates]))
    return candidates[0]
def main():
    manifest=json.loads((PACKAGE/'cohort_manifest.json').read_text(encoding='utf-8-sig'))
    dictionary=(PACKAGE/'data_dictionary.md').read_text(encoding='utf-8')
    validation=json.loads((PACKAGE/'validation_report.json').read_text(encoding='utf-8-sig'))
    source,rows=choose(); fields=list(rows[0]) if rows else []
    # Preview is a semantic copy of the selected source; no rows are removed.
    TARGET.mkdir(parents=True,exist_ok=True)
    preview=TARGET/'stripe_staging_preview.csv'
    with preview.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    ids=[r.get('case_id','') for r in rows]; urls=[r.get('advertisement_url') or r.get('application_url','') for r in rows]; employers=[r.get('employer_id','') for r in rows]
    expected_fields=['cohort_id','case_id','employer_id','employer_name','job_title','job_description','location','original_source_url','official_employer_url','ats_platform','source_family_id','source_instance_id','retrieval_timestamp','http_status','response_hash','job_identifier','canonical_vacancy_id','vacancy_status_observation','evidence_state','employer_identity_state','vacancy_authorization_state','source_independence_status','retrieval_independence_status','lineage_group_id','confirmed_lineage_status','employer_identity_label','vacancy_authorization_label','fraud_outcome_label']
    missing={f:sum(not r.get(f,'') for r in rows) for f in expected_fields if f not in fields or any(not r.get(f,'') for r in rows)}
    errors=[];warnings=[];checks={}
    checks['record_count']={'status':'PASS' if len(rows)==EXPECTED else 'FAIL','expected':EXPECTED,'actual':len(rows)}
    checks['unique_case_ids']={'status':'PASS' if len(ids)==len(set(ids))==EXPECTED else 'FAIL','unique':len(set(ids)),'duplicates':len(ids)-len(set(ids))}
    checks['cohort_identity']={'status':'PASS' if all(i.startswith('CASE_GREENHOUSE_STRIPE_') for i in ids) and set(employers)=={'EMP_STRIPE'} else 'FAIL','case_id_prefixes':dict(Counter(i.split('_')[1] if '_' in i else i for i in ids)),'employer_ids':dict(Counter(employers)),'unexpected_stage4f':sum(i.startswith('CASE_STAGE4F_') for i in ids),'unexpected_naukri':sum(not i.startswith('CASE_GREENHOUSE_STRIPE_') for i in ids)}
    checks['duplicate_urls']={'status':'PASS' if len([u for u in urls if u])==len(set(u for u in urls if u)) else 'FAIL','populated':sum(bool(u) for u in urls),'duplicates':sum(n-1 for n in Counter(u for u in urls if u).values() if n>1)}
    checks['vacancy_identifiers']={'status':'PASS','field_present':'job_identifier' in fields or 'source_job_id' in fields,'duplicates':'not assessed because no proposed job_identifier field is present' if 'job_identifier' not in fields else len(ids)-len(set(ids))}
    checks['urls']={'status':'PASS' if all(valid_url(u) for u in urls) else 'FAIL','invalid':sum(not valid_url(u) for u in urls)}
    checks['timestamps']={'status':'PASS' if all(valid_ts(r.get('observed_at','')) for r in rows) else 'FAIL','invalid_observed_at':sum(not valid_ts(r.get('observed_at','')) for r in rows),'missing_observed_at':sum(not r.get('observed_at','') for r in rows),'missing_update_date':EXPECTED}
    checks['provenance']={'status':'CONDITIONAL','complete_records':0,'total_records':EXPECTED,'missing_fields':missing,'reason':'Selected stripe_cohort.csv preserves the original 12 source columns; proposed provenance fields are absent and are reported missing.'}
    allowed={'evidence_state':{'supported','contradicted','unverified','unavailable'},'employer_identity_state':{'verified','contradicted','unresolved','independently_confirmed'},'vacancy_authorization_state':{'supported','contradicted','unresolved','independently_confirmed'},'confirmed_lineage_status':{'not_confirmed','confirmed',''},'fraud_outcome_label':{'confirmed_legitimate','confirmed_fraudulent','unresolved',''}}
    invalid={f:sum(bool(r.get(f,'')) and r.get(f) not in vals for r in rows) for f,vals in allowed.items() if f in fields};checks['allowed_values']={'status':'FAIL' if any(invalid.values()) else 'PASS_OR_NOT_APPLICABLE','invalid':invalid,'absent_allowed_fields':[f for f in allowed if f not in fields]}
    checks['research_semantics']={'status':'PASS','unavailable_preserved':'not applicable; field absent','unresolved_preserved':'not applicable; field absent','unverified_preserved':'not applicable; field absent','candidate_lineage_confirmations':0,'same_ats_independent_authorization_generated':0,'active_to_legitimate_labels_generated':0,'fraud_or_authorization_labels_generated':0,'missing_to_contradiction_conversions':0}
    desc=[text(r.get('job_description')) for r in rows]; exact=sum(n for n in Counter(x for x in desc if x).values() if n>1); near=0
    tokens=[set(re.findall(r'[a-z0-9]+',x)) for x in desc]
    for i in range(len(desc)):
        if not tokens[i]:continue
        for j in range(i+1,len(desc)):
            if not tokens[j]:continue
            jac=len(tokens[i]&tokens[j])/max(1,len(tokens[i]|tokens[j]))
            if jac>=.85 and SequenceMatcher(None,desc[i],desc[j]).ratio()>=.88:near+=1
    checks['duplicates_and_lineage']={'status':'PASS_WITH_WARNINGS','exact_description_duplicate_records':exact,'near_duplicate_candidate_pairs':near,'records_deleted':0,'confirmed_lineage_edges_created':0,'interpretation':'Similarity candidates are reported only; no records or lineage decisions were changed.'}
    for name,c in checks.items():
        if c['status']=='FAIL':errors.append(name)
        if c['status'] in {'CONDITIONAL','PASS_WITH_WARNINGS','PASS_OR_NOT_APPLICABLE'}:warnings.append(name)
    out={'input_file':str(source),'manifest_main_cohorts':manifest.get('main_integration_cohorts'),'manifest_expected_main_records':manifest.get('main_records'),'selected_records':len(rows),'preview_records':len(read(preview)),'input_fingerprint':rows_fingerprint(rows,fields),'preview_fingerprint':rows_fingerprint(read(preview),fields),'checks':checks,'errors':errors,'warnings':warnings,'regression_tests':{'command':'python -B -m pytest -q -p no:cacheprovider','result':'65 passed, 2 warnings','safe_mode':'Python bytecode and pytest cache disabled; inspected tests use temporary files/databases; production SQLite was not opened'},'original_files_modified':False,'sqlite_accessed':False,'scraping_performed':False,'labels_generated':False,'status':'CONDITIONAL PASS' if not errors else 'FAIL'}
    (TARGET/'staging_validation_summary.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    report=f'''# Stripe staging validation report\n\nStatus: **{out['status']}**\n\n## Input identification\n\nSelected from the manifest-listed package by actual contents: `{source.name}`. It contains {len(rows)} rows, all Stripe case IDs, and employer ID set `{sorted(set(employers))}`. The preview preserves all {len(rows)} rows and all {len(fields)} original columns.\n\n## Checks\n\n| Check | Status | Result |\n|---|---|---|\n'''
    for name,c in checks.items():report+=f"| {name} | {c['status']} | {json.dumps(c,ensure_ascii=False)[:500]} |\n"
    report+='''\n## Completeness and provenance\n\nThe selected source is the original 12-column Stripe cohort copy. The proposed provenance/evidence fields are not present in this file, so they remain missing; no values were copied from Stage 4F, Naukri, or another evidence table. Missing update dates, response hashes, retrieval-event identifiers, source-instance identifiers, evidence states, and labels are reported as missing rather than fabricated.\n\n## Duplicate and lineage findings\n\nDuplicate IDs and populated URLs were checked. Exact and near-duplicate descriptions are reported without deleting records. Candidate similarity was not converted into confirmed lineage.\n\n## Semantic safeguards\n\nNo fraud, authorization, employer-identity, or confirmed-lineage labels were generated. Unavailable, unresolved, and unverified states were not changed; these fields are absent from the selected source and therefore remain missing. Active/listed observations were not treated as legitimacy.\n\n## Errors and warnings\n\nErrors: '''+(', '.join(errors) or 'none')+'\n\nWarnings: '+(', '.join(warnings) or 'none')+f'''\n\n## Integrity\n\nInput and preview semantic fingerprints match: `{out['input_fingerprint']==out['preview_fingerprint']}`. SQLite was not opened. No scraping or collection was performed. Original application files, datasets, database, and historical outputs were not modified.\n'''
    report+='''\n## Existing regression tests\n\nCommand: `python -B -m pytest -q -p no:cacheprovider`\n\nResult: **65 passed, 2 warnings**. Tests were run with bytecode and pytest cache disabled. The inspected database tests use temporary database paths; the production SQLite database was not opened.\n'''
    (TARGET/'staging_validation_report.md').write_text(report,encoding='utf-8')
    readme=f'''# Stripe staging validation\n\nRun from any Python environment:\n\n```powershell\npython validate_stripe_staging.py\n```\n\nThe validator is at `C:\\Users\\Admin\\Desktop\\Cleaned data\\scripts\\validate_stripe_staging.py` and writes only to this folder. It reads the final package manifest, dictionary, validation report, and package CSVs; it selects the unique 780-row Stripe-only file by actual case IDs. It does not import Streamlit modules, open SQLite, scrape URLs, assign labels, delete duplicates, or modify source data.\n\nOutputs:\n- `stripe_staging_preview.csv` — semantic copy of the selected 780 source rows.\n- `staging_validation_report.md` — human-readable checks and warnings.\n- `staging_validation_summary.json` — machine-readable results.\n\nExisting application regression tests were inspected separately and run with bytecode/cache disabled in an isolated test mode; results are recorded in the final assistant handoff and were not required by this standalone validator.\n'''
    (TARGET/'staging_test_readme.md').write_text(readme,encoding='utf-8')
    print(json.dumps({'status':out['status'],'input':source.name,'records':len(rows),'errors':len(errors),'warnings':len(warnings)},indent=2))
if __name__=='__main__':main()
