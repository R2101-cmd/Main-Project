import csv
import json
import hashlib
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'final_completion_package'

def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig', errors='replace') as f:
        return list(csv.DictReader(f))

def read_json(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return json.load(f)

def read_jsonl(path):
    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fieldnames})

NOW = datetime.now(timezone.utc).isoformat()

# 02 dataset reconciliation refinement
stage4e = read_csv(ROOT/'DatasetCollection/processed/stage4e_evidence_records.csv')
table_a = read_csv(ROOT/'DatasetCollection/processed/table_A_advertisements.csv')
table_b = read_csv(ROOT/'DatasetCollection/processed/table_B_ground_truth.csv')
table_c = read_csv(ROOT/'DatasetCollection/processed/table_C_evidence_records.csv')
stripe_pkg = read_csv(ROOT/'DatasetCollection/final_research_package/stripe_cohort.csv')
unified_pkg = read_csv(ROOT/'DatasetCollection/final_research_package/unified_proposed_dataset.csv')
stage4f_pkg = read_csv(ROOT/'DatasetCollection/final_research_package/stage4f_expansion_cohort.csv')
naukri_pkg = read_csv(ROOT/'DatasetCollection/final_research_package/naukri_separate_cohort.csv')
lineage21 = read_csv(ROOT/'DatasetCollection/processed/vacancyguard_table_d_lineage_candidates.csv')
pairs207 = read_csv(ROOT/'DatasetCollection/processed/stage5b_lineage_pair_review.csv')

