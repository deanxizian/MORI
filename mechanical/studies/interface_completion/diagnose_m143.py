import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from assembly_issue_fixes import change_regions,boxm
load_collections();COLS['DATUMS'].hide_viewport=False;assembled()
b=json.loads((ROOT/'studies/interface_completion/six_fix_baseline.json').read_text());ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts()}
for n in ['Drive_L_-8_Nut','Drive_R_8_Nut','Head_Pitch_Ear_0_Nut']:
 s=ss[n];print('BOUNDS',n,s.lo.tolist(),s.hi.tolist(),flush=True)
for n in ['Drive_Bridge','Pitch_Yoke']:
 r=b[n];old=manifold.Manifold(manifold.Mesh64(np.array(r['vertices_mm']),np.array(r['triangles'],dtype=np.uint64)));d=((ss[n].m-old)+(old-ss[n].m))-change_regions()[n]
 print('RESIDUAL',n,[(x.volume(),x.bounding_box()) for x in d.decompose() if x.volume()>.001],flush=True)
 if n=='Drive_Bridge':
  for y in [-8,8]:
   nut=ss[f'Drive_R_{y}_Nut'];c=(nut.lo+nut.hi)/2;ys=sorted([y,18 if y>0 else -18]);cut=boxm([c[0]-2.5,ys[0],c[2]-.95],[c[0]+2.5,ys[1],c[2]+.95]);print('SLOT_REMAINDER',c.tolist(),(cut^ss[n].m).volume(),flush=True)
s=ss['Body_Lower'];tri=s.v[s.f];p=np.array([23.7111269633,73.8198750814,88.8527297974]);i=np.argmin(np.linalg.norm(tri.mean(1)-p,axis=1));pts=tri[i];nv=np.cross(pts[1]-pts[0],pts[2]-pts[0]);nv/=np.linalg.norm(nv);h,hn,j,d=s.bvh().ray_cast(Vector(p-nv*.0001),Vector(-nv),300);print('THIN_RAY',i,pts.tolist(),'area',np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0]))/2,'normal',nv.tolist(),'hit',tuple(h),tuple(hn),j,d,tri[j].tolist(),flush=True)
