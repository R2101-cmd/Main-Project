"""Read-only integration and descriptive summaries for research CSV cohorts."""
from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path

REQUIRED = {
 "stripe": {"case_id","employer_id","job_title","job_description","location"},
 "stage4f": {"case_id","employer_id","job_title","job_description","location","canonical_vacancy_id","source_independence_status"},
 "unified": {"case_id","cohort_id","employer_id","canonical_vacancy_id","evidence_state","lineage_group_id","confirmed_lineage_status","vacancy_authorization_label"},
 "naukri": {"case_id","employer_id","job_title","job_description","location"},
}

def read_csv(path):
 with Path(path).open(encoding="utf-8-sig",newline="") as f:
  reader=csv.DictReader(f)
  if not reader.fieldnames: raise ValueError(f"CSV has no header: {path}")
  return list(reader.fieldnames),list(reader)

def _counts(rows, field): return dict(Counter((r.get(field) or "").strip() or "<missing>" for r in rows))
def _miss(rows,field): return sum(not (r.get(field) or "").strip() for r in rows)

def _dups(rows,field):
 values=[(r.get(field) or "").strip() for r in rows if (r.get(field) or "").strip()]
 return len(values)-len(set(values))

def load_and_summarize(*,stripe_path,stage4f_path,unified_path,naukri_path,evidence_path,lineage_candidate_paths):
 inputs={"stripe":stripe_path,"stage4f":stage4f_path,"unified":unified_path,"naukri":naukri_path}
 files={}; tables={}; errors=[]
 for name,path in inputs.items():
  cols,rows=read_csv(path); files[name]={"path":str(path),"columns":cols,"records":len(rows)};tables[name]=rows
  missing=REQUIRED[name]-set(cols)
  if missing: errors.append(f"{name}: required columns missing: {sorted(missing)}")
  ids=[(r.get("case_id") or "").strip() for r in rows]
  if any(not x for x in ids): errors.append(f"{name}: blank case_id")
  if len(ids)!=len(set(ids)): errors.append(f"{name}: duplicate case_id")
 if errors: raise ValueError("; ".join(errors))
 stripe_ids={r["case_id"].strip() for r in tables["stripe"]}; stage_ids={r["case_id"].strip() for r in tables["stage4f"]}; unified_ids={r["case_id"].strip() for r in tables["unified"]}; naukri_ids={r["case_id"].strip() for r in tables["naukri"]}
 union=stripe_ids|stage_ids
 ucoh=_counts(tables["unified"],"cohort_id")
 reconciliation={"stripe_count":len(stripe_ids),"stage4f_count":len(stage_ids),"expected_main_count":len(union),"unified_count":len(unified_ids),"stripe_stage4f_overlap":len(stripe_ids&stage_ids),"unified_missing_ids":sorted(union-unified_ids),"unified_extra_ids":sorted(unified_ids-union),"unified_exact_union_match":unified_ids==union,"unified_cohort_counts":ucoh,"naukri_count":len(naukri_ids),"naukri_overlap_main":len(naukri_ids&union),"naukri_kept_separate":not bool(naukri_ids&union),"main_advertisement_sum":len(stripe_ids)+len(stage_ids)}
 main=tables["unified"]
 summaries=[]
 for field in ("cohort_id","employer_id","source_family_id","source_type","ats_platform","platform_type","source_independence_status","retrieval_independence_status","evidence_state","employer_identity_state","vacancy_authorization_state","fraud_outcome_label","adjudication_status"):
  if any(field in r for r in main):
   for value,count in _counts(main,field).items(): summaries.append({"dataset":"main","dimension":field,"value":value,"count":count})
 for name in ("main",):
  rows=main
  for field in ("job_title","location","canonical_vacancy_id","lineage_group_id","case_id"):
   summaries.append({"dataset":name,"dimension":"missing_"+field,"value":"<summary>","count":_miss(rows,field)})
 summaries.append({"dataset":"main","dimension":"duplicate_case_ids","value":"<summary>","count":_dups(main,"case_id")})
 naukri=tables["naukri"]
 for field in ("employer_id","platform_type"):
  summaries.extend({"dataset":"naukri","dimension":field,"value":v,"count":n} for v,n in _counts(naukri,field).items())
 for field in ("job_title","location","case_id"):
  summaries.append({"dataset":"naukri","dimension":"missing_"+field,"value":"<summary>","count":_miss(naukri,field)})
 # Evidence/lineage artifacts remain separate from advertisement counts.
 evidence=[]
 if evidence_path:
  _,evidence=read_csv(evidence_path)
 ev_summary={"records":len(evidence),"case_ids_matched_to_main":sum((r.get("case_id") or "").strip() in union for r in evidence),"states":_counts(evidence,"evidence_classification") if evidence and "evidence_classification" in evidence[0] else _counts(evidence,"evidence_state"),"snapshot_only_count":sum((r.get("evidence_classification") or r.get("verification_status") or "").strip() in {"snapshot_match_only","independent_official_confirmation"} for r in evidence),"historical_confirmation_source_value_count":sum((r.get("evidence_classification") or "").strip()=="independent_official_confirmation" for r in evidence),"independently_adjudicated_authorization_count":sum((r.get("verification_status") or "").strip()=="independently_supported" for r in evidence),"unavailable_count":sum((r.get("evidence_classification") or r.get("evidence_state") or "").strip() in {"unavailable","inaccessible"} for r in evidence),"unresolved_count":sum((r.get("evidence_classification") or r.get("evidence_state") or "").strip() in {"unresolved","independently_unresolved"} for r in evidence)}
 lin=[]
 for p in lineage_candidate_paths:
  _,rs=read_csv(p);lin.extend({**x,"_artifact":str(p)} for x in rs)
 lin_summary={"candidate_records":len(lin),"candidate_pairs":sum(1 for r in lin if r.get("case_id_1") or r.get("related_case_ids")),"confirmed_relationship_records":sum((r.get("adjudication_status") or r.get("lineage_review_status") or "").strip().lower()=="adjudicated" and (r.get("reviewer_decision") or r.get("source_relationship") or "").strip().lower() in {"copied_derived","independent","original"} for r in lin),"missing_group_id":sum(not (r.get("lineage_group_id") or "").strip() for r in lin),"not_assessed_or_candidate":sum((r.get("lineage_review_status") or r.get("adjudication_status") or "").strip().lower() in {"","not_started","not_assessed","automated candidate","candidate","candidate_only"} for r in lin)}
 return {"files":files,"reconciliation":reconciliation,"descriptive_rows":summaries,"evidence_summary":ev_summary,"lineage_summary":lin_summary,"main_record_count":len(main),"naukri_record_count":len(naukri)}