recon = {
    'generated_utc': NOW,
    'datasets': {
        'stripe_greenhouse_original_780': {
            'paths': ['DatasetCollection/processed/table_A_advertisements.csv','DatasetCollection/processed/table_B_ground_truth.csv','DatasetCollection/processed/table_C_evidence_records.csv','DatasetCollection/processed/stage4e_evidence_records.csv'],
            'records': {'table_a': len(table_a), 'table_b': len(table_b), 'table_c_snapshot': len(table_c), 'stage4e_evidence': len(stage4e)},
            'unique_case_ids': {'table_a': len({r['case_id'] for r in table_a}), 'stage4e': len({r['case_id'] for r in stage4e})},
            'employer_count': len({r.get('employer_id') for r in table_a if r.get('employer_id')}),
            'source_family': 'Stripe/Greenhouse snapshot-derived cohort',
            'label_status': 'No adjudicated human ground truth in Tables B/5B; Table B and reviewer worksheets remain unresolved/unsubmitted.',
            'evidence_status': 'Stage 4E collected evidence records exist; 744 independent_official_confirmation, 19 fresh_same_system_retrieval, 16 unresolved, 1 unavailable by evidence_state field (provenance classes, not human authorization labels).',
            'limitations': ['Single employer/source-family concentration', 'Snapshot match != independently verified authorization', 'No frozen human benchmark']
        },
        'stage4f_expansion_2200': {
            'paths': ['DatasetCollection/processed/stage4f_expansion_records.csv','DatasetCollection/final_research_package/stage4f_expansion_cohort.csv'],
            'records': len(stage4f_pkg),
            'unique_case_ids': len({r['case_id'] for r in stage4f_pkg}),
            'employer_count': len({r.get('employer_id') for r in stage4f_pkg if r.get('employer_id')}),
            'source_families': dict(Counter(r.get('source_family_id','') for r in stage4f_pkg)),
            'label_status': 'Collection dataset only; no human adjudication, no authorization/fraud ground truth.',
            'limitations': ['Greenhouse/Lever-heavy', 'No third-party/Workday/SmartRecruiters/Ashby collected in this package summary', 'Collection interrupted/finalized from checkpoint per logs']
        },
        'proposed_unified_2980': {
            'paths': ['DatasetCollection/final_research_package/unified_proposed_dataset.csv'],
            'records': len(unified_pkg),
            'unique_case_ids': len({r['case_id'] for r in unified_pkg}),
            'employer_count': len({r.get('employer_id') for r in unified_pkg if r.get('employer_id')}),
            'cohorts': dict(Counter(r.get('cohort_id','') for r in unified_pkg)),
            'selection_decision': 'PROPOSED_NOT_PRIMARY_BENCHMARK: structurally packaged and useful as a collection/staging dataset, but not eligible as a verified evaluation benchmark because adjudicated human labels, confirmed lineage, and balanced source diversity are incomplete.',
            'must_not_replace_automatically': True
        },
        'naukri_separate_198': {
            'paths': ['DatasetCollection/final_research_package/naukri_separate_cohort.csv'],
            'records': len(naukri_pkg),
            'unique_case_ids': len({r['case_id'] for r in naukri_pkg}),
            'employer_count': len({r.get('employer_id') for r in naukri_pkg if r.get('employer_id')}),
            'selection_decision': 'SEPARATE_COHORT_ONLY: provenance/structure differ; do not merge with main dataset until comparability, labeling, and lineage rules are established.',
            'overlap_with_unified_case_ids': len({r['case_id'] for r in naukri_pkg} & {r['case_id'] for r in unified_pkg})
        },
        'phase2_v1_research_data': {
            'paths': ['research-data/phase2_v1/advertisements_v1.jsonl','research-data/phase2_v1/evidence_v1.jsonl','research-data/phase2_v1/independent_annotations_v1.jsonl','research-data/phase2_v1/lineage_reviews_v1.jsonl','research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl'],
            'core_label_files_empty': True,
            'synthetic_records': len(read_jsonl(ROOT/'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl')),
            'selection_decision': 'Synthetic benchmark valid for controlled implementation checks only; not real-world ground truth.'
        },
        'provisional_annotations': {
            'paths': ['data/annotations/pilot.jsonl','data/annotations/job_ad_authorization_evaluation.jsonl','data/annotations/job_ad_independent_review_v1.jsonl'],
            'pilot_records': len(read_jsonl(ROOT/'data/annotations/pilot.jsonl')),
            'evaluation_records': len(read_jsonl(ROOT/'data/annotations/job_ad_authorization_evaluation.jsonl')),
            'independent_review_v1_records': len(read_jsonl(ROOT/'data/annotations/job_ad_independent_review_v1.jsonl')),
            'selection_decision': 'PROVISIONAL/SINGLE-REVIEWER: usable for exploratory analysis only, not for defensible hypothesis proof.'
        }
    },
    'overlaps': {
        'stripe_pkg_case_ids': len({r['case_id'] for r in stripe_pkg}),
        'table_a_case_ids': len({r['case_id'] for r in table_a}),
        'table_a_vs_stripe_pkg_case_id_overlap': len({r['case_id'] for r in table_a} & {r['case_id'] for r in stripe_pkg}),
        'table_a_vs_unified_case_id_overlap': len({r['case_id'] for r in table_a} & {r['case_id'] for r in unified_pkg}),
        'expansion_vs_unified_case_id_overlap': len({r['case_id'] for r in stage4f_pkg} & {r['case_id'] for r in unified_pkg}),
        'stripe_vs_expansion_case_id_overlap': len({r['case_id'] for r in stripe_pkg} & {r['case_id'] for r in stage4f_pkg}),
        'naukri_vs_main_case_id_overlap': len({r['case_id'] for r in naukri_pkg} & {r['case_id'] for r in unified_pkg}),
    },
    'primary_dataset_decision': {
        'selected_for_verified_evaluation': 'NONE (blocked: no adjudicated multi-reviewer human ground truth / confirmed lineage benchmark)',
        'selected_for_collection_staging_reference': 'DatasetCollection/final_research_package/unified_proposed_dataset.csv (proposed, versioned, structurally validated; not approved replacement)',
        'selected_for_existing_snapshot_cohort_analysis': 'DatasetCollection/processed table_A/B/C + stage4e_evidence_records.csv (780 Stripe/Greenhouse, provenance/snapshot evidence only)',
        'selected_for_controlled_implementation_validation': 'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl'
    }
}
write_json(PKG/'02_dataset/dataset_reconciliation.json', recon)
with open(PKG/'02_dataset/dataset_reconciliation.md','w',encoding='utf-8',newline='\n') as f:
    f.write('# Dataset reconciliation\n\n')
    f.write(f"Generated: {NOW}\n\n")
    f.write('## Decision\n')
    f.write('- **Verified evaluation benchmark:** none available (human adjudication/confirmed lineage incomplete).\n')
    f.write('- **Primary collection/staging reference:** proposed unified 2,980-record package (`final_research_package/unified_proposed_dataset.csv`) — structurally valid, not approved as verified benchmark or automatic replacement.\n')
    f.write('- **Snapshot/provenance cohort:** 780 Stripe/Greenhouse processed tables and Stage 4E evidence.\n')
    f.write('- **Controlled implementation checks:** synthetic benchmark v1 (60 records).\n')
    f.write('- **Kept separate:** Naukri 198-record cohort.\n\n')
    f.write('## Overlaps\n\n```json\n'+json.dumps(recon['overlaps'],indent=2)+'\n```\n\n')
    f.write('## Key findings\n')
    f.write('- Table A (processed 780) and stripe package use different `case_id` namespaces (0 overlap by ID) but represent the same Stripe/Greenhouse cohort context; do not merge without explicit mapping.\n')
    f.write('- Expansion package equals processed stage4f expansion by IDs (2200/2200) and is fully contained in unified proposed package.\n')
    f.write('- Naukri has no case-ID overlap with unified main package and must remain separate.\n')
    f.write('- No dataset may be treated as adjudicated ground truth today; reviewer worksheets/pair decisions remain unsubmitted.\n')

