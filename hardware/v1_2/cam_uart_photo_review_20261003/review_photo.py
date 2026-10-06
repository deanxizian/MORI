"""Record photo observations and check their logical/zero-pose correspondence."""
from pathlib import Path
import ast,csv,datetime,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
assert not(HERE/'delivery_manifest.json').exists(),'Use a new revision for published records'
(HERE/'sources').mkdir(exist_ok=True)
inputs=[
 'mechanical/sources/waveshare_detail/esp32-s3-cam-ovxxxx-3_1.jpg',
 'mechanical/sources/waveshare_detail/source_manifest.json',
 'mechanical/sources/waveshare_detail/browser_assets_2.json',
 'config/geometry.json',
 'mechanical/scripts/waveshare_detail.py',
 'mechanical/studies/prearrival_finish/harness_A8/check_cam_uart_mating_allocation.py',
 'mechanical/studies/prearrival_finish/harness_A8/cam_pitch_port/mating_allocation.json',
 'hardware/v1_2/head_harness_evidence_20261003/head_interface_pinmap_revA.csv',
]
snapshots=[]
for rel in inputs:
    p=ROOT/rel;dst=HERE/'sources'/p.name
    if dst.exists():assert sha(dst)==sha(p)
    else:shutil.copy2(p,dst)
    snapshots.append(dict(source=rel,snapshot=str(dst.relative_to(ROOT)),sha256=sha(dst)))
S=HERE/'sources';photo=S/'esp32-s3-cam-ovxxxx-3_1.jpg'
assert sha(photo)=='018cefb8862e411ebb126abadc5bb6dbbeb1b8ab99207918ba9e70d0504295b8'
origin=next(r for r in json.loads((S/'source_manifest.json').read_text())['sources']if r['file'].endswith(photo.name))
assert origin['sha256']==sha(photo)
pinrows=[r for r in csv.DictReader((S/'head_interface_pinmap_revA.csv').open())if r['reference']=='CAM J11']
assert [r['pin']for r in pinrows]==['1','2','3','4']
expected={1:'CAM_RX / GPIO44',2:'CAM_TX / GPIO43',3:'CAM local 3V3',4:'GND'}
assert all(r['function']==expected[int(r['pin'])]for r in pinrows)

cfg=json.loads((S/'geometry.json').read_text());cam=cfg['waveshare_detail']['cam']
hole_x=[p[0]for p in cam['photo_registration']['centers_px']]
cx=(max(hole_x)+min(hole_x))/2
scale=cam['hole_grid_mm']/(max(hole_x)-min(hole_x))
registration=[]
for name in ['UART_4P','I2C_4P']:
    part=next(p for p in cam['parts']if p['reference']==name)
    assert part['side']=='IC'
    u=-(part['photo_center_px'][0]-cx)*scale
    assert abs(u-part['center_uv_mm'][0])<.011
    registration.append(dict(reference=name,photo_x=part['photo_center_px'][0],derived_u_mm=u,stored_u_mm=part['center_uv_mm'][0],status='PASS',scope='Existing reconstruction registration, not measured geometry'))
tree=ast.parse((S/'waveshare_detail.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='apply_waveshare_detail')
assign=next(n for n in fn.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='r'for t in n.targets))
matrix=ast.literal_eval(assign.value.args[0])
assert matrix==[[1.,0,0],[0,0,-1.],[0,1.,0]]
allocation=json.loads((S/'mating_allocation.json').read_text())
slots=allocation['estimated_datum']['exit_geometric_slots_mm']
assert len(slots)==4 and all(slots[i][0]<slots[i+1][0]for i in range(3))
assert allocation['source_script_sha256']==sha(S/'check_cam_uart_mating_allocation.py')

# Read visually from the unmodified source image in this review, not OCR or CAD.
observed=['GND','3V3','TXD','RXD'];pins=[4,3,2,1]
rows=[dict(photo_left_to_right_index=i+1,observed_silkscreen=label,existing_logical_pin=pin,
           inferred_zero_pose_slot_index=pin-1,slot_mapping_evidence='ASSUMED_MODEL_INFERENCE',actual_mating_cavity_view='BLOCKED')
      for i,(label,pin)in enumerate(zip(observed,pins))]
with (HERE/'position_mapping.csv').open('w',newline='')as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
dump(HERE/'evidence.json',dict(revision='CAM-UART-PHOTO-01',review_date='2026-10-03',photo_url=origin['url'],photo_sha256=sha(photo),
 review_scope='Visible board-face labels and conditional logical position correspondence only',
 photo_orientation='IC/component face front view; Type-C bottom; UART bottom right',photo_mirrored=False,photo_cropped=False,
 official_photo_position_status='PASS',electrical_map_correspondence='PASS',rows=rows,
 registration_checks=registration,zero_pose_rotation_matrix=matrix,
 inferred_photo_right_to_world_axis='-X at the recorded neutral pose',geometric_slot_indices_in_increasing_X=[0,1,2,3],
 inferred_logical_pins_in_increasing_X=[1,2,3,4],slot_inference_evidence='ASSUMED',actual_header_mpn=None,
 actual_header_mating_front_view=None,wire_housing_mating_view=None,wire_exit_view=None,actual_cavity_dimensions_mm=None,
 physical_continuity='NOT_TESTED',manufacturing_status='BLOCKED',pinmap_modified=False,PCB_modified=False,mechanical_sources_modified=False,
 physical_cavity_field_in_A7_remains_valid='BLOCKED refers to actual cavity views; visible photo board-face order is now separately available',
 live_web_image_retrieval='BLOCKED: image URL not accessible by web tool in this review; existing source photo reviewed',
 viewed_image=str(photo.relative_to(ROOT)),source_snapshots=snapshots))

checks=[]
for rel in ['hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json',
 'hardware/v1_2/head_harness_evidence_20261003/delivery_manifest.json',
 'hardware/v1_2/reviews/J10_C3_visual_20261003/delivery_manifest.json',
 'hardware/v1_2/head_harness_A8_20261003/delivery_manifest.json',
 'hardware/v1_2/harness_process_reference_20261003/delivery_manifest.json',
 'hardware/v1_2/harness_process_comparison_20261003/delivery_manifest.json']:
    data=json.loads((ROOT/rel).read_text());files=data.get('files',data)
    changed=[n for n,h in files.items()if not(ROOT/n).exists()or sha(ROOT/n)!=h]
    checks.append(dict(manifest=rel,checked=len(files),changed=changed,status='FAIL'if changed else'PASS'))
assert all(r['status']=='PASS'for r in checks)
assert all(sha(ROOT/r['source'])==r['sha256']for r in snapshots),'Source changed during review'
dump(HERE/'preservation_check.json',checks)
files={str(p.relative_to(ROOT)):sha(p)for p in HERE.rglob('*')if p.is_file()and p.name!='delivery_manifest.json'}
dump(HERE/'delivery_manifest.json',dict(status='PASS',scope='Evidence file integrity only',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files))
print(json.dumps(dict(files=len(files),photo_left_to_right=observed,logical_left_to_right=pins,inferred_slots_to_pins=[1,2,3,4],protected_files=sum(r['checked']for r in checks),source_preservation='PASS'),ensure_ascii=False,indent=2))
