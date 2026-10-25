"""One-time M1.56 receipt for the approved M1.57 DC trial seat.

Saved meshes are independent verification references, never construction inputs.
"""
import sys, hashlib, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *
from validate import Solid

out=ROOT/'input_assets/dc_trial_M1_57'
assert not (out/'baseline.json').exists(), 'Never overwrite the pre-adoption receipt'
out.mkdir(parents=True,exist_ok=True)
study=ROOT/'studies/off_shelf_modules_20261013/dc_interface_M1_56'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert P['revision']=='V1.2-M1.56'
candidate=json.loads((study/'sample_mount_candidate_check.json').read_text())
assert candidate['source_blend_sha256']==sha(ROOT/'mori_v1_2.blend')
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
for c in COLS.values():c.hide_viewport=False
bpy.context.view_layer.update()
rows={}
for o in parts():
    n=o.name.removeprefix(PREFIX);o.data.calc_loop_triangles()
    vv=np.array([list(v.co) for v in o.data.vertices],dtype=np.float32)
    ff=np.array([list(f.vertices) for f in o.data.loop_triangles],dtype=np.uint32)
    rows[n]=dict(vertices_sha256=hashlib.sha256(vv.tobytes()).hexdigest(),
        triangles_sha256=hashlib.sha256(ff.tobytes()).hexdigest(),
        matrix_world=[list(r) for r in o.matrix_world],category=o.get('category'),
        data_status=o.get('data_status'),group=o.get('group'))
    if n=='Body_Rear':
        s=Solid(o);np.savez_compressed(out/'body_rear_before.npz',vertices=s.v,triangles=s.f)
for name in ['sample_mount_candidate_check.json','sample_mount_candidate_meshes.json',
             'sample_dimensions.json','sample_current_receipt.json','photo_installation_update.json']:
    shutil.copy2(study/name,out/name)
shutil.copytree(study/'sources',out/'sources',dirs_exist_ok=True)
shutil.copy2(PROJECT/'config/geometry.json',out/'geometry_M1_56.json')
shutil.copy2(PROJECT/'contracts/mechanical_interfaces.json',out/'interfaces_M1_56.json')
for n in ['validation','off_shelf_scope','off_shelf_delivery','export_manifest']:
    shutil.copy2(ROOT/'reports'/f'{n}.json',out/f'{n}_M1_56.json')
save_json(out/'approval.json',dict(date='2026-10-13',answer='采用，先按样品尺寸做试配孔座',
    scope='Adopt the reviewed rear-center DC trial seat near z130: diameter8 trial bore, diameter15 seat, 4mm nominal wall, 0.5mm external seat recess. Only Body_Rear changes; no new print or switch hole.',
    source_candidate_sha256=sha(study/'sample_mount_candidate_meshes.json'),
    sample_references='Existing sample jack and its nut retained as ASSUMED capacity illustrations; not exact rigid product or lead geometry.',
    actual_fit='NOT_TESTED',complete_lead_passage='BLOCKED',manufacturing_release=False))
save_json(out/'baseline.json',dict(revision=P['revision'],source_main_sha256=sha(ROOT/'mori_v1_2.blend'),
    parts=rows,verification_only=True,
    files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}))
print('DC_BASELINE_CAPTURED',len(rows),flush=True)
