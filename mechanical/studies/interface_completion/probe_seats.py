import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from mathutils.bvhtree import BVHTree
load_collections();assembled();bpy.context.view_layer.update()
a=json.loads((HERE/'baseline_audit.json').read_text());cand=json.loads((HERE/'insert_candidate.json').read_text())['rows'];rows=[]
for old,c in zip(a['inserts'],cand):
 s=Solid(bpy.data.objects[PREFIX+c['host']]);b=BVHTree.FromPolygons(s.v.tolist(),s.f.tolist(),all_triangles=True)
 mid=np.array(old['center_mm']);axis=np.array(c['outward']);u=np.cross(axis,[1,0,0] if abs(axis[0])<.9 else [0,1,0]);u/=np.linalg.norm(u);v=np.cross(axis,u);ends=[]
 for th in np.arange(0,360,45):
  d=u*math.cos(math.radians(th))+v*math.sin(math.radians(th));origin=mid+d*(old['reference_pilot_diameter_mm']/2+.35)
  q=b.ray_cast(Vector(origin),Vector(axis),10)
  q2=b.ray_cast(Vector(origin),Vector(-axis),12)
  ends.append([round(q[3],4) if q[0] else None,round(q2[3],4) if q2[0] else None])
 rows.append({'id':c['id'],'outward':c['outward'],'mid':mid.tolist(),'host_ends':ends})
print(json.dumps(rows,indent=2));(HERE/'seat_probes.json').write_text(json.dumps(rows,indent=2))
