import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
from common import *
from validate import Solid
from export import topology
from neck_reference import approved
from mathutils.bvhtree import BVHTree
load_collections();assembled();bpy.context.view_layer.update()
for name in ['Yaw_Base','Pitch_Yoke']:
 s=Solid(bpy.data.objects[PREFIX+name]);m=s.m;a=approved(name)
 d=a.to_mesh64();a32=manifold.Manifold(manifold.Mesh64(np.array(d.vert_properties[:,:3],dtype=np.float32).astype(np.float64),np.array(d.tri_verts,dtype=np.uint64,copy=True,order="C")))
 for i in [.000005,.00001,.00002,.00005,.0001]:
  m=s.m
  d=m.simplify(i).to_mesh64();v=np.array(d.vert_properties[:,:3],dtype=np.float32).astype(np.float64);f=np.array(d.tri_verts,dtype=np.uint64,copy=True,order="C")
  m=manifold.Manifold(manifold.Mesh64(v,f));t=topology(v,f.tolist())
  print(name,i,t,'candidate32_delta',max(0,(m-a32).volume())+max(0,(a32-m).volume()),'saved_delta',max(0,(m-s.m).volume())+max(0,(s.m-m).volume()),flush=True)

