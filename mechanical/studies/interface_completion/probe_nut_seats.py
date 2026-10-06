"""Read existing nut bearing lands; do not infer seats from floating hardware."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
rows=json.loads((HERE/'nut_review.json').read_text())['rows'];ff={r['id']:r for r in json.loads((HERE/'fastener_current.json').read_text())};out=[]
for r in rows:
 axis=np.array(ff[r['screw']]['extracted_axis_outward']);p=np.array(r['nominal_candidate_center_mm']);s=Solid(bpy.data.objects[PREFIX+r['host']]);u=np.cross(axis,[1,0,0] if abs(axis[0])<.9 else [0,1,0]);u/=np.linalg.norm(u);v=np.cross(axis,u);dist=[]
 for angle in range(0,360,15):
  q=p+(u*math.cos(math.radians(angle))+v*math.sin(math.radians(angle)))*(2.1 if r['thread']=='M3' else 1.6)
  hs=s.m.ray_cast(q.tolist(),(q+axis*12).tolist());h=next((h for h in hs if np.dot(h.normal,axis)<-.5),None)
  if h:dist.append(h.distance*12)
 out.append({'id':r['id'],'host':r['host'],'center':p.tolist(),'axis':axis.tolist(),'bearing_distances_mm':dist,'old_nominal_bearing_distance':r['height_mm']/2})
(HERE/'nut_seat_probes.json').write_text(json.dumps(out,indent=2));print('NUT_SEATS',[(r['id'], sorted(set(round(x,3) for x in r['bearing_distances_mm']))) for r in out],flush=True)
