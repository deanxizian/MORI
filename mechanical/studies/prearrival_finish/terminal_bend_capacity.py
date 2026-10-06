"""Report a constrained connector's available space; do not qualify a cable."""
from pathlib import Path
REVIEW=Path(__file__).resolve().parent
helper=(REVIEW/'route_bezier_trials.py').read_text().split('results=[]')[0]
exec(compile(helper,str(REVIEW/'route_bezier_trials.py'),'exec'),globals())
r=1.4;ea,a,aa=endpoint('motion_J7',r);eb,b,ab=endpoint('power_J10',r)
ea+=np.array([4,0,0]);a+=np.array([4,0,0]);eb+=np.array([0,4,0]);b+=np.array([0,4,0])
best=None;tried=0
for c in candidates('H05_splitB',a,b,aa,ab):
 tried+=1;mr=curve_radius(c)
 if mr<3 or (best and mr<=best['minimum_curvature_radius_mm']):continue
 curve=bezier(c,np.linspace(0,1,241));pts=resample(curve,.5)
 if not all(rigid_free(p,r+.3) for p in pts):continue
 if solid_hits(curve,r):continue
 best=dict(controls_mm=np.array(c).tolist(),curve_mm=curve.tolist(),minimum_curvature_radius_mm=mr,bundle_diameter_requirement_mm=2*r)
ray=[]
for key,offset in [('power_J10',(0,4,0)),('power_J10',(0,-4,0)),('motion_J7',(4,0,0))]:
 e,p,axis=endpoint(key,r);e+=offset;p+=offset;lim=None;ob=None
 for step in np.arange(0,25.01,.1):
  pt=p+axis*step
  if not rigid_free(pt,r+.3):
   lim=float(step);near=[]
   for n,t in trees.items():
    pos,no,face,dist=t.find_nearest(Vector(pt))
    if dist<r+.35:near.append(n)
   ob=near;break
 ray.append(dict(port=key,offset_mm=offset,wire_exit_face_mm=e.tolist(),allocation_center_start_mm=p.tolist(),free_axis_extension_from_start_mm=lim,first_blockers=ob))
out=dict(revision=P['revision'],source_blend_sha256=source_hash,status='BLOCKED',status_scope='Cable bend requirement unresolved; narrower-radius geometry is not approved cable data',best_finite_candidate=best,required_previous_radius_mm=6,straight_exit_capacity=ray,tried=tried,main_modified=False,limits=['No wire property was altered or labeled vendor-documented','A finite search is not a proof of best possible radius','Other harnesses and strain relief are not included in this capacity probe'])
(REVIEW/'terminal_bend_capacity.json').write_text(json.dumps(out,indent=2)+'\n');print('BEND_CAPACITY',None if best is None else best['minimum_curvature_radius_mm'],ray,flush=True)
