import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
from interface_completion import change_regions
load_collections();assembled();bpy.context.view_layer.update()
b=json.loads((HERE/'baseline_geometry.json').read_text())
for n in ['Dock_Pad_0','Parking_Cradle']:
 print(n,'OLD',b['parts'][n],'NEW',geometry_record(bpy.data.objects[PREFIX+n]))
r=b['Head_Front'];old=manifold.Manifold(manifold.Mesh64(np.array(r['vertices_mm']),np.array(r['triangles'],dtype=np.uint64)));new=Solid(bpy.data.objects[PREFIX+'Head_Front']).m;zone=change_regions()['Head_Front']
from mathutils.bvhtree import BVHTree
bo=BVHTree.FromPolygons(r['vertices_mm'],r['triangles'],all_triangles=True)
d=new.to_mesh64();bn=BVHTree.FromPolygons(d.vert_properties[:,:3].tolist(),d.tri_verts.tolist(),all_triangles=True)
results=[]
for label,mesh,tree in [('old_to_new',old,bn),('new_to_old',new,bo)]:
 data=mesh.to_mesh64();vs=data.vert_properties[:,:3];faces=data.tri_verts;points=np.concatenate([vs,vs[faces].mean(1)]);distances=[]
 for p in points:
  hit=zone.ray_cast(p.tolist(),(p+[500,0,0]).tolist())
  if hit and hit[0].normal[0]>0:continue
  loc,normal,idx,distance=tree.find_nearest(Vector(p));distances.append(float(distance))
 results.append({'id':label,'samples':len(distances),'max_distance_mm':max(distances)})
print('SURFACE_DEVIATION',results,flush=True)
(HERE/'surface_deviation.json').write_text(json.dumps(results,indent=2))
