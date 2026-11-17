import csv, json, hashlib
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STAGE4E = ROOT / 'DatasetCollection' / 'processed' / 'stage4e_evidence_records.csv'
BEFORE = ROOT / 'final_completion_package' / '03_stage4_verification' / 'verification_summary.json'
NOW = datetime.now(timezone.utc).isoformat()

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def norm_match(v):
    v = (v or '').strip().lower()
    if v in ('exact', 'match', 'matched', 'true', 'yes', '1', 'exact_match', 'full_match'): return 'match'
    if v in ('partial', 'similar', 'fuzzy', 'partial_match'): return 'partial'
    if v in ('mismatch', 'conflict', 'different', 'false', 'no', '0', 'no_match'): return 'mismatch'
    if v in ('', 'na', 'n/a', 'none', 'null', 'unknown', 'not_available', 'not_comparable'): return 'unknown'
    return v

rows = []
with open(STAGE4E, newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        rows.append(r)

field_rows = []
auth_rows = []
state_rows = []
for r in rows:
    cid = r.get('case_id','')
    fields = {
        'employer_identity': norm_match(r.get('match_employer')),
        'job_title': norm_match(r.get('match_title')),
        'location': norm_match(r.get('match_location')),
        'job_description': norm_match(r.get('match_description')),
        'job_id': norm_match(r.get('match_job_identifier')),
        'application_url': 'unknown',
        'posting_date': 'unknown',
        'recruiter_contact': 'unknown',
    }
    # source authority/provenance from available fields
    src_ind = (r.get('source_independence') or '').lower()
    evid_cls = (r.get('evidence_classification') or '').lower()
    match_state = (r.get('source_record_match_state') or '').lower()
    retr_ind = (r.get('retrieval_independence') or '').lower()
    err = (r.get('retrieval_error') or '').strip()
    http_off = (r.get('official_http_status') or '').strip()
    http_gh = (r.get('greenhouse_http_status') or '').strip()
    inaccessible = bool(err) or (http_off and not http_off.startswith('2') and http_gh and not http_gh.startswith('2'))
    snapshot_context = ('snapshot' in match_state) or ('snapshot' in retr_ind) or ('frozen_snapshot' in retr_ind)
    authoritative_hint = ('employer' in src_ind) or ('official' in src_ind) or ('greenhouse' in src_ind) or ('api' in src_ind)
    contradiction = any(v == 'mismatch' for v in fields.values()) or ('contradict' in evid_cls)
    comparable = any(v in ('match','partial','mismatch') for v in fields.values())
    strong_match = fields['job_id']=='match' or (fields['job_title']=='match' and (fields['employer_identity']=='match' or fields['location']=='match' or fields['job_description'] in ('match','partial')))

    if inaccessible:
        vstatus = 'inaccessible'
    elif not comparable:
        vstatus = 'not_comparable'
    elif contradiction and authoritative_hint and not snapshot_context:
        vstatus = 'independently_contradicted'
    elif strong_match and authoritative_hint and not snapshot_context:
        vstatus = 'independently_supported'
    elif strong_match and snapshot_context:
        vstatus = 'snapshot_match_only'
    elif contradiction and snapshot_context:
        vstatus = 'snapshot_match_only'
    else:
        vstatus = 'independently_unresolved'

    for fname, fval in fields.items():
        field_rows.append({
            'case_id': cid,
            'evidence_id': r.get('evidence_id',''),
            'field': fname,
            'match_status': fval,
            'advertised_value': r.get('advertised_job_title','') if fname=='job_title' else (r.get('advertised_location','') if fname=='location' else ''),
            'observed_value': r.get('retrieved_job_title','') if fname=='job_title' else (r.get('retrieved_location','') if fname=='location' else (r.get('retrieved_description','')[:120] if fname=='job_description' else '')),
            'comparison_note': 'derived from stage4e collected artifact fields (automated reclassification, not ground truth)'
        })

    auth_rows.append({
        'case_id': cid,
        'evidence_id': r.get('evidence_id',''),
        'official_employer_url': r.get('official_employer_url',''),
        'greenhouse_api_url': r.get('greenhouse_api_url',''),
        'official_http_status': http_off,
        'greenhouse_http_status': http_gh,
        'source_independence': r.get('source_independence',''),
        'retrieval_independence': r.get('retrieval_independence',''),
        'source_record_match_state': r.get('source_record_match_state',''),
        'evidence_classification_original': r.get('evidence_classification',''),
        'authority_assessment_note': 'employer/official ATS hints present in artifact; employer-ATS relationship not independently adjudicated',
        'employer_relationship_assessed': 'verified_employer_associated_ats_or_official_hint' if authoritative_hint else 'unknown',
        'snapshot_context': snapshot_context,
        'verification_status_phase2': vstatus
    })

    state_rows.append({'case_id': cid, 'evidence_id': r.get('evidence_id',''), 'verification_status': vstatus, 'retrieval_error': err})

counts = Counter(r['verification_status'] for r in state_rows)
before = json.load(open(BEFORE, encoding='utf-8')) if BEFORE.exists() else {}

# write outputs
field_fields = ['case_id','evidence_id','field','match_status','advertised_value','observed_value','comparison_note']
with open(OUT/'field_matching_results.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=field_fields); w.writeheader(); w.writerows(field_rows)
auth_fields = ['case_id','evidence_id','official_employer_url','greenhouse_api_url','official_http_status','greenhouse_http_status','source_independence','retrieval_independence','source_record_match_state','evidence_classification_original','authority_assessment_note','employer_relationship_assessed','snapshot_context','verification_status_phase2']
with open(OUT/'source_authority_analysis.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=auth_fields); w.writeheader(); w.writerows(auth_rows)

summary = {
    'generated_utc': NOW,
    'phase': 'Phase 2 - Official-Source Verification Improvement',
    'input_artifact': str(STAGE4E.relative_to(ROOT)),
    'input_sha256': sha256(STAGE4E),
    'total_records': len(state_rows),
    'verification_status_counts': dict(counts),
    'required_counts': {
        'independently_supported': counts.get('independently_supported',0),
        'independently_contradicted': counts.get('independently_contradicted',0),
        'independently_unresolved': counts.get('independently_unresolved',0),
        'inaccessible': counts.get('inaccessible',0),
        'not_comparable': counts.get('not_comparable',0),
        'snapshot_match_only': counts.get('snapshot_match_only',0),
    },
    'before_after_comparison': {
        'before_source': str(BEFORE.relative_to(ROOT)),
        'before_states': before.get('states', {}),
        'after_states': dict(counts),
        'note': 'Before was prior conservative artifact mapping (all unresolved in saved summary). After applies Phase 2 conservative reclassification using field-match, authority hints, and snapshot-context distinctions from collected Stage 4E artifacts. Not a ground-truth accuracy claim.'
    },
    'methodology': 'Automated, conservative reclassification of existing Stage 4E collected records without live network retrieval, without fabricated evidence, and without human ground-truth labels. Snapshot/frozen-snapshot context kept distinct from independent authorization. Missing/inaccessible evidence not treated as fraud.',
    'limitations': 'No adjudicated ground truth; authority/employer-ATS relationships not independently verified; counts are descriptive reclassifications, not validated accuracy.'
}
with open(OUT/'verification_summary.json','w',encoding='utf-8') as f:
    json.dump(summary,f,indent=2)

print(json.dumps(summary['required_counts'], indent=2))
