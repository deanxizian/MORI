"""One-time read-only receipt of the pre-adoption assembly and approved study.

The captured meshes are verification references, never construction inputs.
"""
import sys, hashlib, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *
from validate import Solid

out = ROOT / 'input_assets/off_shelf_M1_56'
assert not (out / 'baseline.json').exists(), 'Do not replace the original baseline'
out.mkdir(parents=True, exist_ok=True)
bpy.context.window.scene = bpy.data.scenes['MORI_V1_Assembly']
load_collections(); assembled(); bpy.context.view_layer.update()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows = {}; arrays = {}
for o in parts():
    n = o.name.removeprefix(PREFIX)
    o.data.calc_loop_triangles()
    vv = np.array([list(v.co) for v in o.data.vertices], dtype=np.float32)
    ff = np.array([list(f.vertices) for f in o.data.loop_triangles], dtype=np.uint32)
    s = Solid(o)
    arrays[n + '_v'] = s.v; arrays[n + '_f'] = s.f
    rows[n] = dict(local_vertices_sha256=hashlib.sha256(vv.tobytes()).hexdigest(),
                   local_faces_sha256=hashlib.sha256(ff.tobytes()).hexdigest(),
                   matrix_world=[list(r) for r in o.matrix_world],
                   bounds_xyz_mm=bounds(o), category=o.get('category'), group=o.get('group'))
np.savez_compressed(out / 'baseline_solids.npz', **arrays)
shutil.copy2(PROJECT/'config/geometry.json', out/'geometry_M1_55.json')
shutil.copy2(PROJECT/'contracts/mechanical_interfaces.json', out/'interfaces_M1_55.json')
study = ROOT/'studies/off_shelf_modules_20261013/controller_center'
for source, dest in [('candidate_checks.json', 'center_checks.json'),
                     ('generated_candidate_meshes.json', 'center_reference.json'),
                     ('ups_mount_review/direct_checks.json', 'direct_checks.json'),
                     ('ups_mount_review/direct_meshes.json', 'direct_reference.json')]:
    shutil.copy2(study/source, out/dest)
files = [p for p in (PROJECT/'hardware').rglob('*') if p.is_file()
         and p.name != '.DS_Store' and '__pycache__' not in p.parts]
files += [PROJECT/'contracts/components.json']
protected = {str(p.relative_to(PROJECT)): sha(p) for p in files}
record = dict(revision=P['revision'], source_main_sha256=sha(ROOT/'mori.blend'),
              parts=rows, protected_hardware=protected,
              approval='USER_APPROVED: 采用直固方案（推荐）', date='2026-10-13',
              verification_only=True,
              reference_files={p.name:sha(p) for p in out.iterdir() if p.is_file()})
save_json(out/'baseline.json', record)
print('BASELINE_CAPTURED', len(rows), len(protected), flush=True)
