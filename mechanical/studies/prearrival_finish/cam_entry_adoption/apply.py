"""Adopt only the two photo-established CAM entry corrections after backup."""
from pathlib import Path
import hashlib,json

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prep=json.loads((OUT/'preparation.json').read_text())
base=json.loads((OUT/'baseline.json').read_text())
assert prep['status']==base['status']=='PASS'
assert sha(ROOT/'mechanical/mori_v1_2.blend')==prep['source_blend_sha256']
path=ROOT/'config/geometry.json';p=json.loads(path.read_text())
assert p['revision']=='V1.2-M1.49'
study=ROOT/'mechanical/studies/prearrival_finish/head_harness_M1_49'
receipt=study/'remaining_routes/static_flex/connector_faces/direction_receipt.json'
candidate=study/'cam_fpc_entry_geometry.py'
assert sha(receipt)=='7de15259fd5da95fee4eb49233b401c20d3af4767c7bec7a53537deb0233357f'
assert sha(candidate)=='ca56434935b916240b8fbd4e25f7dd71a31c8b7e7d08c69ad09b1f6497546ab4'
entry=dict(enabled=True,revision='CAM-FPC-EXIT-R1',
    direction_receipt=str(receipt.relative_to(ROOT)),direction_receipt_sha256=sha(receipt),
    baseline_revision='V1.2-M1.49',baseline_snapshot=prep['snapshot_root'],
    candidate_helper=str(candidate.relative_to(ROOT)),candidate_helper_sha256=sha(candidate),
    references=['CAMERA_FPC_24','DISPLAY_FPC_18'],
    outward_direction_uvw={'CAMERA_FPC_24':[0,1,0],'DISPLAY_FPC_18':[-1,0,0]},
    display_visual_mouth=dict(width_reduction_mm=1.2,height_mm=.45,height_from_board_face_mm=.95),
    evidence='ASSUMED photo reconstruction; official inserted-product photographs establish outlet direction only',
    authorization='M1.33 official dimensions plus official photographs; preserve board, hardware and printed datums',
    limitations=['Connector slot, contact plane, pin 1, insertion depth, latch and supply revision remain unknown.',
        'Illustrative mouth dimensions may not define harness mating datums.',
        'No printed or electrical change; structural and wire-restraint candidates remain unadopted.'],
    exact_mating='BLOCKED',manufacturing_release=False)
p['revision']='V1.2-M1.50';p['waveshare_detail']['entry_correction']=entry
path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')

# Keep the old component() implementation available for reproducible historical
# comparisons; only the active reconstruction dispatches the two corrected refs.
helper=candidate.read_text().replace('def corrected_component(row, board_thickness=1.6):',
    'def corrected_component(row, options, board_thickness=1.6):')
helper=helper.replace('slot_width=w-1.2; slot_height=.45; slot_center_height=.95',
    "mouth=options['display_visual_mouth']\n    slot_width=w-mouth['width_reduction_mm']; slot_height=mouth['height_mm']; slot_center_height=mouth['height_from_board_face_mm']")
(ROOT/'mechanical/scripts/cam_fpc_entries.py').write_text(helper)

path=ROOT/'mechanical/scripts/waveshare_detail.py';s=path.read_text()
old="    comps += [component(row) for row in c['parts']]"
new="""    entry=W.get('entry_correction',{}); entries=[]
    if entry.get('enabled'):
        from cam_fpc_entries import corrected_component
        receipt_path=PROJECT/entry['direction_receipt']
        assert hashlib.sha256(receipt_path.read_bytes()).hexdigest()==entry['direction_receipt_sha256']
        receipt=json.loads(receipt_path.read_text())
        assert receipt['status']=='PASS' and receipt['revision']==entry['revision']
        for name,expected in receipt['files'].items():
            assert hashlib.sha256((PROJECT/name).read_bytes()).hexdigest()==expected,name
    for row in c['parts']:
        if entry.get('enabled') and row['reference'] in entry['references']:
            detail=corrected_component(row,entry,c['pcb_thickness_mm'])
            assert detail['entry_direction_uvw']==entry['outward_direction_uvw'][row['reference']]
            entries.append({k:v for k,v in detail.items() if k!='solids'})
            comps.append(detail)
        else:comps.append(component(row))"""
assert s.count(old)==1;s=s.replace(old,new)
old="    mic=c['microphone'];mt=c['pcb_thickness_mm']/2"
new="""    if entries:
        result['CAM']['entry_correction']={'policy':entry,'components':entries}
        bpy.data.objects[PREFIX+'CAM_Mainboard']['connector_entry_review']=json.dumps(result['CAM']['entry_correction'],ensure_ascii=False)
    mic=c['microphone'];mt=c['pcb_thickness_mm']/2"""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("DEFERRED_BY_USER; camera FPC flat reference in detail scene only, no installed route or new holes",
    "CANDIDATE_STUDIES_ONLY; no complete adopted installed harness. Connector illustrative mouths do not establish actual cable contact planes or insertion dimensions.")
path.write_text(s)
path=ROOT/'mechanical/scripts/build.py';s=path.read_text()
old="ROOT/'scripts/waveshare_detail.py',"
assert s.count(old)==1
s=s.replace(old,old+"ROOT/'scripts/cam_fpc_entries.py',PROJECT/P['waveshare_detail']['entry_correction']['direction_receipt'],")
path.write_text(s)

path=ROOT/'contracts/mechanical_interfaces.json';contract=json.loads(path.read_text())
for key in ['revision','mechanical_revision','current_geometry_revision']:
    assert contract[key]=='V1.2-M1.49',(key,contract[key])
    contract[key]='V1.2-M1.50'
contract['cam_entry_correction']=entry
path.write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n')
files=['config/geometry.json','contracts/mechanical_interfaces.json',
    'mechanical/scripts/waveshare_detail.py','mechanical/scripts/cam_fpc_entries.py','mechanical/scripts/build.py']
(OUT/'application.json').write_text(json.dumps(dict(status='PASS',revision=p['revision'],scope=entry,
    files={f:sha(ROOT/f) for f in files},script_sha256=sha(Path(__file__))),ensure_ascii=False,indent=2)+'\n')
print('CAM_ENTRY_SOURCE_ADOPTION_PASS')
