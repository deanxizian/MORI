from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
from export import topology
load_collections();assembled()
for name in ['Yaw_Base','Pitch_Yoke']:
 s=Solid(bpy.data.objects[PREFIX+name]).m
 for tol in [.0005,.001,.002,.005,.01]:
  m=s.simplify(tol);d=m.to_mesh64();v=np.array(d.vert_properties[:,:3],dtype=np.float32);f=d.tri_verts
  t=topology(v,f);q=manifold.Manifold(manifold.Mesh64(np.array(v.tolist(),dtype=np.float64),np.array(f.tolist(),dtype=np.uint64)));delta=max(0,(s-q).volume())+max(0,(q-s).volume())
  print(name,tol,t,'delta',delta,flush=True)
