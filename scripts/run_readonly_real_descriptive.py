import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.datasets.descriptive_integration import load_and_summarize

def main():
 p=argparse.ArgumentParser();p.add_argument('--stripe',required=True);p.add_argument('--stage4f',required=True);p.add_argument('--unified',required=True);p.add_argument('--naukri',required=True);p.add_argument('--evidence',required=True);p.add_argument('--lineage',action='append',required=True);p.add_argument('--output-dir',default='final_completion_package/real_descriptive_v1');a=p.parse_args()
 out=ROOT/a.output_dir;out.mkdir(parents=True,exist_ok=True)
 result=load_and_summarize(stripe_path=a.stripe,stage4f_path=a.stage4f,unified_path=a.unified,naukri_path=a.naukri,evidence_path=a.evidence,lineage_candidate_paths=a.lineage)
 (out/'cohort_reconciliation.json').write_text(json.dumps(result['reconciliation'],indent=2),encoding='utf-8')
 (out/'evidence_state_summary.json').write_text(json.dumps(result['evidence_summary'],indent=2),encoding='utf-8')
 (out/'lineage_summary.json').write_text(json.dumps(result['lineage_summary'],indent=2),encoding='utf-8')
 (out/'descriptive_statistics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 with (out/'dataset_inventory.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=['dataset','path','records','columns']);w.writeheader();[w.writerow({'dataset':k,**v,'columns':json.dumps(v['columns'])}) for k,v in result['files'].items()]
 with (out/'descriptive_statistics.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=['dataset','dimension','value','count']);w.writeheader();w.writerows(result['descriptive_rows'])
 report='''# Read-only real dataset descriptive analysis\n\nThis package integrates the Stripe (780) and Stage 4F (2,200) advertisement cohorts in memory and checks the proposed unified CSV by exact case-ID set equality. Naukri is analyzed separately. Source files are read only; evidence and lineage candidate tables are summarized separately.\n\nEvidence-state values are preserved as source classifications. Historical `independent_official_confirmation` is not interpreted as independently adjudicated vacancy authorization. Lineage pairs remain candidates unless their source review fields explicitly indicate adjudication.\n\n## Limits\n\nThe cohort labels are blank, pending or unreviewed; therefore this is descriptive analysis only. It does not provide real-world accuracy, precision, recall, F1, or false-assurance performance. Canonical vacancy IDs are source normalization identifiers, not confirmed lineage.\n'''
 (out/'methodology_limitations.md').write_text(report,encoding='utf-8');print(json.dumps({'output_dir':str(out),'main_records':result['main_record_count'],'naukri_records':result['naukri_record_count'],'reconciliation':result['reconciliation'],'evidence':result['evidence_summary'],'lineage':result['lineage_summary']},indent=2))
if __name__=='__main__':main()
