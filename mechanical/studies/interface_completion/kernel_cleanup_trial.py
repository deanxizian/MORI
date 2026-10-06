import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from export import topology
load_collections();assembled();bpy.context.view_layer.update();rows=[]
for name in ['Head_Front','Head_Rear','Body_Upper']:
 m=Solid(bpy.data.objects[PREFIX+name]).m;tests=[]
 for tol in [.00001,.00005,.0001,.0002,.0005,.001]:
  for mode in ['simple','original','input']:
   if mode=='original':a=m.as_original().simplify(tol)
   elif mode=='simple':a=m.set_tolerance(tol).simplify(tol)
   else:
    d=m.to_mesh64();a=manifold.Manifold(manifold.Mesh64(np.array(d.vert_properties,dtype=np.float64,order='C'),np.array(d.tri_verts,dtype=np.uint64,order='C'),tolerance=tol)).simplify(tol)
   d=a.to_mesh64();v=np.asarray(d.vert_properties[:,:3],dtype=np.float32).astype(np.float64);f=d.tri_verts;t=topology(v.tolist(),f.tolist());b=manifold.Manifold(manifold.Mesh64(np.array(v,dtype=np.float64,order='C'),np.array(f,dtype=np.uint64,order='C')))
   tests.append({'tol':tol,'mode':mode,'status':str(b.status()),'degenerate':t['degenerate_triangles'],'nonmanifold':t['nonmanifold_edges'],'triangles':t['triangles'],'delta_mm3':max(0,(m-a).volume())+max(0,(a-m).volume())})
 rows.append({'id':name,'tests':tests})
(HERE/'kernel_cleanup_trial.json').write_text(json.dumps(rows,indent=2));print('KERNEL_CLEANUP',rows,flush=True)
