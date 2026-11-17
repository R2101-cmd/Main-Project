"""Create a deterministic synthetic benchmark with labels isolated from inputs."""
import hashlib, json, random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research-data'/'phase2_v1'/'synthetic'/'controlled_v2'
SEED=20261203
JOBS=[("People Operations Analyst","Northwind Care","Portland","full-time"),("Cloud Security Engineer","Juniper Works","Austin","contract"),("Clinical Data Coordinator","Harbor Health","Boston","part-time"),("Revenue Operations Lead","Cedar Systems","Denver","full-time"),("Laboratory Technician","Mosaic Bio","Raleigh","contract"),("Customer Support Specialist","Bluebird Transit","Chicago","full-time"),("Product Researcher","Summit Learning","Remote","part-time"),("Network Administrator","Redwood Energy","Phoenix","full-time"),("Payroll Associate","Common Ground Foods","Atlanta","contract"),("Quality Engineer","Silverline Devices","Seattle","full-time")]
SCENARIOS=[
 ('independent_official_support','supported','supported'),('multi_repost_support','supported','supported'),('explicit_support_variant','supported','supported'),('support_with_copied_reposts','supported','supported'),('official_field_contradiction','contradicted','contradicted'),('copied_false_agreement','contradicted','supported'),('similar_title_wrong_vacancy','contradicted','unresolved'),('official_id_conflict','contradicted','contradicted'),('conflicting_sources','unresolved','contradicted'),('unknown_lineage','unresolved','supported'),('missing_lineage','unresolved','supported'),('stale_snapshot','unresolved','unresolved')]
rng=random.Random(SEED); inputs=[]; labels=[]
for j,(scenario,label,b_state) in enumerate(SCENARIOS):
 for rep in range(5):
  job_idx=(j*3+rep*7)%len(JOBS); title,emp,loc,etype=JOBS[job_idx]; family=f"grp-{j:02d}-{rep//2:02d}" if scenario in {'copied_false_agreement','multi_repost_support'} else f"grp-{j:02d}-{rep:02d}"
  variation=[f"{title} at {emp}. The role supports daily operations, maintains accurate records, collaborates with colleagues and prepares clear reports.",f"{emp} is hiring a {title}. Responsibilities include coordinating routine work, documenting results, communicating with teams and improving service quality.",f"Join {emp} as a {title}. Candidates organize work, maintain reliable documentation, solve practical problems and share findings with partners.",f"{title} — {emp}. Work with internal teams, track assigned tasks, maintain quality standards and communicate updates.",f"{emp} seeks a {title} to support team projects, keep information current, address operational issues and deliver dependable results."][rep]
  if scenario=='incomplete_description': variation=f"{title} at {emp}. Apply through the employer careers page."
  if scenario=='similar_title_wrong_vacancy': variation=f"{title} at {emp}. This role handles separate projects and reports to a different department; it is not the vacancy described in the source."
  # No IDs, labels or scenario names in input. The text is the complete shared input for each method.
  ad={"text":variation,"job_title":title,"employer_name":emp,"location":loc,"salary_text":"","employment_type":etype}
  evid=[]
  def add(state,relation,group,review='adjudicated',retrieval='available',verification=None, salt='x'):
   evid.append({"id":f"E{len(evid)}-{salt}","evidence_state":state,"source_relationship":relation,"lineage_review_status":review,"lineage_group":group,"retrieval_status":retrieval,"verification_status":verification,"source_url":f"https://source.invalid/{family}/{salt}","matched_fields":["employer","title"] if state=='supported' else [],"contradicted_fields":["job_id"] if state=='contradicted' else []})
  if scenario=='independent_official_support': add('supported','independent',family)
  elif scenario=='official_field_contradiction': add('contradicted','independent',family)
  elif scenario=='copied_false_agreement':
   add('supported','copied_derived',family,salt='original'); add('supported','copied_derived',family,salt='repost1'); add('supported','copied_derived',family,salt='repost2')
  elif scenario=='multi_repost_support':
   add('supported','copied_derived',family,salt='source'); add('supported','copied_derived',family,salt='copy1'); add('supported','copied_derived',family,salt='copy2')
  elif scenario=='conflicting_sources': add('supported','independent',family+'a',salt='official'); add('contradicted','independent',family+'b',salt='portal')
  elif scenario=='unknown_lineage': add('supported','unknown',None,'unresolved')
  elif scenario=='missing_lineage': evid.append({"id":"ev-missing","evidence_state":"supported","source_url":f"https://source.invalid/{family}/m"})
  elif scenario=='stale_snapshot': add('supported','independent',family,verification='snapshot_match_only')
  elif scenario=='unavailable_sources': add('unavailable','unknown',None,'unresolved','unavailable')
  elif scenario=='incomplete_description': add('unverified','unknown',None,'unresolved')
  elif scenario=='similar_title_wrong_vacancy': add('contradicted','independent',family)
  elif scenario=='explicit_support_variant': add('supported','independent',family)
  elif scenario=='support_with_copied_reposts': add('supported','copied_derived',family,salt='source'); add('supported','copied_derived',family,salt='repost')
  elif scenario=='official_id_conflict': add('contradicted','independent',family)
  elif scenario in {'stale_snapshot','unavailable_sources','incomplete_description','insufficient_sources'}: pass
  elif scenario=='insufficient_sources': add('unverified','unknown',None,'unresolved')
  cid=f"case-{len(inputs):03d}"
  inputs.append({**ad,"evidence":evid,"synthetic":True})
  labels.append({"case_id":cid,"vacancy_group":family,"scenario":scenario,"label":label,"repeated_repost_group":family if scenario in {'copied_false_agreement','multi_repost_support'} else None})
# deterministic group split: assign whole groups, preserve labels in each partition
groups={}
for i,m in enumerate(labels): groups.setdefault(m['vacancy_group'],[]).append(i)
group_ids=list(groups); rng.shuffle(group_ids); development=set(); test=set(); counts={"development":set(),"test":set()}
for group in group_ids:
 ix=groups[group]; current='test' if len(test)<len(inputs)*.3 else 'development'
 # group label homogeneous by construction; greedily balance expected label coverage
 lab=labels[ix[0]]['label']
 if lab not in counts['test'] or (current=='development' and lab not in counts['development']): current='test' if lab not in counts['test'] else 'development'
 (test if current=='test' else development).update(ix); counts[current].add(lab)
for part,ixs in [('development',development),('test',test)]:
 for i in ixs: labels[i]['partition']=part
OUT.mkdir(parents=True,exist_ok=True)
with (OUT/'model_inputs.jsonl').open('w',encoding='utf-8') as f:
 for r in inputs:f.write(json.dumps(r,ensure_ascii=False)+'\n')
with (OUT/'evaluation_labels.jsonl').open('w',encoding='utf-8') as f:
 for r in labels:f.write(json.dumps(r,ensure_ascii=False)+'\n')
manifest={"name":"controlled_v2","synthetic":True,"records":len(inputs),"seed":SEED,"classes":{k:sum(x['label']==k for x in labels) for k in ('supported','contradicted','unresolved')},"scenario_counts":{s:sum(x['scenario']==s for x in labels) for s,_,_ in SCENARIOS},"inputs_file":"model_inputs.jsonl","labels_file":"evaluation_labels.jsonl","labels_separated":True,"group_split":"whole vacancy/source-lineage groups; deterministic stratified greedy split","splits":{p:sum(x['partition']==p for x in labels) for p in ('development','test')},"original_benchmarks_preserved":True}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
