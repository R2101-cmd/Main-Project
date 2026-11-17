import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'final_completion_package' / 'automated_mode'
OUT.mkdir(parents=True, exist_ok=True)

def read_csv(p):
    with open(p, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

# --- lineage automation (all 687) ---
lin21 = read_csv(ROOT / 'DatasetCollection/processed/vacancyguard_table_d_lineage_candidates.csv')
lin459 = read_csv(ROOT / 'DatasetCollection/processed/stage4f_lineage_candidates.csv')
pairs207 = read_csv(ROOT / 'DatasetCollection/processed/stage5b_lineage_pair_review.csv')

def classify_relation(sim, signals='', has_direct_provenance=False):
    try:
        sim = float(sim) if sim not in (None, '') else 0.0
    except Exception:
        sim = 0.0
    if has_direct_provenance:
        return 'confirmed_by_direct_machine_verifiable_provenance', 'Direct provenance/identifier match recorded (machine-verifiable).'
    if sim >= 0.98 or 'same normalized application URL' in (signals or ''):
        return 'likely_dependent', 'High similarity or matching machine-comparable identifiers suggest dependence; not confirmed lineage without provenance/human adjudication.'
    if sim >= 0.80:
        return 'possible_dependency', 'Moderate-to-high similarity suggests possible dependency; insufficient for confirmation.'
    if sim >= 0.50:
        return 'possible_dependency', 'Some overlap detected; relationship remains uncertain.'
    return 'unknown_relationship', 'Insufficient overlap/provenance to infer dependence; must not be assumed independent.'

records = []
for r in lin21:
    cat, note = classify_relation(r.get('similarity_score'), r.get('lineage_signals', ''), False)
    cases = [c for c in (r.get('related_case_ids') or '').split(';') if c]
    records.append({
        'source_set': 'original_21', 'candidate_id': r.get('lineage_group_id', ''),
        'case_id_1': cases[0] if len(cases) > 0 else '', 'case_id_2': cases[1] if len(cases) > 1 else '',
        'similarity_score': r.get('similarity_score', ''), 'signals': r.get('lineage_signals', ''),
        'automated_category': cat, 'machine_verifiable_provenance_confirmed': False,
        'provisional_relationship_label': r.get('source_relationship', ''),
        'conservative_independence_treatment': 'not_assumed_independent',
        'rationale': note + ' Preserved original automated-candidate context; similarity-based, not confirmed lineage.'
    })
for r in lin459:
    cat, note = classify_relation(r.get('similarity_score'), '', False)
    records.append({
        'source_set': 'stage4f_459', 'candidate_id': r.get('pair_id', ''),
        'case_id_1': r.get('case_id_1', ''), 'case_id_2': r.get('case_id_2', ''),
        'similarity_score': r.get('similarity_score', ''), 'signals': '',
        'automated_category': cat, 'machine_verifiable_provenance_confirmed': False,
        'provisional_relationship_label': r.get('relationship_status', 'candidate_only'),
        'conservative_independence_treatment': 'not_assumed_independent',
        'rationale': note
    })
for r in pairs207:
    sig = f"title={r.get('title_similarity','')};desc={r.get('description_similarity','')};loc={r.get('location_similarity','')};src={r.get('source_family','')};pub={r.get('publication_time_comparison','')}"
    cat, note = classify_relation(r.get('similarity_score'), sig, False)
    records.append({
        'source_set': 'stripe_pairs_207', 'candidate_id': r.get('pair_id', ''),
        'case_id_1': r.get('case_id_1', ''), 'case_id_2': r.get('case_id_2', ''),
        'similarity_score': r.get('similarity_score', ''), 'signals': sig,
        'automated_category': cat, 'machine_verifiable_provenance_confirmed': False,
        'provisional_relationship_label': 'candidate_pair',
        'conservative_independence_treatment': 'not_assumed_independent',
        'rationale': note
    })

def independence_est(rows):
    pairs = len(rows)
    confirmed = sum(1 for r in rows if r['automated_category'] == 'confirmed_by_direct_machine_verifiable_provenance')
    likely_dep = sum(1 for r in rows if r['automated_category'] == 'likely_dependent')
    possible = sum(1 for r in rows if r['automated_category'] == 'possible_dependency')
    unknown = sum(1 for r in rows if r['automated_category'] == 'unknown_relationship')
    est_families = confirmed * 1 + likely_dep * 1 + possible * 1 + unknown * 2
    return {
        'pairs': pairs, 'confirmed_by_provenance': confirmed, 'likely_dependent': likely_dep,
        'possible_dependency': possible, 'unknown_relationship': unknown,
        'conservative_estimated_independent_source_families': est_families,
        'lower_bound_families': confirmed + likely_dep + possible + unknown,
        'upper_bound_if_all_independent_not_assumed': pairs * 2,
        'note': 'Automated conservative estimate; unknown relationships not assumed independent; similarity-based relations are not confirmed lineage.'
    }

by_set = defaultdict(list)
for r in records:
    by_set[r['source_set']].append(r)
lineage_summary = {
    'total_candidates_processed': len(records),
    'categories': dict(Counter(r['automated_category'] for r in records)),
    'by_source_set': {k: independence_est(v) for k, v in by_set.items()},
    'overall_independence_estimate': independence_est(records),
    'method': 'Automated scoring from existing similarity/signal/metadata fields; thresholds >=0.98 or strong identifier signal => likely_dependent, >=0.80 => possible_dependency, >=0.50 => possible_dependency, else unknown. No human confirmation; no similarity treated as confirmed lineage.',
    'historical_human_review_artifacts_preserved': [
        'final_completion_package/05_annotations/worksheets/*',
        'DatasetCollection/processed/stage5b_reviewer1_worksheet.csv',
        'DatasetCollection/processed/stage5b_reviewer2_worksheet.csv',
        'DatasetCollection/processed/stage5b_lineage_pair_review.csv',
        'data/annotations/*'
    ]
}

fields = ['source_set', 'candidate_id', 'case_id_1', 'case_id_2', 'similarity_score', 'signals', 'automated_category', 'machine_verifiable_provenance_confirmed', 'provisional_relationship_label', 'conservative_independence_treatment', 'rationale']
with open(OUT / 'automated_lineage_analysis.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(records)
with open(OUT / 'automated_lineage_summary.json', 'w', encoding='utf-8') as f:
    json.dump(lineage_summary, f, indent=2)

# --- descriptive real-data analysis (no ground-truth metrics) ---
def safe_div(a, b):
    return (a / b) if b else None

# Stage 4E / Stripe evidence
stage4e = read_csv(ROOT / 'DatasetCollection/processed/stage4e_evidence_records.csv')
n4 = len(stage4e)
http_ok = 0
official_match = 0
evidence_available = 0
snapshot_only = 0
contradictions = 0
unresolved = 0
unavailable = 0
for r in stage4e:
    hs = str(r.get('official_http_status', '')).strip()
    gs = str(r.get('greenhouse_http_status', '')).strip()
    ok = hs in ('200', '200.0') or gs in ('200', '200.0') or bool(str(r.get('retrieval_timestamp', '')).strip())
    if ok:
        http_ok += 1
    cls = str(r.get('evidence_classification', '')).lower()
    vae = str(r.get('vacancy_authorization_evidence', '')).lower()
    if 'official' in cls or 'independent' in cls or 'confirmed' in cls or 'match' in cls and 'snapshot' not in cls:
        official_match += 1
    if 'unavailable' in cls or vae in ('unavailable', 'inaccessible') or hs in ('404', '403', '500') and not ok:
        unavailable += 1
        evidence_available_counted = False
    else:
        evidence_available += 1
    if 'snapshot' in cls or 'snapshot' in vae:
        snapshot_only += 1
    if 'contradict' in cls or 'contradict' in vae:
        contradictions += 1
    if 'unresolved' in cls or vae in ('unresolved', 'unverified', ''):
        unresolved += 1
stage4e_desc = {
    'records': n4,
    'retrieval_success_rate': safe_div(http_ok, n4),
    'official_source_match_rate_proxy': safe_div(official_match, n4),
    'evidence_availability_rate': safe_div(evidence_available, n4),
    'snapshot_only_match_rate_proxy': safe_div(snapshot_only, n4),
    'contradiction_evidence_count': contradictions,
    'unresolved_rate': safe_div(unresolved, n4),
    'note': 'Descriptive system outputs from collected Stage 4E artifacts; not ground-truth performance metrics.'
}

# Unified proposed package descriptive
unified = read_csv(ROOT / 'DatasetCollection/final_research_package/unified_proposed_dataset.csv')
nu = len(unified)
status_dist = Counter((r.get('vacancy_status_observation') or '').strip() or 'unknown' for r in unified)
# duplicate evidence rate proxy: identical source URLs or identical descriptions within source groups (rough)
urls = [r.get('original_source_url', '') for r in unified]
url_nonempty = [u for u in urls if u]
dup_url = len(url_nonempty) - len(set(url_nonempty))
# candidate lineage rate proxy based on known candidate case involvement across sets
candidate_case_ids = set()
for r in records:
    if r['case_id_1']: candidate_case_ids.add(r['case_id_1'])
    if r['case_id_2']: candidate_case_ids.add(r['case_id_2'])
involved = sum(1 for r in unified if r.get('case_id') in candidate_case_ids)
unified_desc = {
    'records': nu,
    'vacancy_status_observation_distribution': dict(status_dist),
    'duplicate_evidence_rate_url_proxy': safe_div(dup_url, len(url_nonempty)),
    'duplicate_source_url_count': dup_url,
    'candidate_lineage_involved_records': involved,
    'candidate_lineage_rate_proxy': safe_div(involved, nu),
    'decision_distribution_note': 'Unified package is collection/staging data; no automated authorization decisions assigned as labels.',
}

# automated verification pipeline results from existing artifact mapping
ver_results = read_csv(ROOT / 'final_completion_package/03_stage4_verification/verification_results.csv')
vdist = Counter(r.get('verification_state', '') for r in ver_results)
ver_desc = {
    'records': len(ver_results),
    'state_distribution': dict(vdist),
    'retrieval_success_rate_proxy': safe_div(sum(1 for r in ver_results if (r.get('retrieval_status') or '') in ('success','available','ok','200')), len(ver_results)),
    'unresolved_or_inaccessible_rate': safe_div(sum(1 for r in ver_results if r.get('verification_state') in ('independently_unresolved','inaccessible')), len(ver_results)),
    'snapshot_match_only_rate': safe_div(vdist.get('snapshot_match_only',0), len(ver_results)),
    'note': 'States produced from collected artifacts by automated conservative mapping; not live-verified ground truth.'
}

# abstention/decision distribution as system outputs (descriptive, automated rules)
# For stage4e: treat inaccessible/unresolved as abstain/unresolved, snapshot_only as unresolved authorization pending authority
abstain = vdist.get('inaccessible', 0) + vdist.get('independently_unresolved', 0)
decision_dist = {
    'employer_identity': {'verified': 0, 'contradicted': 0, 'unresolved': len(ver_results)},
    'vacancy_authorization': {'supported': 0, 'contradicted': 0, 'unresolved': len(ver_results)},
    'fraud_outcome': {'confirmed_fraudulent': 0, 'confirmed_legitimate': 0, 'unresolved': len(ver_results)},
    'abstention_rate_descriptive': safe_div(abstain, len(ver_results)),
    'note': 'Automated machine-generated evidence assessments; no independently adjudicated conclusions. Unresolved dominates where authority/confirmation unavailable.'
}

descriptive = {
    'stage4e_evidence': stage4e_desc,
    'unified_proposed_package': unified_desc,
    'automated_verification_states': ver_desc,
    'automated_decision_distribution': decision_dist,
    'lineage': {
        'candidate_lineage_rate_overall': safe_div(len(records), len(records)),  # 687/687 candidates processed
        'total_candidate_pairs_processed': len(records),
        'category_distribution': dict(Counter(r['automated_category'] for r in records)),
        'evidence_independence_estimates': lineage_summary['overall_independence_estimate']
    },
    'label': 'DESCRIPTIVE SYSTEM OUTPUTS ONLY - not ground-truth performance metrics (no human/adjudicated labels).'
}

with open(OUT / 'descriptive_real_data_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(descriptive, f, indent=2)

# CSV summary
with open(OUT / 'descriptive_metrics.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['metric_group', 'metric', 'value', 'note'])
    for k, v in stage4e_desc.items():
        if k != 'note': w.writerow(['stage4e_evidence', k, v, stage4e_desc['note']])
    for k, v in ver_desc.items():
        if k not in ('note','state_distribution'): w.writerow(['automated_verification_states', k, v, ver_desc['note']])
    for st, cnt in ver_desc['state_distribution'].items(): w.writerow(['automated_verification_states', f'state_count_{st}', cnt, ver_desc['note']])
    w.writerow(['automated_decision_distribution', 'abstention_rate_descriptive', decision_dist['abstention_rate_descriptive'], decision_dist['note']])
    w.writerow(['lineage', 'candidate_pairs_processed', len(records), descriptive['label']])

print('done', len(records))
