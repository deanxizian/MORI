import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from export import topology
from interface_completion import apply_interface_completion
from monocoque_structure import source_build
import interface_completion
# Reconstruct only the approved phase on immutable M1.41, with tested cleanup variants.
load_collections();assembled();source_build().materials()
src=Path(interface_completion.__file__).read_text();src=src[:src.index('    for name in {r[\'host\'] for r in rows}')]+src[src.index('    from readiness_completion import paint_integral_rim'):];src=src.replace("mm_mesh('interface_construction_mesh',m)","mm_mesh('interface_construction_mesh',m.simplify(.0005))")
exec(compile(src,interface_completion.__file__,'exec'),interface_completion.__dict__);interface_completion.apply_interface_completion()
rows=[]
for name in ['Head_Front','Head_Rear','Body_Upper']:
 o=bpy.data.objects[PREFIX+name];base=o.data.copy();tests=[]
 for tol in [0,.000005,.00002,.00005,.0001,.0002]:
  o.data=base.copy()
  if tol:
   bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=tol);bmesh.ops.dissolve_degenerate(bm,dist=tol,edges=list(bm.edges));bm.to_mesh(o.data);bm.free();o.data.update()
  o.data.calc_loop_triangles();v=np.array([tuple(o.matrix_world@p.co) for p in o.data.vertices]);f=np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.uint64);m=manifold.Manifold(manifold.Mesh64(v,f));t=topology(v.tolist(),f.tolist());tests.append({'tolerance':tol,'manifold':str(m.status()),**t})
 o.data=base
 rows.append({'id':name,'tests':tests})
print('REPAIR_TRIAL',rows,flush=True);(HERE/'repair_surface_trial.json').write_text(json.dumps(rows,indent=2))
