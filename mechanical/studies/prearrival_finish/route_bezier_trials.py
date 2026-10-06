"""Candidate continuous body wires. No source geometry changes or cut lengths."""
from pathlib import Path
import hashlib,json,time,math,itertools
REVIEW=Path(__file__).resolve().parent
base=(REVIEW/'body_routes_current.py').read_text().split('prior=json.loads')[0]
exec(compile(base,str(REVIEW/'body_routes_current.py'),'exec'),globals())
old=json.loads((REVIEW/'body_routes_current.json').read_text())
active=[r for r in old['routes'] if r['id'] in ['H01','H02','H03']]
rigid_free=free
def point_dist(p,curve):
 a=curve[:-1];v=np.diff(curve,axis=0);w=p-a;den=(v*v).sum(axis=1);t=np.clip((w*v).sum(axis=1)/np.maximum(den,1e-12),0,1)
 return float(np.linalg.norm(w-t[:,None]*v,axis=1).min())
def all_free(p,clear):
 if not rigid_free(p,clear):return False
 return all(point_dist(p,np.array(r['curve_mm']))>=clear+r['bundle_diameter_allocation_mm']/2 for r in active)
def bezier(c,t):
 c=np.asarray(c);n=len(c)-1
 return sum(math.comb(n,i)*(1-t[:,None])**(n-i)*t[:,None]**i*c[i] for i in range(n+1))
def curve_radius(c):
 c=np.asarray(c);n=len(c)-1;t=np.linspace(0,1,241)
 d=bezier(np.diff(c,axis=0)*n,t);dd=bezier(np.diff(c,axis=0,n=2)*n*(n-1),t)
 return float(np.min(np.linalg.norm(d,axis=1)**3/np.maximum(np.linalg.norm(np.cross(d,dd),axis=1),1e-10)))
def candidates(hid,a,b,aa,ab):
 if hid.startswith('H05'):
  for h1,h2 in itertools.product([14,18,22,26,30,36],[14,18,22,26,30,36]):
   yield [a,a+aa*h1,b+ab*h2,b]
  for h1,h2,x,y,z in itertools.product([8,12,16,20,24],[8,12,16,20,24],[-12,-4,0,8,16,24,32,40],[-8,0,8,-16,-24,-36,-48],[136,138,142,146,150,156]):
   mid=np.array([x,y,z]);yield [a,a+aa*h1,mid,mid,b+ab*h2,b]
 else:
  for xx,y,za,zb,up,down in itertools.product([0,8,16,24,-8,-16],[-66,-68,-70],[130,134,138],[104,108,112],[10,16,24],[8,12,18]):
   yield [a,a+aa*up,[xx,y,za],[xx,y,zb],b+ab*down,b]
results=[]
for hid,r,R,shift in [('H05_splitA',1.4,6,-4),('H05_splitB',1.4,6,4),('H04_splitA',1.4,6,-4),('H04_splitB',1.4,6,4)]:
 pa,pb=('motion_J7','power_J10') if hid.startswith('H05') else ('motion_J4','imu_J1')
 ea,a,aa=endpoint(pa,r);eb,b,ab=endpoint(pb,r);ea+=np.array([shift,0,0]);a+=np.array([shift,0,0])
 delta=np.array([0,shift,0]) if hid.startswith('H05') else np.array([shift,0,0]);eb+=delta;b+=delta
 counts=dict(tried=0,curvature=0,collision=0);best=None;max_free=0;closest=None;start=time.time()
 for c in candidates(hid,a,b,aa,ab):
  counts['tried']+=1;mr=curve_radius(c)
  if mr<R:counts['curvature']+=1;continue
  curve=bezier(c,np.linspace(0,1,151));n=0
  for p in curve:
   if not all_free(p,r+.3):break
   n+=1
  if n>max_free:max_free=n;closest=dict(controls_mm=np.array(c).tolist(),passed_samples=n,total=151,first_blocked=curve[n].tolist() if n<151 else None)
  if n<151:counts['collision']+=1;continue
  hs=solid_hits(curve,r)
  if hs:counts['collision']+=1;continue
  best=dict(id=hid,status='PASS',from_port=pa,to_port=pb,curve_mm=curve.tolist(),controls_mm=np.array(c).tolist(),exit_faces_mm=[ea.tolist(),eb.tolist()],bundle_diameter_allocation_mm=2*r,minimum_analytic_curvature_radius_sampled_mm=mr,required_radius_mm=R,method='Polynomial Bezier, analytic derivatives sampled at241 parameters; rigid tubes and earlier accepted routes checked',length_mm=float(np.linalg.norm(np.diff(curve,axis=0),axis=1).sum()),data_status='ASSUMED wire envelope; native connector poses')
  active.append(best);break
 result=best or dict(id=hid,status='BLOCKED',closest_candidate=closest,reason='Finite candidate search did not satisfy same-solid and prior-wire clearance; not proof of impossibility')
 result['search']=dict(**counts,elapsed_s=time.time()-start);results.append(result)
 print('BEZIER_ROUTE',hid,result['status'],result['search'],flush=True)
 (REVIEW/'bezier_routes_progress.json').write_text(json.dumps(results,indent=2)+'\n')
(REVIEW/'bezier_routes.json').write_text(json.dumps(dict(revision=P['revision'],source_blend_sha256=source_hash,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,routes=active,attempts=results,status='BLOCKED',scope='Candidate body route allocations only; no anchoring, complete harness or manufacturing release'),indent=2)+'\n')