# 03 Stage 4 independent verification from existing evidence artifacts
# Use stage4e evidence as best available retrieval/provenance records for 780 cohort.
ver_rows = []
for r in stage4e:
    ev_state = (r.get('evidence_state') or '').strip()
    retr = (r.get('retrieval_status') or '').strip()
    stype = (r.get('source_type') or '').strip()
    # Conservative mapping: collected evidence != human-verified authorization
    if retr in ('success', 'available', 'ok', '200') or ev_state in ('independent_official_confirmation','fresh_same_system_retrieval'):
        vstate = 'snapshot_match_only'
        if ev_state == 'independent_official_confirmation':
            note = 'Retrieved/confirmed from official or ATS listing in collected evidence; treated as snapshot/retrieval-supported record pending independent human adjudication and employer-authority confirmation.'
        elif ev_state == 'fresh_same_system_retrieval':
            note = 'Fresh same-system retrieval observed; not independent from source system lineage.'
        else:
            note = 'Retrieval succeeded; authorization remains pending adjudication.'
    elif retr in ('failed','error') or ev_state == 'unavailable':
        vstate = 'inaccessible'
        note = 'Source retrieval unavailable/failed in collected evidence; not a contradiction.'
    else:
        vstate = 'independently_unresolved'
        note = 'Evidence collected but insufficient for independent authorization determination.'
    ver_rows.append({
        'case_id': r.get('case_id',''),
        'employer_id': r.get('employer_id',''),
        'employer_name': r.get('employer_name',''),
        'advertised_url': r.get('advertised_url',''),
        'checked_source_url': r.get('evidence_url','') or r.get('source_url',''),
        'source_type': stype,
        'retrieval_timestamp': r.get('evidence_observation_date','') or r.get('retrieved_at','') or '',
        'retrieval_status': retr,
        'collected_evidence_state': ev_state,
        'verification_state': vstate,
        'verification_basis': note,
        'requires_human_adjudication': 'yes',
        'live_network_recheck_performed': 'no (derived from existing collected artifacts on 2026-11-14)'
    })
vfields = ['case_id','employer_id','employer_name','advertised_url','checked_source_url','source_type','retrieval_timestamp','retrieval_status','collected_evidence_state','verification_state','verification_basis','requires_human_adjudication','live_network_recheck_performed']
write_csv(PKG/'03_stage4_verification/verification_results.csv', ver_rows, vfields)
vcounts = Counter(r['verification_state'] for r in ver_rows)
vsummary = {
    'generated_utc': NOW,
    'method': 'artifact-based verification classification from DatasetCollection/processed/stage4e_evidence_records.csv; no new live network retrieval executed in this run.',
    'total_records': len(ver_rows),
    'states': dict(vcounts),
    'successful_retrievals_by_record': sum(1 for r in ver_rows if r['retrieval_status'] in ('success','available','ok','200') or r['collected_evidence_state'] in ('independent_official_confirmation','fresh_same_system_retrieval')),
    'independently_supported_human_adjudicated': 0,
    'independently_contradicted_human_adjudicated': 0,
    'limitation': 'Snapshot/retrieval evidence does not equal independently verified employer authorization. Human adjudication and authority/lineage confirmation are required.'
}
write_json(PKG/'03_stage4_verification/verification_summary.json', vsummary)
write_json(PKG/'03_stage4_verification/verification_manifest.json', {
    'generated_utc': NOW, 'source': 'DatasetCollection/processed/stage4e_evidence_records.csv', 'source_sha256': sha256(ROOT/'DatasetCollection/processed/stage4e_evidence_records.csv'),
    'records': len(ver_rows), 'live_http_performed': False, 'priority_processing': 'all available collected Stripe/stage4e records classified; live recheck pending for unresolved/inaccessible and for authority confirmation'
})
failures = [r for r in ver_rows if r['verification_state'] in ('inaccessible','independently_unresolved')]
write_csv(PKG/'03_stage4_verification/verification_failures.csv', failures, vfields)
with open(PKG/'03_stage4_verification/verification_methodology.md','w',encoding='utf-8',newline='\n') as f:
    f.write('# Stage 4 independent official-source verification (artifact-based execution)\n\n')
    f.write(f'Generated: {NOW}\n\n')
    f.write('## What was executed\n')
    f.write('- Audited existing Stage 4E evidence records (780 Stripe/Greenhouse cohort) and produced per-case verification classifications without modifying original artifacts.\n')
    f.write('- Preserved distinction between retrieved/snapshot evidence and human-adjudicated independent authorization.\n')
    f.write('- No CAPTCHA/auth bypass, no private/local targets, no unsafe crawling; **no new live network retrieval** was performed in this run.\n\n')
    f.write('## State mapping (conservative)\n')
    f.write('- `snapshot_match_only`: collected retrieval/same-system evidence exists (including official-confirmation/fresh-same-system classes) but employer-vacancy authorization is not human-adjudicated as independently verified.\n')
    f.write('- `inaccessible`: retrieval failed/unavailable in collected evidence.\n')
    f.write('- `independently_unresolved`: insufficient collected evidence for determination.\n')
    f.write('- `independently_supported` / `independently_contradicted`: reserved for future human-adjudicated outcomes with authority-confirmed evidence (0 in this artifact-based pass).\n\n')
    f.write('## Coverage and blocker\n')
    f.write(f'- Classified records: {len(ver_rows)} / 780 collected stage4e records.\n')
    f.write('- Live independent re-verification of public official sources remains required for higher-assurance claims; prioritize cases in `verification_failures.csv` and any human-review queue.\n')

