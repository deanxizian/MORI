"""Read-only diagnosis of viewport activation and validation-proxy transforms."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import *
from validate import Solid
ctx=Context()
rows=[]
def probe(stage):
    out=[]
    for name,s in ctx.ss.items():
        now=Solid(s.o)
        if ctx.fingerprint(now)!=ctx.print_fingerprints[name]:
            proxy=bpy.data.objects[s.o['validation_proxy']] if s.o.get('validation_proxy') else s.o
            out.append(dict(name=name,proxy=proxy.name,
                native_parent=s.o.parent.name if s.o.parent else None,
                proxy_parent=proxy.parent.name if proxy.parent else None,
                v_shape=list(now.v.shape),baseline_shape=list(s.v.shape),
                max_vertex_change=float(np.max(np.abs(now.v-s.v))) if now.v.shape==s.v.shape else None,
                faces_equal=bool(np.array_equal(now.f,s.f)),
                matrix=[list(row) for row in proxy.matrix_world]))
    rows.append(dict(stage=stage,differences=out));print(stage,json.dumps(out),flush=True)
probe('baseline')
for c in COLS.values():c.hide_render=False
bpy.context.view_layer.update();probe('render_only')
for c in COLS.values():c.hide_viewport=False
bpy.context.view_layer.update();probe('viewport_enabled')
assembled();bpy.context.view_layer.update();probe('assembled_again')
(HERE/'preview_diagnosis.json').write_text(json.dumps(dict(source=ctx.source_hash,stages=rows),indent=2)+'\n')
assert sha(ctx.main)==ctx.source_hash
