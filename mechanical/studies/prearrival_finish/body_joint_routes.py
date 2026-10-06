"""Joint routing candidate with wire-to-wire obstacle screening from the outset."""
from pathlib import Path
REVIEW=Path(__file__).resolve().parent
helper=(REVIEW/'route_bezier_trials.py').read_text().split('results=[]')[0]
exec(compile(helper,str(REVIEW/'route_bezier_trials.py'),'exec'),globals())
active=[r for r in old['routes'] if r['id'] in ['H02','H03']]
attempts=[]
def controls(hid,a,b,aa,ab):
 if hid.startswith('H05'):
  yield from candidates(hid,a,b,aa,ab)
 else:
  for h1,h2,x,y,z in itertools.product([12,20,28,36],[12,20,28,36],[-24,-12,0,12,24],[-44,-36,-24,-16,-8,0,8],[138,146,154,162]):
   mid=np.array([x,y,z]);yield [a,a+aa*h1,mid,mid,b+ab*h2,b]
for hid,pa,pb,r,R,shift in [('H05_splitB','motion_J7','power_J10',1.4,6,4),('H05_splitA','motion_J7','power_J10',1.4,6,-4),('H01','power_J17','motion_J1',1.6,6,0)]:
 ea,a,aa=endpoint(pa,r);eb,b,ab=endpoint(pb,r)
 if shift:ea+=np.array([shift,0,0]);a+=np.array([shift,0,0]);eb+=np.array([0,shift,0]);b+=np.array([0,shift,0])
 counts=dict(tried=0,curvature=0,collision=0);best=None;max_free=0;closest=None;start=time.time()
 for c in controls(hid,a,b,aa,ab):
  counts['tried']+=1;mr=curve_radius(c)
  if mr<R:counts['curvature']+=1;continue
  curve=bezier(c,np.linspace(0,1,241));pts=resample(curve,.5);nf=0
  for p in pts:
   if not all_free(p,r+.3):break
   nf+=1
  fraction=nf/len(pts)
  if fraction>max_free:max_free=fraction;closest=dict(controls_mm=np.array(c).tolist(),passed_fraction=fraction,first_blocked=pts[nf].tolist() if nf<len(pts) else None)
  if nf<len(pts):counts['collision']+=1;continue
  hs=solid_hits(curve,r)
  if hs:counts['collision']+=1;continue
  best=dict(id=hid,status='PASS',from_port=pa,to_port=pb,curve_mm=curve.tolist(),controls_mm=np.array(c).tolist(),exit_faces_mm=[ea.tolist(),eb.tolist()],bundle_diameter_allocation_mm=2*r,minimum_analytic_curvature_radius_sampled_mm=mr,required_radius_mm=R,length_mm=float(np.linalg.norm(np.diff(curve,axis=0),axis=1).sum()),data_status='ASSUMED cable envelope',method='Joint planning on current solids and already accepted static routes')
  active.append(best);break
 result=best or dict(id=hid,status='BLOCKED',closest_candidate=closest)
 result['search']=dict(**counts,elapsed_s=time.time()-start);attempts.append(result)
 print('JOINT_ROUTE',hid,result['status'],result['search'],flush=True)
 (REVIEW/'joint_routes_progress.json').write_text(json.dumps(attempts,indent=2)+'\n')
(REVIEW/'body_joint_routes.json').write_text(json.dumps(dict(revision=P['revision'],source_blend_sha256=source_hash,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,routes=active,attempts=attempts,status='BLOCKED',scope='Static cable allocation only; not anchored and no released cut lengths'),indent=2)+'\n')
