"""Receive hardware A8 without changing any electrical or main model files."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def source(p,expected=None):
    p=ROOT/p
    digest=sha(p)
    if expected is not None:assert digest==expected,(str(p),digest,expected)
    sources[str(p.relative_to(ROOT))]=digest
    return json.loads(p.read_text()) if p.suffix=='.json' else p

h=source('hardware/v1_2/handoff/mechanical_P5R7_prearrival_A8_shortlead.json')
e=source(h['evidence'],h['evidence_sha256'])
source(h['report'],h['report_sha256'])
source('mechanical/mori_v1_2.blend','bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f')
source('config/geometry.json')
source('contracts/mechanical_interfaces.json')
source(e['pinmap']['path'],e['pinmap']['sha256'])
review_dir=Path(h['report']).parent
for row in e['source_retrievals']:
    if row['status']=='PASS':source(str(review_dir/'sources'/row['file']),row['sha256'])
manifests=[]
for row in h['preservation_checks']:
    m=source(row['manifest'],row['manifest_sha256'])
    files=m.get('files',m)
    for path,digest in files.items():assert sha(ROOT/path)==digest,path
    manifests.append(dict(path=row['manifest'],file_count=len(files),status='PASS'))
candidate=e['h06_no_splice_study'];wire=candidate['wire_reference']
for contact in candidate['contacts']:
    assert min(contact['awg']) <= wire['awg'] <= max(contact['awg'])
    assert contact['od_mm'][0]<=wire['od_mm'][0]<=wire['od_mm'][1]<=contact['od_mm'][1]
assert abs((.024+.002)*25.4-wire['od_mm'][1])<1e-9
assert abs(wire['od_mm'][1]*10-wire['computed_bend_reference_mm'])<1e-9
assert e['decision']['requires_make_or_buy_question'] is False
assert not candidate['old_A2_wire_record_replaced']
assert h['new_pcb'] is False and h['formal_pinmap_unchanged'] is True
assert h['geometry_candidate']['bundle_od_mm'] is None
assert h['geometry_candidate']['dynamic_bend_radius_mm'] is None
out=dict(status='PASS',scope='A8 evidence receipt and independent catalogue-range calculation only',
    received_utc=datetime.now(timezone.utc).isoformat(),sources=sources,
    preservation_checks=manifests,main_revision='V1.2-M1.47',main_geometry_changed=False,
    actual_cam_mating='BLOCKED',actual_crimp='NOT_TESTED',dynamic_life='NOT_TESTED',
    manufacturing_drawing='BLOCKED',procurement_released=False,
    manufacture_method='USER_CONFIRMED_SUPPLIER_MADE_TO_DRAWING',
    candidate=dict(housings=['PHR-4','SHR-04V-S candidate'],
        contacts=[x['mpn'] for x in candidate['contacts']],wire_reference='Alpha 2841/7',
        od_interval_mm=wire['od_mm'],catalogue_bend_reference_mm=wire['computed_bend_reference_mm'],
        not_final_ordering_mpn=True,wire_count=4,pinmap_preserved=True))
(HERE/'receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','source_count':len(sources),'protected_files_checked':sum(m['file_count'] for m in manifests),'main_unchanged':True}))
