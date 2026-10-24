"""One-time M1.57 receipt; frozen meshes are verification inputs only."""
import sys,hashlib,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
out=ROOT/'input_assets/ups_controls_M1_58';study=ROOT/'studies/off_shelf_modules_20261013/ups_controls_M1_57'
assert not (out/'baseline.json').exists(),'Never overwrite a receipt'
assert P['revision']=='V1.2-M1.57'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt=json.loads((study/'receipt.json').read_text())
for f,h in receipt['protected'].items():assert sha(PROJECT/f)==h,f
out.mkdir(parents=True,exist_ok=True)
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
for c in COLS.values():c.hide_viewport=False
bpy.context.view_layer.update();rows={}
for o in parts():
 n=o.name.removeprefix(PREFIX);o.data.calc_loop_triangles()
 vv=np.array([list(v.co) for v in o.data.vertices],dtype=np.float32);ff=np.array([list(f.vertices) for f in o.data.loop_triangles],dtype=np.uint32)
 rows[n]=dict(vertices_sha256=hashlib.sha256(vv.tobytes()).hexdigest(),triangles_sha256=hashlib.sha256(ff.tobytes()).hexdigest(),matrix_world=[list(r) for r in o.matrix_world],category=o.get('category'),data_status=o.get('data_status'),group=o.get('group'))
 if n=='Body_Rear':
  s=Solid(o);np.savez_compressed(out/'body_rear_before.npz',vertices=s.v,triangles=s.f)
for n in ['candidate_check.json','candidate_meshes.json','saved_verification.json','clearance_check.json','sample_switch_current_receipt.json','receipt.json']:
 shutil.copy2(study/n,out/n)
shutil.copytree(study/'sources',out/'sources')
for f,dest in [('config/geometry.json','geometry_M1_57.json'),('contracts/mechanical_interfaces.json','interfaces_M1_57.json'),('mechanical/reports/validation.json','validation_M1_57.json'),('mechanical/reports/dc_inlet_validation.json','dc_inlet_validation_M1_57.json')]:shutil.copy2(PROJECT/f,out/dest)
backup=ROOT/'revisions/V1.2-M1.57_before_UPS_controls/mechanical';backup.mkdir(parents=True,exist_ok=True)
assert not (backup/'mori_v1_2.blend').exists();shutil.copy2(ROOT/'mori_v1_2.blend',backup/'mori_v1_2.blend')
base=json.loads((PROJECT/P['off_shelf_modules']['baseline']).read_text());protected={f:sha(PROJECT/f) for f in base['protected_hardware']}
drift={f:dict(before=h,received=protected[f]) for f,h in base['protected_hardware'].items() if protected[f]!=h}
save_json(out/'hardware_receipt.json',dict(revision='V1.2-H0.6-UPS-R1',owner_thread='01a0c24f-ddc2-7f03-a9d4-d09dff26d30f',scope='Authorized owner requirements and documentation update; received read-only. Native carrier geometry remains P5R7 reference pending new board design.',owner_changes_since_M1_56=drift,protected_hardware=protected,mechanical_edits_to_hardware=False))
save_json(out/'approval.json',dict(date='2026-10-13',answer='采用上充电、下开关',question_id='call_16d12c091c5e41899ce42b4cd4c0f731',scope='Keep approved upper DC; replace former USB opening with lower UPS original switch trial seat, remove rear interface PCB and its two seats and four fasteners. Only Body_Rear print changes. No video.',approved_candidate_sha256=sha(study/'candidate_meshes.json'),physical_fit='NOT_TESTED',manufacturing_release=False))
save_json(out/'baseline.json',dict(revision=P['revision'],source_main_sha256=sha(ROOT/'mori_v1_2.blend'),preserved_main=str((backup/'mori_v1_2.blend').relative_to(PROJECT)),parts=rows,verification_only=True,protected_video={f:h for f,h in receipt['protected'].items() if f in ['mechanical/mori_assembly_animation.blend','mechanical/animation/MORI_assembly.mp4']},files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}))
print('UPS_CONTROLS_BASELINE_CAPTURED',len(rows),len(drift),flush=True)
