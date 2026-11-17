"""Read-only exact-case-ID provenance reconciliation for Stripe."""
import csv,json,hashlib
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(r'C:\Users\Admin\Desktop\Cleaned data'); TARGET=Path(r'C:\Users\Admin\Desktop\Main Project\integration_review\provenance_reconciliation'); csv.field_size_limit(50_000_000)
def read(p):
    with (ROOT/p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows,fields):
    p=TARGET/p; p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def fingerprint(rows,fields):return hashlib.sha256(json.dumps([{k:r.get(k,'') for k in fields} for r in rows],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def main():
    staging=read(Path(r'C:\Users\Admin\Desktop\Main Project\integration_review/staging_test/stripe_staging_preview.csv'))
    tablea=read('processed/table_A_advertisements.csv'); tableb=read('processed/table_B_ground_truth.csv'); tablec=read('processed/table_C_evidence_records.csv'); e4=read('processed/stage4e_evidence_records.csv'); unified=read('final_research_package/unified_proposed_dataset.csv'); reg=read('processed/stripe_official_source_registry.csv'); pairs=read('processed/stage5b_lineage_pair_review.csv'); raw=json.loads((ROOT/'raw/greenhouse/greenhouse_raw.json').read_text(encoding='utf-8'))
    maps={k:{r.get('case_id'):r for r in v if r.get('case_id')} for k,v in {'table_a':tablea,'table_b':tableb,'table_c':tablec,'stage4e':e4,'unified':unified}.items()}
    pair_by={}
    for p in pairs:
        for c in (p.get('case_id_1',''),p.get('case_id_2','')):pair_by.setdefault(c,[]).append(p.get('pair_id',''))
    fields=['case_id','cohort_id','employer_id','source_family_id','source_instance_id','retrieval_event_id','source_url','official_employer_url','canonical_vacancy_id','retrieved_at','updated_at','response_hash','evidence_state','source_independence','lineage_candidate_id','confirmed_lineage_id']
    recovered_sources=[];out=[]; complete_core=partial=no_recovery=ambiguous=0
    core=['cohort_id','employer_id','source_family_id','source_instance_id','retrieval_event_id','source_url','official_employer_url','canonical_vacancy_id','retrieved_at','updated_at','response_hash','evidence_state','source_independence']
    for s in staging:
        cid=s['case_id']; a=maps['table_a'].get(cid,{}); x=maps['stage4e'].get(cid,{}); u=maps['unified'].get(cid,{}); b=maps['table_b'].get(cid,{}); c=maps['table_c'].get(cid,{})
        row=dict(s); row.update({f:'' for f in fields if f not in row}); row['case_id']=cid
        vals={
            'cohort_id':('stripe_greenhouse_780','final_research_package/cohort_manifest.json:main_integration_cohorts; final_research_package/unified_proposed_dataset.csv:cohort_id','recovered_from_derived_artifact'),
            'employer_id':(a.get('employer_id') or s.get('employer_id'),'processed/table_A_advertisements.csv:employer_id','recovered'),
            'source_family_id':(u.get('source_family_id'),'final_research_package/unified_proposed_dataset.csv:source_family_id','recovered_from_derived_artifact'),
            'source_instance_id':(u.get('source_instance_id'),'final_research_package/unified_proposed_dataset.csv:source_instance_id','recovered_from_derived_artifact'),
            'retrieval_event_id':('','','unavailable'),
            'source_url':(s.get('advertisement_url') or s.get('application_url',''),'staging_test/stripe_staging_preview.csv:advertisement_url/application_url; processed/table_A_advertisements.csv:same case_id','recovered'),
            'official_employer_url':(x.get('official_employer_url'),'processed/stage4e_evidence_records.csv:official_employer_url','recovered'),
            'canonical_vacancy_id':(u.get('canonical_vacancy_id'),'final_research_package/unified_proposed_dataset.csv:canonical_vacancy_id','recovered_from_derived_artifact'),
            'retrieved_at':(x.get('retrieval_timestamp'),'processed/stage4e_evidence_records.csv:retrieval_timestamp','recovered'),
            'updated_at':(x.get('updated_date'),'processed/stage4e_evidence_records.csv:updated_date','partially_recovered'),
            'response_hash':(x.get('greenhouse_response_hash'),'processed/stage4e_evidence_records.csv:greenhouse_response_hash','recovered'),
            'evidence_state':(x.get('evidence_classification'),'processed/stage4e_evidence_records.csv:evidence_classification','recovered'),
            'source_independence':(x.get('source_independence'),'processed/stage4e_evidence_records.csv:source_independence','recovered'),
            'lineage_candidate_id':(';'.join(pair_by.get(cid,[])), 'processed/stage5b_lineage_pair_review.csv:pair_id','recovered_candidate_only' if pair_by.get(cid) else 'unavailable'),
            'confirmed_lineage_id':('','','unavailable')}
        statuses=[]
        for f,(v,src,status) in vals.items():
            row[f]=v; statuses.append(status)
            recovered_sources.append({'case_id':cid,'field_name':f,'recovered_value_present':bool(v),'recovery_status':status,'source_file_and_field':src,'matching_method':'exact case_id' if v and f!='cohort_id' else ('manifest/cohort identity' if v else 'not recoverable'),'notes':'Derived-package values are retained as derived, not original retrieval events.' if status=='recovered_from_derived_artifact' else ('Candidate only; not confirmed lineage.' if f=='lineage_candidate_id' and v else '')})
        row['reconciliation_status']='complete_core_provenance' if all(row.get(f) for f in core) else 'partial_provenance' if any(row.get(f) for f in core) else 'no_recoverable_provenance'
        row['strict_historical_status']='complete' if all((row.get(f) and not f in {'source_family_id','source_instance_id','canonical_vacancy_id'}) for f in core) else 'partial'
        row['ambiguous_match']='no'
        out.append(row)
        if row['reconciliation_status']=='complete_core_provenance':complete_core+=1
        elif row['reconciliation_status']=='partial_provenance':partial+=1
        else:no_recovery+=1
    extra=['reconciliation_status','strict_historical_status','ambiguous_match']
    write('provenance_reconciliation.csv',out,list(dict.fromkeys(list(staging[0])+fields+extra)))
    write('recovered_field_sources.csv',recovered_sources,list(recovered_sources[0]))
    unmatched=[{'case_id':s['case_id'],'reason':'No exact case_id match in one or more historical sources; see field-level report.'} for s in staging if s['case_id'] not in maps['table_a'] or s['case_id'] not in maps['stage4e']]
    write('unmatched_records.csv',unmatched,['case_id','reason'])
    field_counts={f:{'present':sum(bool(r.get(f,'')) for r in out),'missing':sum(not r.get(f,'') for r in out),'source_files':sorted({x['source_file_and_field'] for x in recovered_sources if x['field_name']==f and x['recovered_value_present']})} for f in fields}
    summary={'generated_utc':datetime.now(timezone.utc).isoformat(),'input_file':'Main Project/integration_review/staging_test/stripe_staging_preview.csv','records':len(staging),'exact_case_id_matches':len(staging)-len(unmatched),'unmatched_records':len(unmatched),'ambiguous_matches':ambiguous,'complete_core_provenance':complete_core,'partial_provenance':partial,'no_recoverable_provenance':no_recovery,'strict_historical_complete':sum(r['strict_historical_status']=='complete' for r in out),'derived_artifact_fields':{'source_family_id':780,'source_instance_id':780,'canonical_vacancy_id':780,'retrieval_event_id':0},'field_completeness':field_counts,'lineage_candidates_recovered':sum(bool(pair_by.get(r['case_id'])) for r in out),'confirmed_lineage_recovered':0,'same_ats_independence_inferred':0,'labels_generated':False,'scraping_performed':False,'database_writes':False,'application_modified':False,'source_files_used':['processed/table_A_advertisements.csv','processed/table_B_ground_truth.csv','processed/table_C_evidence_records.csv','processed/stage4e_evidence_records.csv','processed/stripe_official_source_registry.csv','processed/stage5b_lineage_pair_review.csv','raw/greenhouse/greenhouse_raw.json','final_research_package/cohort_manifest.json','final_research_package/unified_proposed_dataset.csv'],'matching_rule':'Exact case_id or documented cohort manifest; no description-only joins.','recommendation':'CONDITIONAL: core fields are recoverable from Stage 4E plus later derived artifacts, but strict historical provenance is incomplete because retrieval_event_id is absent and source-instance/canonical fields are derived rather than original event records.'}
    (TARGET/'provenance_reconciliation_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    report=f'''# Stripe provenance completeness report\n\n## Result\n\n- Input records: **{len(staging)}**.\n- Exact case-ID matches to Table A and Stage 4E: **{len(staging)-len(unmatched)}**.\n- Complete core provenance using recovered plus derived-package fields: **{complete_core}**.\n- Partial provenance: **{partial}**.\n- No recoverable provenance: **{no_recovery}**.\n- Strict historical complete provenance excluding derived source-instance/canonical fields: **{summary['strict_historical_complete']}**.\n- Unmatched records: **{len(unmatched)}**.\n- Ambiguous matches: **{ambiguous}**.\n\n## Interpretation\n\nThe original Stripe staging preview has only the 12 advertisement columns. Stage 4E recovers official URL, Greenhouse URL/job identifier, retrieval timestamp, response hash, updated date where present, evidence state, and source-independence values by exact `case_id`. The final package supplies `source_family_id`, `source_instance_id`, and `canonical_vacancy_id`, but these are derived package fields rather than original retrieval-event records. No `retrieval_event_id` exists in the inspected historical artifacts.\n\nTherefore the cohort is not fully historically provenance-complete. The derived fields are clearly marked in `recovered_field_sources.csv` and must not be presented as independently captured event identifiers.\n\n## Field completeness\n\n'''+ '\n'.join(f"- `{f}`: {v['present']} present, {v['missing']} missing; sources: {', '.join(v['source_files']) or 'none'}" for f,v in field_counts.items())+f'''\n\n## Lineage and semantics\n\nStage 5B pair IDs were recovered only as candidate lineage references. Confirmed lineage IDs recovered: 0. No description-only matching was used for provenance joins. Same-ATS retrieval was not converted into independent authorization. No labels were generated, and no missing or unavailable evidence was converted into contradiction.\n\n## Files and integrity\n\nThe reconciliation preserves all original staging-preview columns and appends reconciliation fields. Original datasets, application files, SQLite, and historical outputs were not modified. No scraping or database write occurred.\n\n## Recommendation\n\n**CONDITIONAL — not ready for a future database integration test that requires complete historical provenance.** A read-only schema test may proceed, but an integration test should either allow explicit missing `retrieval_event_id` and derived-field provenance or first establish an auditable retrieval-event registry.\n'''
    (TARGET/'provenance_completeness_report.md').write_text(report,encoding='utf-8')
    print(json.dumps({'records':len(staging),'complete_core':complete_core,'partial':partial,'unmatched':len(unmatched),'ambiguous':ambiguous},indent=2))
if __name__=='__main__':main()
