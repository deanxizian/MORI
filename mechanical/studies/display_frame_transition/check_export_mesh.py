"""Preflight the current edit on the immutable original, including STL roundtrip."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from display_frame_simplification import apply_display_frame_simplification,dimensions
from validate import Solid
from export import write_stl,read_stl,topology
from monocoque_structure import obj,source_build
here=Path(__file__).parent
load_collections()
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[n].hide_viewport=False
assembled();source_build().materials();bpy.context.view_layer.update()
original=Solid(obj('Display_Frame')).m
apply_display_frame_simplification()
o=obj('Display_Frame');m=Solid(o).m
p=here/'Display_Frame_preflight.stl';write_stl(o,p);v,f,n=read_stl(p);t=topology(v,f,n)
r={'status':str(m.status()),'volume_mm3':m.volume(),'stl_topology':t}
from mathutils.bvhtree import BVHTree
def shape(row):return manifold.Manifold(manifold.Mesh64(np.array(row['vertices_mm']),np.array(row['triangles'],dtype=np.uint64)))
def separation(a,b,outside=False):
 d=dimensions();ma=a.to_mesh64();mb=b.to_mesh64();av=ma.vert_properties[:,:3];af=ma.tri_verts
 bv=mb.vert_properties[:,:3];bf=mb.tri_verts;tree=BVHTree.FromPolygons([Vector(x) for x in bv],bf.tolist(),all_triangles=True)
 pts=np.concatenate([av,av[af].mean(axis=1)]);rows=[]
 for p in pts:
  if outside and -d['outer']-.02<=p[0]<=d['outer']+.02 and d['earback']-.02<=p[1]<=d['front']+.02 and d['bot']-.02<=p[2]<=d['join1']+.02:continue
  result=tree.find_nearest(Vector(p));rows.append((float(result[3]),p.tolist()))
 return {'max_mm':max(rows)[0],'worst_point_mm':max(rows)[1],'samples':len(rows)}
target=shape(json.loads((here/'approved_geometry.json').read_text())['Display_Frame'])
r['accepted_volume_difference_mm3']=max(0,(m-target).volume())+max(0,(target-m).volume())
r['outside_region_volume_mm3']=max(0,((m-original)-__import__('display_frame_simplification').change_region()).volume())+max(0,((original-m)-__import__('display_frame_simplification').change_region()).volume())
r['source_outside_region_distance']=[separation(m,original,True),separation(original,m,True)]
r['accepted_distance']=[separation(m,target),separation(target,m)]
from display_frame_simplification import cylinder
mask=manifold.Manifold();q=P['readiness_completion']['lcd']
for row in json.loads((ROOT/'reports/readiness_geometry.json').read_text())['LCD']:
 axis=np.array(row['axis']);p0=np.array(row['post_face_mm']);f0=np.array(row['head_bearing_mm'])
 mask+=cylinder(p0-axis*15,axis,q['clearance_radius_mm']+.01,60)
 mask+=cylinder(f0-axis*20,axis,q['spotface_radius_mm']+.01,20.01)
r['accepted_difference_outside_lcd_cutters_mm3']=max(0,((m-target)-mask).volume())+max(0,((target-m)-mask).volume())
(here/'export_mesh_preflight.json').write_text(json.dumps(r,indent=2)+'\n')
print('PREFLIGHT',json.dumps(r),flush=True)
