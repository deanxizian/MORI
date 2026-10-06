"""Current all-print opposed-normal sampling; no geometry changes."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from export import topology
load_collections()
for c in COLS.values():c.hide_viewport=False
assembled();bpy.context.view_layer.update();rows=[]
ids={r['id'] for r in json.loads((ROOT/'reports/bom.json').read_text()) if r['candidate_stl']}
for o in parts(True):
 if o.name.removeprefix(PREFIX) not in ids:continue
 s=Solid(o);tri=s.v[s.f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cross,axis=1)/2;ns=cross/np.maximum(ar[:,None]*2,1e-15)
 indices=np.unique(np.searchsorted(np.cumsum(ar),np.linspace(0,ar.sum(),20002)[1:-1]));rays=[];b=s.bvh()
 for i in indices:
  p=tri[i].mean(0);n=ns[i];h,hn,j,d=b.ray_cast(Vector(p-n*.0001),Vector(-n),300)
  if h is not None and j!=i and n@np.array(hn)<-.95 and d>.02:rays.append((float(d+.0001),p.tolist()))
 rays.sort();t=topology(s.v,s.f)
 rows.append({'id':s.name,'group':s.group,'samples':len(rays),'sampled_minimum_mm':rays[0][0] if rays else None,'under_1mm_samples':sum(r[0]<1 for r in rays),'critical_samples':rays[:8],'topology':t})
 print('FINAL_PRINT',s.name,rows[-1]['sampled_minimum_mm'],flush=True)
out={'revision':P['revision'],'source_blend_sha256':hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),'rows':rows,'global_wall_proof':'NOT_TESTED','method':'Area-stratified up to20000 triangle-centroid inward rays per part, opposing normals dot<-0.95. Sharp tapers and functional lead-ins need classification; sampled minima are not global minima or strength qualification.'}
(ROOT/'reports/interface_printability.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
