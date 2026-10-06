"""A8 catalogue bounds and preservation checks. No PCB or pinmap writes."""
from pathlib import Path
from decimal import Decimal as D
import datetime, hashlib, json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
if (HERE/'delivery_manifest.json').exists():
    raise SystemExit('A8 already published. Use a new revision for changes.')
sources=json.loads((HERE/'retrievals.json').read_text())
for row in sources:
    if row['status']=='PASS':
        assert sha(HERE/'sources'/row['file'])==row['sha256']
for name in ['JST_PH_20261003.pdf','JST_SH_20261003.pdf','GAM-050_retrieved.pdf','Alpha_2841_7.html']:
    assert next(r for r in sources if r['file']==name)['status']=='PASS',name
assert sha(HERE/'sources/GAM-050_retrieved.pdf')==sha(HERE/'sources/JST_GAM-050_received.pdf')
assert sha(HERE/'sources/JST_SH_20261003.pdf')==sha(ROOT/'hardware/v1_2/head_harness_evidence_20261003/sources/JST_SH.pdf')

manifests=[
 'hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json',
 'hardware/v1_2/head_harness_evidence_20261003/delivery_manifest.json',
 'hardware/v1_2/reviews/J10_C3_visual_20261003/delivery_manifest.json',
]
preserve=[]
for rel in manifests:
    data=json.loads((ROOT/rel).read_text())
    entries=data.get('files',data)
    errors=[name for name,digest in entries.items() if not (ROOT/name).exists() or sha(ROOT/name)!=digest]
    preserve.append(dict(manifest=rel,manifest_sha256=sha(ROOT/rel),checked=len(entries),changed=errors,status='FAIL'if errors else'PASS'))
assert all(r['status']=='PASS'for r in preserve),preserve
dump(HERE/'preservation_check.json',preserve)

lo=(D('.024')-D('.002'))*D('25.4')
hi=(D('.024')+D('.002'))*D('25.4')
bend=hi*D(10)
contacts=[dict(mpn='SPH-004T-P0.5S',awg=[32,28],od_mm=[.5,.9],source='sources/JST_PH_20261003.pdf p2'),
          dict(mpn='SSH-003T-P0.2-H',awg=[32,28],od_mm=[.4,.8],source='sources/JST_SH_20261003.pdf p1-p2')]
screens=[]
for c in contacts:
    ok=c['awg'][1]<=30<=c['awg'][0] and D(str(c['od_mm'][0]))<=lo and hi<=D(str(c['od_mm'][1]))
    screens.append(dict(contact=c['mpn'],status='PASS'if ok else'FAIL',scope='Catalogue AWG and entire insulation OD interval only; not crimp qualification'))
assert all(r['status']=='PASS'for r in screens)