# 04 lineage outputs
cand_rows = []
for r in lineage21:
    cand_rows.append({
        **r,
        'candidate_type': 'naukri/processed_21_existing',
        'confirmed_relationship': '',
        'human_confirmation_required': 'yes',
        'confirmation_status': 'pending_review'
    })
# include stage4f candidates if present
s4f_path = ROOT/'DatasetCollection/processed/stage4f_lineage_candidates.csv'
if s4f_path.exists():
    for r in read_csv(s4f_path):
        cand_rows.append({**r, 'candidate_type': 'stage4f_candidate', 'confirmed_relationship': '', 'human_confirmation_required': 'yes', 'confirmation_status': 'pending_review'})
# pair review queue
pair_rows = []
for r in pairs207:
    pair_rows.append({**r})
# relationships: none confirmed
rel_rows = []
lin_summary = {
    'generated_utc': NOW,
    'existing_21_candidates_preserved': len(lineage21),
    'stage4f_candidates_preserved': len(read_csv(s4f_path)) if s4f_path.exists() else 0,
    'stripe_pair_review_candidates': len(pairs207),
    'confirmed_relationships': 0,
    'rejected_relationships': 0,
    'unknown_pending_relationships': len(cand_rows) + len(pair_rows),
    'independent_source_families_confirmed': 0,
    'note': 'No candidate treated as confirmed; all require human review. Text/similarity/URL signals are candidate evidence only.'
}
all_cand_fields = sorted({k for r in cand_rows for k in r.keys()}) if cand_rows else []
write_csv(PKG/'04_stage5_lineage/lineage_candidates.csv', cand_rows, all_cand_fields)
rel_fields = ['relationship_id','left_case_id','right_case_id','relationship_type','evidence_basis','reviewer','review_status','rationale']
write_csv(PKG/'04_stage5_lineage/lineage_relationships.csv', rel_rows, rel_fields)
pair_fields = list(pairs207[0].keys()) if pairs207 else []
write_csv(PKG/'04_stage5_lineage/lineage_review_queue.csv', pair_rows, pair_fields)
write_json(PKG/'04_stage5_lineage/lineage_summary.json', lin_summary)
write_json(PKG/'04_stage5_lineage/lineage_validation_report.json', {'generated_utc': NOW, 'checks': {'candidates_preserved': True, 'no_auto_confirmation': True, 'unknown_preserved': True}, 'issues': ['Human confirmation missing for all candidate/pair relationships']})
with open(PKG/'04_stage5_lineage/lineage_methodology.md','w',encoding='utf-8',newline='\n') as f:
    f.write('# Stage 5 lineage methodology (execution update)\n\n')
    f.write('- Preserved 21 existing lineage candidates and stage4f/stripe pair review candidates as unconfirmed.\n')
    f.write('- No relationship promoted to confirmed/copied/independent without human review.\n')
    f.write('- Independence handling rule: count distinct confirmed source families only; unknown lineage must not be assumed independent and must not be collapsed into one original without evidence.\n')
    f.write('- Candidate signals may include URL normalization, duplicate URLs, text/title/description similarity, employer/job ID/date/source metadata comparisons; similarity alone is insufficient.\n')

print('ok')
