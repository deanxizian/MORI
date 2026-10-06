"""Record actual saved part and CAM component meshes for a bounded correction."""
from pathlib import Path
import json,sys,hashlib
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
ctx=Context();assert ctx.source_hash==json.loads((OUT/'preparation.json').read_text())['source_blend_sha256']
rows={n:dict(fingerprint=ctx.fingerprint(s),group=s.group,category=s.o.get('category'),
            bounds_mm=[s.lo.tolist(),s.hi.tolist()],vertices=len(s.v),triangles=len(s.f)) for n,s in ctx.ss.items()}
s=ctx.ss['CAM_Mainboard'];index=json.loads(s.o['component_reference_index'])
# Component index addresses the original object's mesh, not the union-solid
# triangulation. Save those vertices/faces with the exact world transform.
v=np.asarray([tuple(s.o.matrix_world@p.co) for p in s.o.data.vertices],float)
f=np.asarray([tuple(p.vertices) for p in s.o.data.polygons],np.uint64)
np.savez_compressed(OUT/'CAM_before.npz',vertices_mm=v,triangles=f)
(OUT/'CAM_before_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
ctx.assert_unchanged()
(OUT/'baseline.json').write_text(json.dumps(dict(status='PASS',sources=ctx.sources,parts=rows,
    component_mesh_sha256=sha(OUT/'CAM_before.npz'),component_index_sha256=sha(OUT/'CAM_before_index.json'),
    script_sha256=sha(Path(__file__))),ensure_ascii=False,indent=2)+'\n')
print('CAM_ENTRY_BASELINE_PASS',len(rows),len(index))
