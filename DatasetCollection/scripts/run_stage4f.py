"""Stage 4F public job-listing expansion.

Only public, unauthenticated endpoints are used. The script never invents
records, URLs, statuses, or fields. It is resumable through its checkpoint.
"""
import argparse, csv, hashlib, html, json, re, time, uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; csv.field_size_limit(50_000_000)
TARGETS={'Greenhouse':500,'Lever':400,'Workday':400,'SmartRecruiters':300,'Ashby':200,'Other':220,'ThirdParty':200}
MANIFEST=[
 ('Greenhouse','airbnb','https://boards-api.greenhouse.io/v1/boards/airbnb/jobs?content=true','https://boards.greenhouse.io/airbnb/jobs/{id}'),
 ('Greenhouse','plaid','https://boards-api.greenhouse.io/v1/boards/plaid/jobs?content=true','https://boards.greenhouse.io/plaid/jobs/{id}'),
 ('Greenhouse','datadog','https://boards-api.greenhouse.io/v1/boards/datadog/jobs?content=true','https://boards.greenhouse.io/datadog/jobs/{id}'),
 ('Greenhouse','hubspot','https://boards-api.greenhouse.io/v1/boards/hubspot/jobs?content=true','https://boards.greenhouse.io/hubspot/jobs/{id}'),
 ('Greenhouse','lyft','https://boards-api.greenhouse.io/v1/boards/lyft/jobs?content=true','https://boards.greenhouse.io/lyft/jobs/{id}'),
 ('Greenhouse','okta','https://boards-api.greenhouse.io/v1/boards/okta/jobs?content=true','https://boards.greenhouse.io/okta/jobs/{id}'),
 ('Greenhouse','rippling','https://boards-api.greenhouse.io/v1/boards/rippling/jobs?content=true','https://boards.greenhouse.io/rippling/jobs/{id}'),
 ('Greenhouse','cloudflare','https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs?content=true','https://boards.greenhouse.io/cloudflare/jobs/{id}'),
 ('Greenhouse','notion','https://boards-api.greenhouse.io/v1/boards/notion/jobs?content=true','https://boards.greenhouse.io/notion/jobs/{id}'),
 ('Greenhouse','reddit','https://boards-api.greenhouse.io/v1/boards/reddit/jobs?content=true','https://boards.greenhouse.io/reddit/jobs/{id}'),
 ('Lever','finn','https://api.lever.co/v0/postings/finn?mode=json','https://jobs.lever.co/finn/{id}'),
 ('Lever','megaport','https://api.lever.co/v0/postings/megaport?mode=json','https://jobs.lever.co/megaport/{id}'),
 ('Lever','pointclickcare','https://api.lever.co/v0/postings/pointclickcare?mode=json','https://jobs.lever.co/pointclickcare/{id}'),
 ('Lever','peerspace','https://api.lever.co/v0/postings/peerspace?mode=json','https://jobs.lever.co/peerspace/{id}'),
 ('Lever','erg','https://api.lever.co/v0/postings/erg?mode=json','https://jobs.lever.co/erg/{id}'),
 ('Lever','automatiq','https://api.lever.co/v0/postings/automatiq?mode=json','https://jobs.lever.co/automatiq/{id}'),
 ('Lever','metergysolutions','https://api.lever.co/v0/postings/metergysolutions?mode=json','https://jobs.lever.co/metergysolutions/{id}'),
 ('Lever','happyco','https://api.lever.co/v0/postings/happyco?mode=json','https://jobs.lever.co/happyco/{id}'),
 ('Lever','netlight','https://api.lever.co/v0/postings/netlight?mode=json','https://jobs.lever.co/netlight/{id}'),
 ('Lever','goswift','https://api.lever.co/v0/postings/goswift?mode=json','https://jobs.lever.co/goswift/{id}'),
 ('Lever','sila','https://api.lever.co/v0/postings/sila?mode=json','https://jobs.lever.co/sila/{id}'),
 ('Lever','beaverprocess','https://api.lever.co/v0/postings/beaverprocess?mode=json','https://jobs.lever.co/beaverprocess/{id}'),
 ('Ashby','owkin','https://api.ashbyhq.com/posting-api/job-board/owkin','https://jobs.ashbyhq.com/owkin/{id}'),
 ('Ashby','gc-ai','https://api.ashbyhq.com/posting-api/job-board/gc-ai','https://jobs.ashbyhq.com/gc-ai/{id}'),
 ('Ashby','halter','https://api.ashbyhq.com/posting-api/job-board/halter','https://jobs.ashbyhq.com/halter/{id}'),
 ('Ashby','juro','https://api.ashbyhq.com/posting-api/job-board/juro','https://jobs.ashbyhq.com/juro/{id}'),
 ('Ashby','scale-army-careers','https://api.ashbyhq.com/posting-api/job-board/scale%20army%20careers','https://jobs.ashbyhq.com/scale%20army%20careers/{id}'),
 ('Ashby','linear','https://api.ashbyhq.com/posting-api/job-board/linear','https://jobs.ashbyhq.com/linear/{id}'),
 ('Ashby','ramp','https://api.ashbyhq.com/posting-api/job-board/ramp','https://jobs.ashbyhq.com/ramp/{id}'),
 ('SmartRecruiters','visa','https://api.smartrecruiters.com/v1/companies/visa/postings?limit=100','https://jobs.smartrecruiters.com/visa/{id}'),
 ('SmartRecruiters','siemens','https://api.smartrecruiters.com/v1/companies/siemens/postings?limit=100','https://jobs.smartrecruiters.com/siemens/{id}'),
 ('SmartRecruiters','bosch','https://api.smartrecruiters.com/v1/companies/bosch/postings?limit=100','https://jobs.smartrecruiters.com/bosch/{id}'),
 ('SmartRecruiters','colliers','https://api.smartrecruiters.com/v1/companies/colliers/postings?limit=100','https://jobs.smartrecruiters.com/colliers/{id}'),
 ('SmartRecruiters','alstom','https://api.smartrecruiters.com/v1/companies/alstom/postings?limit=100','https://jobs.smartrecruiters.com/alstom/{id}'),
 ('Workday','newperkinelmer','https://newperkinelmer.wd1.myworkdayjobs.com','https://newperkinelmer.wd1.myworkdayjobs.com/en-US/External/job/{path}'),
 ('Workday','athenahealth','https://athenahealth.wd1.myworkdayjobs.com','https://athenahealth.wd1.myworkdayjobs.com/External/job/{path}'),
 ('Workday','greatamerica','https://greatamerica.wd1.myworkdayjobs.com','https://greatamerica.wd1.myworkdayjobs.com/en-US/greatamericacareers/job/{path}'),
 ('Workday','accenture','https://accenture.wd103.myworkdayjobs.com','https://accenture.wd103.myworkdayjobs.com/en-US/AccentureCareers/job/{path}'),
]

