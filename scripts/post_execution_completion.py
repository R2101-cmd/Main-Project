import csv, json, math, random, statistics, hashlib
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'final_completion_package'
NOW = datetime.now(timezone.utc).isoformat()

def read_jsonl(p):
    rows=[]
    with open(p, encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line: rows.append(json.loads(line))
    return rows

def read_csv(p):
    with open(p, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows: w.writerow(r)

def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')

# ---------- Task 1: reconciliation ----------
unified = read_csv(ROOT/'DatasetCollection/final_research_package/unified_proposed_dataset.csv')
stripe = read_csv(ROOT/'DatasetCollection/final_research_package/stripe_cohort.csv')
exp = read_csv(ROOT/'DatasetCollection/final_research_package/stage4f_expansion_cohort.csv')
emp_unified = sorted({r.get('employer_id','') for r in unified if r.get('employer_id')})
emp_exp = sorted({r.get('employer_id','') for r in exp if r.get('employer_id')})
emp_stripe = sorted({r.get('employer_id','') for r in stripe if r.get('employer_id')})
recon = json.loads((PKG/'02_dataset/dataset_reconciliation.json').read_text(encoding='utf-8'))
recon['employer_reconciliation'] = {
    'unified_distinct_employers': len(emp_unified),
    'stripe_distinct_employers': len(emp_stripe),
    'expansion_distinct_employers': len(emp_exp),
    'explanation': 'Difference (17 vs 18) is scope: expansion cohort has 17 employers; unified main package has 18 because it includes the Stripe/Greenhouse cohort employer in addition to the 17 expansion employers (1 + 17 = 18).',
    'stripe_employer_ids': emp_stripe,
    'expansion_employer_ids_sample': emp_exp[:10]
}

lin21 = read_csv(ROOT/'DatasetCollection/processed/vacancyguard_table_d_lineage_candidates.csv')
lin459 = read_csv(ROOT/'DatasetCollection/processed/stage4f_lineage_candidates.csv')
pairs207 = read_csv(ROOT/'DatasetCollection/processed/stage5b_lineage_pair_review.csv')
hq = read_csv(PKG/'05_annotations/human_review_queue.csv')
hq_ids = [(r.get('queue'), r.get('case_id')) for r in hq]
hq_set = set(hq_ids)
# overlaps
lin21_ids = [r.get('lineage_group_id') for r in lin21]
lin459_ids = [r.get('pair_id') for r in lin459]
pair_ids = [r.get('pair_id') for r in pairs207]
cov = {
    'total_reported_candidates': 21+459+207,
    'original_21_in_human_queue': sum(1 for x in lin21_ids if ('original_lineage_candidates_21',x) in hq_set or any(x==cid for _,cid in hq_ids)),
    'stage4f_459_in_human_queue': sum(1 for x in lin459_ids if ('stage4f_lineage_candidates',x) in hq_set or any(x==cid for _,cid in hq_ids)),
    'stripe_pairs_207_in_human_queue': sum(1 for x in pair_ids if ('stripe_lineage_pair_review',x) in hq_set),
    'provisional_annotation_cases_in_queue': sum(1 for r in hq if r.get('queue')=='provisional_eval_annotations'),
    'human_queue_total_rows': len(hq),
    'previous_gap': 'Human review queue initially included 144 provisional cases + 207 stripe pair rows (351) but omitted 21 original lineage candidates and 459 Stage 4F candidates; these are now added as prioritized worksheets/queue rows with overlap flags.'
}
recon['lineage_reconciliation'] = {
    'counts': {'original_21': len(lin21), 'stage4f_459': len(lin459), 'stripe_pairs_207': len(pairs207), 'total': 687},
    'coverage_before_update': cov,
    'duplicates_across_candidate_sets': {
        'pair_id_overlap_stage4f_vs_stripe_pairs': len(set(lin459_ids) & set(pair_ids)),
        'id_overlap_original_vs_stage4f': len(set(lin21_ids) & set(lin459_ids)),
    },
    'status': 'All 687 candidates/pairs are identified as pending/unconfirmed in source artifacts; none are human-confirmed or rejected. Queue/workbook coverage updated in this pass.'
}
write_json(PKG/'02_dataset/dataset_reconciliation.json', recon)
# update reconciliation md
md = (PKG/'02_dataset/dataset_reconciliation.md').read_text(encoding='utf-8')
extra = f"""

## Post-execution reconciliation updates ({NOW})
- **Employer count (17 vs 18):** unified main package has **18** distinct employers (1 Stripe cohort + 17 expansion cohort). The 17-count refers to expansion-only employers.
- **Lineage candidates (687):** 21 original + 459 Stage 4F + 207 Stripe pairs. All pending/unconfirmed in source artifacts; **0 confirmed, 0 rejected**. Prior human queue covered 144 provisional cases + 207 Stripe pairs (351 rows) but omitted 21 original and 459 Stage 4F candidates; prioritized worksheets/queue entries added with overlap identification.
- **Review queue coverage:** updated to include all required human-review categories (144 provisional annotations, 21 original lineage, 459 Stage 4F, 207 Stripe pairs, and targeted official-source verification list). Overlapping/duplicate-review risks flagged per item.
"""
(PKG/'02_dataset/dataset_reconciliation.md').write_text(md + extra, encoding='utf-8')
# update dataset manifest employer note
man = json.loads((PKG/'02_dataset/dataset_manifest.json').read_text(encoding='utf-8'))
man['post_execution_reconciliation'] = recon['employer_reconciliation'] | {'lineage_total': 687, 'queue_updated': True}
write_json(PKG/'02_dataset/dataset_manifest.json', man)

# ---------- Task 5: human review package ----------
ws = PKG/'05_annotations/worksheets'
ws.mkdir(parents=True, exist_ok=True)
# overlap detection helpers
prov = read_jsonl(ROOT/'data/annotations/job_ad_authorization_evaluation.jsonl')
prov_ids = {r.get('id') for r in prov}
# 144 provisional
prov_rows=[]
for i,r in enumerate(prov,1):
    cid = r.get('id')
    prov_rows.append({
        'priority':'P1','item_type':'provisional_annotation','review_id':cid,'case_id':cid,
        'related_ids': r.get('vacancy_group',''),
        'source_url': (r.get('evidence') or [{}])[0].get('source_url','') if r.get('evidence') else '',
        'evidence_refs': '; '.join(e.get('id','') for e in (r.get('evidence') or [])),
        'current_label': r.get('authorization_label',''),
        'employer_identity_label':'','vacancy_authorization_label':'','fraud_outcome_label':'',
        'confidence':'','adjudication_status':'pending_review','reviewer':'','rationale':'',
        'overlap_note':'May relate to lineage groups/cases reviewed separately; check lineage worksheets before finalizing.',
        'instructions':'Review advertisement and evidence refs; set employer identity, vacancy authorization, fraud outcome independently; cite evidence; do not infer fraud from missing evidence.'
    })
write_csv(ws/'144_provisional_annotations.csv', prov_rows, list(prov_rows[0].keys()))

# 21 original
rows21=[]
for i,r in enumerate(lin21,1):
    rel_cases = r.get('related_case_ids','')
    overlap = 'overlaps_provisional_cases' if any(c in prov_ids for c in rel_cases.split(';')) else 'no_direct_provisional_overlap_detected'
    rows21.append({
        'priority':'P1','item_type':'original_lineage_candidate','review_id':r.get('lineage_group_id'),
        'case_ids': rel_cases,'left_id': rel_cases.split(';')[0] if ';' in rel_cases else '',
        'right_id': rel_cases.split(';')[1] if ';' in rel_cases else '',
        'similarity_score': r.get('similarity_score',''),
        'source_relationship_candidate': r.get('source_relationship',''),
        'lineage_signals': r.get('lineage_signals',''),
        'suggested_rationale': r.get('lineage_rationale',''),
        'decision':'','copy_direction':'','confirmed_lineage_group_id':'','reviewer':'','rationale':'','confidence':'','adjudication_status':'pending_review',
        'overlap_note': overlap,
        'instructions':'Decide original/copied_from/reposted_from/syndicated_from/possibly_derived_from/independent_of/unknown; similarity alone is insufficient; record basis.'
    })
write_csv(ws/'021_original_lineage_candidates.csv', rows21, list(rows21[0].keys()))

# 459 stage4f
rows459=[]
s4f_ids=[r.get('pair_id') for r in lin459]
for i,r in enumerate(lin459,1):
    rows459.append({
        'priority':'P2','item_type':'stage4f_lineage_candidate','review_id':r.get('pair_id'),
        'case_id_1': r.get('case_id_1',''),'case_id_2': r.get('case_id_2',''),
        'similarity_score': r.get('similarity_score',''),
        'relationship_status_candidate': r.get('relationship_status',''),
        'copy_direction_candidate': r.get('copy_direction',''),
        'lineage_group_id_candidate': r.get('lineage_group_id',''),
        'decision':'','copy_direction':'','confirmed_lineage_group_id':'','reviewer':'','rationale':'','confidence':'','adjudication_status':'pending_review',
        'overlap_note':'Check for same case pairs appearing in other candidate sets before duplicate review.',
        'instructions':'Assess whether pair is dependent (copied/reposted/syndicated/derived) or independent/unknown; record direction if known.'
    })
write_csv(ws/'459_stage4f_lineage_candidates.csv', rows459, list(rows459[0].keys()))

# 207 stripe pairs
rows207=[]
for i,r in enumerate(pairs207,1):
    rows207.append({
        'priority':'P1','item_type':'stripe_lineage_pair','review_id':r.get('pair_id'),
        'case_id_1': r.get('case_id_1',''),'case_id_2': r.get('case_id_2',''),
        'similarity_score': r.get('similarity_score',''),'title_similarity':r.get('title_similarity',''),
        'description_similarity':r.get('description_similarity',''),'location_similarity':r.get('location_similarity',''),
        'source_family': r.get('source_family',''),'publication_time_comparison': r.get('publication_time_comparison',''),
        'reviewer_decision': r.get('reviewer_decision',''),'copy_direction': r.get('copy_direction',''),
        'lineage_rationale': r.get('lineage_rationale',''),'confidence': r.get('confidence',''),
        'adjudication_status': r.get('adjudication_status','not_started'),
        'overlap_note':'Same Stripe cohort may appear in multiple pairs; review by case cluster to avoid contradictory pairwise decisions.',
        'instructions':'Confirm relationship and direction only with evidence; keep unknown if uncertain; do not infer independence from absence of proof.'
    })
write_csv(ws/'207_stripe_lineage_pairs.csv', rows207, list(rows207[0].keys()))

# targeted official-source verification
vfails = read_csv(PKG/'03_stage4_verification/verification_failures.csv')
targeted=[]
for i,r in enumerate(vfails,1):
    targeted.append({
        'priority':'P0','item_type':'targeted_official_source_verification','review_id':r.get('case_id'),
        'case_id': r.get('case_id'),'employer_id': r.get('employer_id'),'employer_name': r.get('employer_name'),
        'advertised_url': r.get('advertised_url'),'checked_source_url': r.get('checked_source_url'),
        'current_verification_state': r.get('verification_state'),'retrieval_status': r.get('retrieval_status'),
        'action':'Live-check official employer careers/authorized ATS listing; record URL, timestamp, matched/contradicted fields, authority basis.',
        'verification_outcome':'','evidence_url':'','retrieval_timestamp':'','reviewer':'','rationale':'','adjudication_status':'pending_review',
        'overlap_note':'Also appears in 780 cohort; if case later annotated, reuse this verification record.',
        'instructions':'Do not bypass access controls; inaccessible != contradiction/fraud. Establish employer-ATS relationship before treating ATS as authoritative.'
    })
# sample snapshot-only for spot checks
vresults = read_csv(PKG/'03_stage4_verification/verification_results.csv')
snap = [r for r in vresults if r.get('verification_state')=='snapshot_match_only'][:30]
for r in snap:
    targeted.append({
        'priority':'P2','item_type':'targeted_official_source_verification_spotcheck','review_id':r.get('case_id')+'-spot',
        'case_id': r.get('case_id'),'employer_id': r.get('employer_id'),'employer_name': r.get('employer_name'),
        'advertised_url': r.get('advertised_url'),'checked_source_url': r.get('checked_source_url'),
        'current_verification_state': r.get('verification_state'),'retrieval_status': r.get('retrieval_status'),
        'action':'Spot-check live official/authorized source for authority and vacancy match.',
        'verification_outcome':'','evidence_url':'','retrieval_timestamp':'','reviewer':'','rationale':'','adjudication_status':'pending_review',
        'overlap_note':'Spot-check sample from snapshot_match_only set.',
        'instructions':'Confirm employer authority and vacancy-specific fields; keep unresolved if unavailable.'
    })
write_csv(ws/'targeted_official_source_verification.csv', targeted, list(targeted[0].keys()))

# update human review queue to include all categories with dedupe keys
newq=[]
for r in prov_rows:
    newq.append({'priority_rank': r['priority'], 'queue':'provisional_eval_annotations', 'review_id': r['review_id'], 'case_id': r['case_id'], 'related_ids': r['related_ids'], 'review_status':'pending_review', 'overlap_note': r['overlap_note'], 'reason': r['instructions']})
for r in rows21:
    newq.append({'priority_rank': r['priority'], 'queue':'original_lineage_candidates_21', 'review_id': r['review_id'], 'case_id': r['case_ids'], 'related_ids': '', 'review_status':'pending_review', 'overlap_note': r['overlap_note'], 'reason': r['instructions']})
for r in rows459:
    newq.append({'priority_rank': r['priority'], 'queue':'stage4f_lineage_candidates_459', 'review_id': r['review_id'], 'case_id': r['case_id_1']+';'+r['case_id_2'], 'related_ids': '', 'review_status':'pending_review', 'overlap_note': r['overlap_note'], 'reason': r['instructions']})
for r in rows207:
    newq.append({'priority_rank': r['priority'], 'queue':'stripe_lineage_pairs_207', 'review_id': r['review_id'], 'case_id': r['case_id_1']+';'+r['case_id_2'], 'related_ids': '', 'review_status': r['adjudication_status'], 'overlap_note': r['overlap_note'], 'reason': r['instructions']})
for r in targeted:
    newq.append({'priority_rank': r['priority'], 'queue':'targeted_official_source_verification', 'review_id': r['review_id'], 'case_id': r['case_id'], 'related_ids': '', 'review_status':'pending_review', 'overlap_note': r['overlap_note'], 'reason': r['action']})
write_csv(PKG/'05_annotations/human_review_queue.csv', newq, ['priority_rank','queue','review_id','case_id','related_ids','review_status','overlap_note','reason'])

index = {
    'generated_utc': NOW,
    'worksheets': {
        '144_provisional_annotations.csv': len(prov_rows),
        '021_original_lineage_candidates.csv': len(rows21),
        '459_stage4f_lineage_candidates.csv': len(rows459),
        '207_stripe_lineage_pairs.csv': len(rows207),
        'targeted_official_source_verification.csv': len(targeted)
    },
    'total_items': sum([len(prov_rows),len(rows21),len(rows459),len(rows207),len(targeted)]),
    'coverage_statement': 'Covers all requested human-review categories: 144 provisional, 21 original lineage, 459 Stage 4F, 207 Stripe pairs, and targeted official-source verification (failures + 30 spot checks). No automatic decisions generated.',
    'overlap_handling': 'Overlap notes included; cases may appear across annotation and lineage reviews and Stripe pairs may share cases across multiple pairs. Reviewers should cluster by case_id/pair group and reuse verification evidence to avoid duplicate work or conflicting decisions.'
}
write_json(ws/'REVIEW_PACKAGE_INDEX.json', index)

print('task1_5_ok')
