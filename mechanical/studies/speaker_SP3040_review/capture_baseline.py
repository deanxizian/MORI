"""Immutable geometry evidence before replacing the speaker; read only scene."""
import sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from common import *
from validate_head_cleanup import geometry_record
bpy.context.window.scene = bpy.data.scenes['MORI_V1_Assembly']
load_collections()
for n in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
out = Path(__file__).parent / 'baseline_geometry_evaluated.json'
assert not out.exists(), 'Do not replace immutable comparison evidence'
r = {'revision': 'V1.2-M1.36', 'source_blend_sha256': hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
     'capture_note': 'Explicitly evaluate hidden dock/coupon transforms; supersedes initial capture that left their cached matrices unevaluated. Archived original source blend is unchanged.',
     'parts': {o.name.removeprefix(PREFIX): geometry_record(o) for o in parts()}}
o = bpy.data.objects[PREFIX + 'Body_Upper']; o.data.calc_loop_triangles()
r['Body_Upper'] = {'vertices_mm': [list(o.matrix_world @ v.co) for v in o.data.vertices],
                   'triangles': [list(t.vertices) for t in o.data.loop_triangles]}
save_json(out, r)
print('SPEAKER_BASELINE_SAVED', out)
