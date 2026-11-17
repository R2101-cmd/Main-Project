import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research-data' / 'phase2_v1' / 'synthetic'
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20261114

def make_case(i, label, scenario, evidence, partition='test'):
    cid = f"SYNX-{i:04d}"
    return {
        "id": cid,
        "advertisement_id": cid,
        "vacancy_group": f"SYNX-G-{i:04d}",
        "vacancy_group_id": f"SYNX-G-{i:04d}",
        "partition": partition,
        "text": f"Synthetic extended case {cid}. Employer: Synthetic Employer X. Title: Analyst. Location: Remote. Scenario: {scenario}. Generated for automated system testing only.",
        "employer_id": "SYNX-EMP",
        "employer_name": "Synthetic Employer X",
        "job_title": "Analyst",
        "location": "Remote",
        "salary_text": "Synthetic",
        "requisition_id": cid,
        "original_source_url": f"synthetic://extended/{cid}",
        "source_type": "synthetic_scenario_extended",
        "input_type": "pasted_text",
        "observed_at": None,
        "source_published_at": None,
        "snapshot_reference": None,
        "privacy_review_status": "not_needed",
        "missing_data_notes": ["All fields are synthetic; not real vacancy data."],
        "authorization_label": label,
        "employer_identity": "synthetic_scenario_label",
        "annotation_status": "synthetic_generator_extended_v1_not_human_reviewed",
        "annotation_rationale": f"Synthetic extended scenario: {scenario}.",
        "synthetic": True,
        "synthetic_label_source": "extended_scenario_generator_v1",
        "synthetic_generation_seed": SEED,
        "evidence": evidence,
    }

def ev(case_i, j, state, retrieval, lg=None, rel='original', url_suffix='a'):
    eid = f"SYNX-EV-{case_i:04d}-{j}"
    summary = {
        'supported': 'Synthetic source supports the specific vacancy claim.',
        'contradicted': 'Synthetic source contradicts the specific vacancy claim.',
        'unverified': 'Synthetic source retrieved but does not establish authorization.',
        'unavailable': 'Synthetic source inaccessible; unavailable evidence is not fraud.',
    }[state]
    return {
        "id": eid, "evidence_id": eid, "advertisement_id": f"SYNX-{case_i:04d}", "case_id": f"SYNX-{case_i:04d}",
        "vacancy_group_id": f"SYNX-G-{case_i:04d}", "source_url": f"synthetic://extended/source/{case_i}/{j}/{url_suffix}",
        "source_type": "synthetic_extended_source", "source_relationship": rel, "lineage_group": lg,
        "lineage_review_status": "synthetic_automated_not_human_reviewed", "retrieval_status": retrieval,
        "retrieval_state": retrieval, "evidence_state": state, "evidence_status": state,
        "matched_fields": ["title", "employer"] if state == 'supported' else ([] if state != 'contradicted' else ["employer"]),
        "contradicted_fields": ["title"] if state == 'contradicted' else [],
        "summary": summary, "rationale": summary,
        "evidence_excerpt": f"Synthetic extended evidence for SYNX-{case_i:04d}.", "retrieved_at": None,
        "source_published_at": None, "snapshot_reference": None, "privacy_review_status": "not_needed"
    }

rows = []
i = 1
# source dependence / copied evidence (same lineage group repeated) - supported but dependent copies
for _ in range(6):
    rows.append(make_case(i, 'supported', 'copied/dependent sources share lineage group', [
        ev(i,1,'supported','available', f'SYNX-LG-{i}-A','original'),
        ev(i,2,'supported','available', f'SYNX-LG-{i}-A','copied','b'),
        ev(i,3,'supported','available', f'SYNX-LG-{i}-A','copied','c'),
    ]))
    i += 1
# copied evidence leading to unverified/ambiguous
for _ in range(4):
    rows.append(make_case(i, 'unresolved', 'dependent copied third-party sources remain unverified', [
        ev(i,1,'unverified','available', f'SYNX-LG-{i}-A','original'),
        ev(i,2,'unverified','available', f'SYNX-LG-{i}-A','copied','b'),
    ]))
    i += 1
# contradictory evidence
for _ in range(6):
    rows.append(make_case(i, 'contradicted', 'independent sources include contradiction', [
        ev(i,1,'supported','available', f'SYNX-LG-{i}-A','original'),
        ev(i,2,'contradicted','available', f'SYNX-LG-{i}-B','independent','b'),
    ]))
    i += 1
# unavailable sources
for _ in range(6):
    rows.append(make_case(i, 'unresolved', 'sources unavailable or inaccessible', [
        ev(i,1,'unavailable','unavailable', None,'unknown'),
        ev(i,2,'unavailable','failed', None,'unknown','b'),
    ]))
    i += 1
# unknown lineage / mixed
for _ in range(4):
    rows.append(make_case(i, 'unresolved', 'unknown lineage and mixed unverified evidence', [
        ev(i,1,'unverified','available', None,'unknown'),
        ev(i,2,'unverified','available', f'SYNX-LG-{i}-B','unknown','b'),
    ]))
    i += 1
# independent supporting sources
for _ in range(4):
    rows.append(make_case(i, 'supported', 'independent supporting sources with distinct lineage groups', [
        ev(i,1,'supported','available', f'SYNX-LG-{i}-A','original'),
        ev(i,2,'supported','available', f'SYNX-LG-{i}-B','independent','b'),
    ]))
    i += 1

path = OUT / 'synthetic_benchmark_extended_v1.jsonl'
with open(path, 'w', encoding='utf-8') as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
manifest = {
    'name': 'synthetic_benchmark_extended_v1',
    'records': len(rows),
    'seed': SEED,
    'synthetic': True,
    'human_reviewed': False,
    'labels_are_synthetic_not_ground_truth': True,
    'scenarios': {
        'copied_dependent_supported': 6,
        'copied_dependent_unresolved': 4,
        'contradictory_evidence': 6,
        'unavailable_sources': 6,
        'unknown_lineage_mixed_unresolved': 4,
        'independent_supporting': 4,
    },
    'original_benchmark_preserved': 'research-data/phase2_v1/synthetic/synthetic_benchmark_v1.jsonl'
}
with open(OUT / 'synthetic_benchmark_extended_v1.manifest.json', 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)
print(len(rows))
