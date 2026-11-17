import csv,json,sqlite3,hashlib
from pathlib import Path

TARGET=Path(r'C:\Users\Admin\Desktop\Main Project\integration_review\schema_test')
ROOT=Path(r'C:\Users\Admin\Desktop\Cleaned data')
INPUT=Path(r'C:\Users\Admin\Desktop\Main Project\integration_review\provenance_reconciliation\provenance_reconciliation.csv')
csv.field_size_limit(50000000)

SCHEMA='''PRAGMA foreign_keys=ON;
CREATE TABLE cohorts (cohort_id TEXT PRIMARY KEY, cohort_name TEXT NOT NULL, record_scope TEXT NOT NULL, metadata_status TEXT NOT NULL);
CREATE TABLE advertisements (case_id TEXT PRIMARY KEY, cohort_id TEXT NOT NULL REFERENCES cohorts, employer_id TEXT, job_title TEXT, job_description TEXT, location TEXT, source_url TEXT, original_fields_json TEXT NOT NULL, original_row_hash TEXT NOT NULL);
CREATE TABLE employer_identity_claims (claim_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES advertisements, cohort_id TEXT NOT NULL REFERENCES cohorts, label TEXT, evidence_state TEXT, rationale TEXT, claim_status TEXT NOT NULL);
CREATE TABLE vacancy_authorization_claims (claim_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES advertisements, cohort_id TEXT NOT NULL REFERENCES cohorts, label TEXT, evidence_state TEXT, rationale TEXT, claim_status TEXT NOT NULL);
CREATE TABLE source_families (source_family_id TEXT PRIMARY KEY, cohort_id TEXT NOT NULL REFERENCES cohorts, metadata_value TEXT, metadata_status TEXT NOT NULL);
CREATE TABLE source_instances (source_instance_id TEXT PRIMARY KEY, cohort_id TEXT NOT NULL REFERENCES cohorts, source_family_id TEXT REFERENCES source_families, metadata_value TEXT, metadata_status TEXT NOT NULL);
CREATE TABLE retrieval_events (retrieval_event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES advertisements, cohort_id TEXT NOT NULL REFERENCES cohorts, retrieved_at TEXT, http_status TEXT, event_status TEXT NOT NULL);
CREATE TABLE response_hashes (hash_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES advertisements, cohort_id TEXT NOT NULL REFERENCES cohorts, response_hash TEXT, hash_type TEXT NOT NULL, metadata_status TEXT NOT NULL);
CREATE TABLE evidence_records (evidence_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES advertisements, cohort_id TEXT NOT NULL REFERENCES cohorts, evidence_state TEXT, source_independence TEXT, retrieval_independence TEXT, source_url TEXT, official_employer_url TEXT, response_hash TEXT, evidence_status TEXT NOT NULL);
CREATE TABLE lineage_candidates (candidate_id TEXT PRIMARY KEY, cohort_id TEXT NOT NULL REFERENCES cohorts, case_id_1 TEXT NOT NULL REFERENCES advertisements, case_id_2 TEXT NOT NULL REFERENCES advertisements, review_status TEXT NOT NULL, rationale TEXT NOT NULL);
CREATE TABLE confirmed_lineage (confirmed_lineage_id TEXT PRIMARY KEY, cohort_id TEXT NOT NULL REFERENCES cohorts, case_id_1 TEXT NOT NULL REFERENCES advertisements, case_id_2 TEXT NOT NULL REFERENCES advertisements, adjudication_status TEXT NOT NULL, rationale TEXT);
CREATE TABLE provenance_field_sources (case_id TEXT NOT NULL REFERENCES advertisements, cohort_id TEXT NOT NULL REFERENCES cohorts, field_name TEXT NOT NULL, value_present INTEGER NOT NULL, source_file_and_field TEXT NOT NULL, recovery_status TEXT NOT NULL, metadata_status TEXT NOT NULL, PRIMARY KEY(case_id,field_name));
CREATE TABLE missingness (case_id TEXT NOT NULL REFERENCES advertisements, cohort_id TEXT NOT NULL REFERENCES cohorts, field_name TEXT NOT NULL, missing_reason TEXT NOT NULL, PRIMARY KEY(case_id,field_name));'''

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(path,rows,fields):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    TARGET.mkdir(parents=True,exist_ok=True); rows=read(INPUT); fields=list(rows[0]); db=TARGET/'disposable_staging.sqlite3'
    if db.exists(): db.unlink()
    conn=sqlite3.connect(db); conn.executescript(SCHEMA)
    cohort='stripe_greenhouse_780'; conn.execute('INSERT INTO cohorts VALUES (?,?,?,?)',(cohort,'Stripe/Greenhouse','780 reconciled staging rows','main cohort only'))
    write(TARGET/'disposable_staging_import.csv',rows,fields)
    for r in rows:
        cid=r['case_id']; raw=json.dumps({k:r.get(k,'') for k in fields},sort_keys=True,ensure_ascii=False)
        conn.execute('INSERT INTO advertisements VALUES (?,?,?,?,?,?,?,?,?)',(cid,cohort,r.get('employer_id',''),r.get('job_title',''),r.get('job_description',''),r.get('location',''),r.get('source_url',''),raw,hashlib.sha256(raw.encode()).hexdigest()))
        conn.execute('INSERT INTO employer_identity_claims VALUES (?,?,?,?,?,?,?)',(f'EI-{cid}',cid,cohort,None,r.get('evidence_state',''),'', 'not_adjudicated'))
        conn.execute('INSERT INTO vacancy_authorization_claims VALUES (?,?,?,?,?,?,?)',(f'VA-{cid}',cid,cohort,None,r.get('evidence_state',''),'', 'not_adjudicated'))
        if r.get('source_family_id'): conn.execute('INSERT OR IGNORE INTO source_families VALUES (?,?,?,?)',(r['source_family_id'],cohort,r['source_family_id'],'derived_metadata'))
        if r.get('source_instance_id'): conn.execute('INSERT OR IGNORE INTO source_instances VALUES (?,?,?,?,?)',(r['source_instance_id'],cohort,r.get('source_family_id',''),r['source_instance_id'],'derived_metadata'))
        if r.get('retrieval_event_id'): conn.execute('INSERT INTO retrieval_events VALUES (?,?,?,?,?,?)',(r['retrieval_event_id'],cid,cohort,r.get('retrieved_at',''),r.get('http_status',''),'historical_or_derived'))
        conn.execute('INSERT INTO response_hashes VALUES (?,?,?,?,?,?)',(f'RH-{cid}',cid,cohort,r.get('response_hash',''),'greenhouse_response','historical_recovered' if r.get('response_hash') else 'missing'))
        conn.execute('INSERT INTO evidence_records VALUES (?,?,?,?,?,?,?,?,?,?)',(f'EV-{cid}',cid,cohort,r.get('evidence_state',''),r.get('source_independence',''),'',r.get('source_url',''),r.get('official_employer_url',''),r.get('response_hash',''),'observation_not_ground_truth'))
        for key in fields:
            if key in {'case_id','job_title','job_description','location','source_url','employer_id'}:continue
            present=bool(r.get(key,'')); conn.execute('INSERT INTO provenance_field_sources VALUES (?,?,?,?,?,?,?)',(cid,cohort,key,int(present),'provenance_reconciliation.csv:'+key,'recovered_or_derived' if present else 'unavailable','historical_or_derived'))
            if not present:conn.execute('INSERT INTO missingness VALUES (?,?,?,?)',(cid,cohort,key,'not present in reconciled historical artifacts'))
    pair_map={p.get('pair_id'):p for p in read(ROOT/'processed/stage5b_lineage_pair_review.csv')}
    candidate_ids=set()
    for r in rows:
        for pid in filter(None,r.get('lineage_candidate_id','').split(';')):
            p=pair_map.get(pid)
            if p:
                candidate_ids.add(pid);conn.execute('INSERT OR IGNORE INTO lineage_candidates VALUES (?,?,?,?,?,?)',(pid,cohort,p['case_id_1'],p['case_id_2'],'candidate_unadjudicated','Existing Stage 5B candidate; no confirmed lineage.'))
    conn.commit(); q=lambda s:conn.execute(s).fetchone()[0]
    checks={'records_imported':q('select count(*) from advertisements'),'unique_case_ids':q('select count(distinct case_id) from advertisements'),'duplicate_case_ids':q('select count(*)-count(distinct case_id) from advertisements'),'missing_records':780-q('select count(*) from advertisements'),'cohort_rows':q("select count(*) from advertisements where cohort_id='stripe_greenhouse_780'"),'naukri_rows':q("select count(*) from advertisements where cohort_id like '%naukri%'"),'stage4f_rows':q("select count(*) from advertisements where cohort_id like '%stage4f%'"),'candidate_lineage_rows':q('select count(*) from lineage_candidates'),'confirmed_lineage_rows':q('select count(*) from confirmed_lineage'),'retrieval_event_rows':q('select count(*) from retrieval_events'),'missing_retrieval_event_rows':q("select count(*) from missingness where field_name='retrieval_event_id'"),'null_claim_labels':q('select count(*) from vacancy_authorization_claims where label is null')}
    errors=[]
    if checks['records_imported']!=780 or checks['unique_case_ids']!=780 or checks['duplicate_case_ids']!=0 or checks['missing_records']!=0:errors.append('record identity/count failure')
    if checks['naukri_rows'] or checks['stage4f_rows']:errors.append('cohort contamination')
    if checks['candidate_lineage_rows']!=len(candidate_ids):errors.append('candidate lineage preservation failure')
    summary={'schema_version':'vacancyguard_staging_v1','database':str(db),'checks':checks,'expected_candidate_lineage_references':len(candidate_ids),'candidate_lineage_records':sum(bool(r.get('lineage_candidate_id','')) for r in rows),'errors':errors,'production_database_opened':False,'application_modified':False,'source_files_modified':False,'labels_generated':False,'confirmed_lineage_generated':False,'recommendation':'PASS' if not errors and checks['retrieval_event_rows']==0 and checks['confirmed_lineage_rows']==0 else 'CONDITIONAL PASS'}
    (TARGET/'schema_test_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8'); (TARGET/'proposed_staging_schema.sql').write_text(SCHEMA,encoding='utf-8')
    (TARGET/'schema_mapping_report.md').write_text('# Schema mapping report\n\nThe disposable versioned schema preserves advertisements, separate employer-identity and vacancy-authorization claims, observation evidence, source families/instances, nullable retrieval events, response hashes, field-level provenance sources, explicit missingness, candidate lineage, and an empty confirmed-lineage table. Derived metadata is marked as derived. No labels or confirmed lineage are generated.\n',encoding='utf-8')
    (TARGET/'schema_validation_report.md').write_text(f"# Schema compatibility validation report\n\nStatus: **{summary['recommendation']}**\n\n- Records imported: {checks['records_imported']}\n- Unique case IDs: {checks['unique_case_ids']}\n- Duplicate case IDs: {checks['duplicate_case_ids']}\n- Missing records: {checks['missing_records']}\n- Candidate lineage records: {summary['candidate_lineage_records']}\n- Candidate lineage pair references preserved: {checks['candidate_lineage_rows']} of {len(candidate_ids)}\n- Confirmed lineage rows: {checks['confirmed_lineage_rows']}\n- Retrieval event rows: {checks['retrieval_event_rows']}\n- Explicit missing retrieval-event rows: {checks['missing_retrieval_event_rows']}\n- Null authorization labels: {checks['null_claim_labels']}\n- Stage 4F rows: {checks['stage4f_rows']}\n- Naukri rows: {checks['naukri_rows']}\n\nAll 780 rows were imported into a disposable database. Missing provenance remains explicit; no historical retrieval event was invented. Evidence is observation-only, not ground truth. The production database and original files were not accessed for writing.\n",encoding='utf-8')
    (TARGET/'schema_test_readme.md').write_text('# Isolated schema compatibility test\n\nRun the standalone generator from the research workspace. It reads only the 780-row reconciliation CSV and the existing candidate worksheet, creates disposable_staging.sqlite3 in this folder, and never opens the production database, scrapes, imports other cohorts, generates labels, or modifies source files.\n',encoding='utf-8')
    conn.close();print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