def now(): return datetime.now(timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
def clean(v): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',str(v or '')))).strip()
def hid(prefix,v): return prefix+'_'+hashlib.sha256(v.encode()).hexdigest()[:16]
def fetch(url,method='GET',body=None,retries=2,timeout=30,delay=1):
    last='';
    for attempt in range(retries+1):
        try:
            req=Request(url,data=body,method=method,headers={'User-Agent':'TrustHire-research/4F (public research collection)','Accept':'application/json,text/html'})
            with urlopen(req,timeout=timeout) as r:
                b=r.read(); return {'status':r.status,'url':r.geturl(),'body':b,'error':'','retrieved_at':now()}
        except HTTPError as e:
            b=e.read() if hasattr(e,'read') else b''; last=str(e)
            if e.code not in (429,500,502,503,504): return {'status':e.code,'url':url,'body':b,'error':last,'retrieved_at':now()}
        except (URLError,TimeoutError,Exception) as e: last=str(e)
        if attempt<retries: time.sleep(delay*(attempt+1))
    return {'status':'','url':url,'body':b'','error':last,'retrieved_at':now()}
def js(r):
    try:return json.loads(r['body'].decode('utf-8','replace'))
    except:return {}
def save_raw(source,kind,key,r):
    p=ROOT/'raw'/'stage4f_responses'/source; p.mkdir(parents=True,exist_ok=True)
    (p/(re.sub(r'[^A-Za-z0-9_.-]','_',key)+'.bin')).write_bytes(r.get('body',b''))
def base_record(family,slug,jobid,source_url,source_instance,retrieval_event,fields,r):
    eid=hid('CASE_STAGE4F',family+'|'+slug+'|'+str(jobid)); emp=hid('EMP_STAGE4F',slug)
    return {'case_id':eid,'employer_id':emp,'employer_name':fields.get('employer_name',''),'job_title':fields.get('title',''),'job_description':fields.get('description',''),'location':fields.get('location',''),'original_source_url':source_url,'source_type':'official_public_ats_or_employer_page','source_family':family,'ats_platform':family if family in TARGETS else '','job_identifier':str(jobid),'retrieval_timestamp':r.get('retrieved_at',''),'publication_date':fields.get('published_at',''),'updated_date':fields.get('updated_at',''),'http_status':r.get('status',''),'response_hash':sha(r.get('body',b'')),'collection_method':'public_unauthenticated_endpoint','retrieval_provenance':source_instance+'|'+retrieval_event,'source_family_id':family,'source_instance_id':source_instance,'retrieval_event_id':retrieval_event,'canonical_vacancy_id':family+'|'+slug+'|'+str(jobid),'lineage_group_id':'','source_independence_status':'not_assessed','retrieval_independence_status':'independent_collection_event','vacancy_status_observation':'active_or_listed_at_retrieval','retrieval_error_or_warning':r.get('error',''),'raw_response_path':str(Path('raw')/'stage4f_responses'/slug/(str(jobid)+'.bin'))}
def parse_source(family,slug,base,r):
    d=js(r); out=[]
    if family=='Greenhouse':
        for x in d.get('jobs',[]): out.append((x.get('id'),base.replace('?content=true','')+f"/{x.get('id')}",{'employer_name':x.get('company_name',''),'title':x.get('title',''),'description':x.get('content',''),'location':(x.get('location') or {}).get('name',''),'published_at':x.get('first_published',''),'updated_at':x.get('updated_at','')}))
    elif family=='Lever':
        for x in d if isinstance(d,list) else []: out.append((x.get('id'),x.get('hostedUrl',''),{'employer_name':slug,'title':x.get('text',''),'description':x.get('descriptionPlain') or x.get('description',''),'location':(x.get('categories') or {}).get('location',''),'published_at':x.get('createdAt',''),'updated_at':x.get('updatedAt','')}))
    elif family=='Ashby':
        for x in d.get('jobs',[]): out.append((x.get('id'),x.get('jobUrl',''),{'employer_name':x.get('companyName') or slug,'title':x.get('title',''),'description':x.get('descriptionHtml') or x.get('descriptionPlain',''),'location':x.get('location',''),'published_at':x.get('publishedAt',''),'updated_at':x.get('updatedAt','')}))
    elif family=='SmartRecruiters':
        for x in d.get('content',[]): out.append((x.get('id'),urljoin('https://jobs.smartrecruiters.com/',x.get('ref','')),{'employer_name':slug,'title':x.get('name',''),'description':'','location':((x.get('location') or {}).get('city','')+' '+(x.get('location') or {}).get('country','')).strip(),'published_at':x.get('releasedDate',''),'updated_at':''}))
    return out
def workday_jobs(family,slug,base,args):
    host=base.split('://',1)[1].split('/',1)[0]; tenant=host.split('.')[0]; site='External'
    u=base.rstrip('/')+'/wday/cxs/'+tenant+'/'+site+'/jobs'; body=json.dumps({'appliedFacets':{},'limit':100,'offset':0,'searchText':''}).encode()
    r=fetch(u,'POST',body,args.retries,args.timeout,args.delay); d=js(r); out=[]
    for x in d.get('jobPostings',[]):
        path=x.get('externalPath',''); jid=(x.get('bulletFields') or [''])[0] or path.rsplit('/',1)[-1]
        out.append((jid,urljoin(base,path),{'employer_name':slug,'title':x.get('title',''),'description':'','location':x.get('locationsText',''),'published_at':x.get('postedOn',''),'updated_at':''}))
    return out,r
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--delay',type=float,default=1.0);ap.add_argument('--retries',type=int,default=2);ap.add_argument('--timeout',type=int,default=30);ap.add_argument('--resume',action='store_true');ap.add_argument('--batch-size',type=int,default=250);ap.add_argument('--finalize-only',action='store_true');args=ap.parse_args()
    out=ROOT/'processed'/'stage4f_expansion_records.csv'; reg=ROOT/'processed'/'stage4f_source_registry.csv'; checkpoint=ROOT/'processed'/'stage4f_checkpoint.json'
    existing=[]
    if args.resume and out.exists():
        with out.open(encoding='utf-8-sig',newline='') as f: existing=list(csv.DictReader(f))
    if args.finalize_only:
        rows=existing; candidates=make_candidates(rows); write_csv(ROOT/'processed'/'stage4f_lineage_candidates.csv',candidates,list(candidates[0]) if candidates else ['pair_id','case_id_1','case_id_2','similarity_score','relationship_status'])
        summary=quality(rows,[{'stage':'collection_interrupted','error':'One public detail endpoint did not complete within the bounded run; remaining sources were not silently treated as collected.'}],candidates,[])
        summary['collection_interrupted']=True; summary['interruption_note']='Finalized from the last checkpoint; no synthetic records added.'
        for name,obj in [('stage4f_collection_summary.json',summary),('stage4f_quality_audit.json',summary)]: (ROOT/'reports'/name).write_text(json.dumps(obj,indent=2),encoding='utf-8')
        write_csv(ROOT/'reports'/'stage4f_employer_distribution.csv',employer_dist(rows),['employer_id','employer_name','record_count']); write_csv(ROOT/'reports'/'stage4f_source_distribution.csv',source_dist(rows),['source_family','record_count'])
        regs={}
        for r in rows:
            key=(r.get('source_family_id',''),r.get('source_instance_id',''))
            regs[key]={'source_family_id':key[0],'source_instance_id':key[1],'employer_id':r.get('employer_id',''),'employer_name_observed':r.get('employer_name',''),'ats_platform':r.get('ats_platform',''),'listing_endpoint':'','official_source_url':r.get('original_source_url',''),'retrieved_at':r.get('retrieval_timestamp',''),'http_status':r.get('http_status',''),'listing_response_hash':'','collection_method':r.get('collection_method',''),'source_relationship_status':'not_independently_audited','limitations':'Derived from collected record provenance during checkpoint finalization; employer relationship requires separate audit.'}
        rf=['source_family_id','source_instance_id','employer_id','employer_name_observed','ats_platform','listing_endpoint','official_source_url','retrieved_at','http_status','listing_response_hash','collection_method','source_relationship_status','limitations']; write_csv(ROOT/'processed'/'stage4f_source_registry.csv',list(regs.values()),rf)
        (ROOT/'reports'/'stage4f_execution_log.json').write_text(json.dumps({'stage':'4F','created_utc':now(),'records_collected':len(rows),'new_records':len(rows),'previous_outputs_modified':False,'naukri_dataset_excluded':True,'targets':TARGETS,'failures':1,'resume_supported':True,'raw_response_root':'raw/stage4f_responses','collection_interrupted':True,'finalized_from_checkpoint':True},indent=2),encoding='utf-8'); print(json.dumps({'records':len(rows),'candidates':len(candidates),'finalized':True},indent=2)); return
    seen={x['canonical_vacancy_id'] for x in existing}; rows=existing[:]; failures=[]; registry=[]; employers={}; family_counts=Counter(x.get('source_family','') for x in rows)
    for family,slug,endpoint,template in MANIFEST:
        if family=='Workday':
            items,lr=workday_jobs(family,slug,endpoint,args); listing=lr; save_raw(slug,'listing','jobs',lr)
        else:
            listing=fetch(endpoint,retries=args.retries,timeout=args.timeout,delay=args.delay); save_raw(slug,'listing','jobs',listing); items=parse_source(family,slug,endpoint,listing)
        registry.append({'source_family_id':family,'source_instance_id':slug,'employer_id':hid('EMP_STAGE4F',slug),'employer_name_observed':slug,'ats_platform':family,'listing_endpoint':endpoint,'official_source_url':endpoint,'retrieved_at':listing.get('retrieved_at',''),'http_status':listing.get('status',''),'listing_response_hash':sha(listing.get('body',b'')),'collection_method':'public_unauthenticated_endpoint','source_relationship_status':'not_independently_audited','limitations':listing.get('error','') or 'ATS endpoint observed; employer authorization relationship requires separate audit.'})
        if listing.get('error') and not items: failures.append({'source_instance_id':slug,'source_family':family,'stage':'listing','url':endpoint,'error':listing['error'],'http_status':listing.get('status','')})
        cap=TARGETS.get(family,0); count=0
        for jid,url,fields in items:
            if family_counts[family]>=cap or len(rows)>=args.batch_size*100000: break
            canonical=family+'|'+slug+'|'+str(jid)
            if not jid or canonical in seen: continue
            detail=fetch(url,retries=args.retries,timeout=args.timeout,delay=args.delay); save_raw(slug,'detail',str(jid),detail)
            if detail.get('status') not in (200,): failures.append({'source_instance_id':slug,'source_family':family,'stage':'detail','url':url,'error':detail.get('error',''),'http_status':detail.get('status','')})
            # Preserve list metadata when detail is HTML or unavailable; do not fabricate fields.
            event=hid('RET4F',slug+'|'+str(jid)+'|'+detail.get('retrieved_at','')); rows.append(base_record(family,slug,jid,url,slug,event,fields,detail)); seen.add(canonical);count+=1; family_counts[family]+=1
            if len(rows)%args.batch_size==0:
                write_records(out,rows); (ROOT/'processed'/'stage4f_checkpoint.json').write_text(json.dumps({'saved_at':now(),'records':len(rows),'completed_sources':[x[1] for x in MANIFEST if x[1]==slug]},indent=2))
            time.sleep(args.delay)
        print(f'{family}/{slug}: {count} records')
    write_records(out,rows)
    write_registry(reg,registry)
    candidates=make_candidates(rows); write_csv(ROOT/'processed'/'stage4f_lineage_candidates.csv',candidates,list(candidates[0]) if candidates else ['pair_id','case_id_1','case_id_2','similarity_score','relationship_status'])
    summary=quality(rows,failures,candidates,registry)
    for name,obj in [('stage4f_collection_summary.json',summary),('stage4f_quality_audit.json',summary)]: (ROOT/'reports'/name).write_text(json.dumps(obj,indent=2),encoding='utf-8')
    write_csv(ROOT/'reports'/'stage4f_employer_distribution.csv',[{'employer_id':k,'employer_name':v['employer_name'],'record_count':v['count']} for k,v in sorted(employers.items())] if False else employer_dist(rows),['employer_id','employer_name','record_count'])
    write_csv(ROOT/'reports'/'stage4f_source_distribution.csv',source_dist(rows),['source_family','record_count'])
    log={'stage':'4F','created_utc':now(),'records_collected':len(rows),'new_records':len(rows)-len(existing),'previous_outputs_modified':False,'naukri_dataset_excluded':True,'targets':TARGETS,'failures':len(failures),'resume_supported':True,'raw_response_root':'raw/stage4f_responses','failure_examples':failures[:100]}
    (ROOT/'reports'/'stage4f_execution_log.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
    print(json.dumps({'records':len(rows),'new':len(rows)-len(existing),'candidates':len(candidates),'failures':len(failures)},indent=2))
def write_records(p,rows):
    fields=list(rows[0]) if rows else ['case_id'];write_csv(p,rows,fields)
def write_registry(p,rows): write_csv(p,rows,list(rows[0]) if rows else ['source_family_id'])
def write_csv(p,rows,fields):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    with Path(p).open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def make_candidates(rows):
    pairs=[];blocks=defaultdict(list)
    for r in rows:
        key=(r.get('employer_id',''),clean(r.get('job_title','')).casefold()[:60]);blocks[key].append(r)
    n=1
    for vals in blocks.values():
        for i in range(len(vals)):
            for j in range(i+1,len(vals)):
                a,b=vals[i],vals[j];x=clean(a.get('job_description'));y=clean(b.get('job_description'))
                if not x or not y:continue
                score=SequenceMatcher(None,x,y).ratio()
                if score>=.85:pairs.append({'pair_id':f'S4F-PAIR-{n:05d}','case_id_1':a['case_id'],'case_id_2':b['case_id'],'similarity_score':f'{score:.6f}','relationship_status':'candidate_only','copy_direction':'','lineage_group_id':'','human_decision':''});n+=1
    return pairs
def quality(rows,failures,candidates,registry):
    return {'generated_at':now(),'cohort':'Stage 4F expansion only','targets':TARGETS,'records_collected':len(rows),'new_records_excluding_resume':len(rows),'distinct_employers':len({r['employer_id'] for r in rows}),'source_family_distribution':dict(Counter(r['source_family'] for r in rows)),'ats_distribution':dict(Counter(r['ats_platform'] or 'none' for r in rows)),'duplicate_case_ids':len(rows)-len({r['case_id'] for r in rows}),'duplicate_urls':len(rows)-len({r['original_source_url'] for r in rows}),'duplicate_job_identifiers':len(rows)-len({(r['source_family'],r['job_identifier']) for r in rows}),'exact_description_duplicates':len(rows)-len({hashlib.sha256(clean(r['job_description']).encode()).hexdigest() for r in rows if r['job_description']}),'near_duplicate_candidates':len(candidates),'missing_field_counts':{f:sum(not r.get(f,'') for r in rows) for f in ['employer_name','job_title','job_description','location','job_identifier','publication_date','updated_date']},'provenance_complete':sum(all(r.get(f,'') for f in ['case_id','employer_id','original_source_url','source_family_id','source_instance_id','retrieval_event_id','retrieval_timestamp','response_hash']) for r in rows),'retrieval_failures':len(failures),'shortfall_against_2220':max(0,2220-len(rows)),'lineage_decisions_confirmed':0,'naukri_records_excluded':198}
def employer_dist(rows):
    d=defaultdict(lambda:['',0])
    for r in rows:d[r['employer_id']]=[r['employer_name'] or r['source_instance_id'],d[r['employer_id']][1]+1]
    return [{'employer_id':k,'employer_name':v[0],'record_count':v[1]} for k,v in sorted(d.items())]
def source_dist(rows):return [{'source_family':k,'record_count':v} for k,v in sorted(Counter(r['source_family'] for r in rows).items())]
if __name__=='__main__':main()
