"""Resolve hidden-dependency matrices in the preserved pre-adoption study.

Initial read-only baseline captured hidden dock matrices before dependency
evaluation. Preserve that receipt and add an independently evaluated correction.
"""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
out=ROOT/'input_assets/off_shelf_M1_56'
base=json.loads((out/'baseline.json').read_text())
scene=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=scene
assert scene['native_model_sha256']==base['source_main_sha256']
load_collections()
for c in COLS.values():c.hide_viewport=False
for o in scene.objects:
    if o.get('mori_owner')==OWNER:o.hide_set(False)
assembled();bpy.context.view_layer.update()
rows={}
for o in parts():
    if o.get('group')!='dock':continue
    n=o.name.removeprefix(PREFIX)
    vv=np.array([list(v.co) for v in o.data.vertices],dtype=np.float32)
    assert hashlib.sha256(vv.tobytes()).hexdigest()==base['parts'][n]['local_vertices_sha256']
    rows[n]=[list(r) for r in o.matrix_world]
save_json(out/'evaluated_dock_reference.json',dict(source_file=bpy.data.filepath,
    source_file_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
    preserved_main_sha256=base['source_main_sha256'],matrices=rows,
    reason='Original dock source meshes unchanged; force hidden collection dependency evaluation before reading matrices'))
print('EVALUATED_ORIGINAL_DOCK',len(rows))