record=dict(revision='HEAD-HARNESS-A8',date='2026-10-03',source_retrievals=sources,
 fabrication_status='BLOCKED',physical_status='NOT_TESTED',decision=dict(method='SUPPLIER_MADE_TO_DRAWING',source='sources/DECISION_received.md',requires_make_or_buy_question=False,supplier_contact_authorized=False),
 precrimp_reference=dict(mpn='ASSHSSH28K152',drawing='GAM-050',revision=3,revision_date='2018-07-02',source='sources/JST_GAM-050_received.pdf',
  lead_count=1,end_contacts=['SSH-003T-P0.2-H','SSH-003T-P0.2-H'],compatible_4way_housings=['SHR-04V-S','SHR-04V-S-B'],
  wire_description='UL1571 / 28AWG / BLACK - BCD; revision 2 names Hitachi',inside_length_mm=152.4,inside_length_tolerance_mm=5,overall_reference_mm=160.2,overall_reference_tolerance_mm=5,
  drawing_current_rating_A=1,drawing_voltage_rating_V=50,actual_wire_od_mm=None,actual_wire_od_tolerance_mm=None,raw_wire_ordering_mpn=None,dynamic_bend_life=None,
  assembled_h06=False,installed_length_approved=False,procurement_released=False),
 h06_no_splice_study=dict(status='BLOCKED',scope='Candidate wire-terminal combination only; no formal substitution',board_socket_change=False,
  body_housing='PHR-4',head_housing_candidate='SHR-04V-S',contacts=contacts,common_od_mm=[.5,.8],
  wire_reference=dict(manufacturer='Alpha Wire',base_mpn='2841/7',orderable_suffix=None,procurement_status='BLOCKED',source='sources/Alpha_2841_7.html',
   awg=30,stranding='7/38 AWG',insulation='PTFE',nominal_od_in=.024,od_tolerance_in=.002,od_mm=[float(lo),float(hi)],
   catalogue_bend_rule='10 x cable diameter; no continuous-motion claim',computed_bend_reference_mm=float(bend),dynamic_bend_radius_mm=None,bend_cycles=None,crimp_height_mm=None,crimp_width_mm=None,pull_test_limit_N=None,
   price_CNY=None,domestic_stock_confirmed=False),
  screens=screens,cam_actual_manufacturer_mpn=None,cam_actual_mating_view=None,overall_route_length_mm=None,length_datums=None,bundle_od_mm=None,
  old_A2_wire_record_replaced=False),
 pinmap=dict(path='hardware/v1_2/head_harness_evidence_20261003/head_interface_pinmap_revA.csv',sha256=sha(ROOT/'hardware/v1_2/head_harness_evidence_20261003/head_interface_pinmap_revA.csv'),mapping_preserved='motion J5 -> CAM J11: 1->1,2->2,3->3,4->4; pin3 only local level reference',no_new_pinmap=True),
 inspection=dict(viewed=['sources/JST_GAM-050_received.png','sources/JST_PH_20261003_PDFKit_2.png'],reused_A7_SH_visual_review=True,pcb_edited=False),
 unresolved=['GAM-050 exact wire OD/tolerance and raw wire SKU','actual CAM J11 manufacturer/MPN and physical pin1 view','supplier crimp process and acceptance limits','fixed/dynamic route geometry and actual lengths','continuous-flex life','procurement cost/availability'],
 provenance_boundary='JST original drawing on distributor mirror; catalogue evidence is not measured physical fit. No fabrication or supplier contact authorized.')
dump(HERE/'evidence.json',record)

handoff=ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A8_shortlead.json'
assert not handoff.exists(),'Refuse to overwrite published handoff'
dump(handoff,dict(revision='A8',date='2026-10-03',supersedes=None,scope='Addendum to A7; PCB/candidate selection unchanged',evidence=str((HERE/'evidence.json').relative_to(ROOT)),evidence_sha256=sha(HERE/'evidence.json'),report=str((HERE/'README.md').relative_to(ROOT)),report_sha256=sha(HERE/'README.md'),
 production_status='BLOCKED',make_route='Supplier-made confirmed',cam_actual_connector='BLOCKED',new_pcb=False,formal_pinmap_unchanged=True,
 geometry_candidate=dict(wire_reference='Alpha 2841/7, not procurement released',wire_od_max_mm=float(hi),single_wire_catalogue_bend_reference_mm=float(bend),dynamic_bend_radius_mm=None,bundle_od_mm=None,route_length_mm=None),
 mechanical_action='Independent candidate screening only; no replacement of main geometry or successful two-loop claims; supplier lengths need full paths and terminal views',
 note='ASSHSSH28K152 is a one-wire SH/SH double-end standard lead, not a PH/SH four-way harness. Its actual wire OD remains unknown.',preservation_checks=preserve))
entries={str(p.relative_to(ROOT)):sha(p) for p in HERE.rglob('*')if p.is_file()and p.name!='delivery_manifest.json'}
entries[str(handoff.relative_to(ROOT))]=sha(handoff)
dump(HERE/'delivery_manifest.json',dict(status='PASS',scope='File integrity only',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=entries))
print(json.dumps(dict(preservation=preserve,files=len(entries),wire_od_mm=[float(lo),float(hi)],bend_reference_mm=float(bend),handoff=str(handoff)),ensure_ascii=False,indent=2))
