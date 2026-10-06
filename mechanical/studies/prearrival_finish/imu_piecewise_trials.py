"""Two tangent-continuous cubic elbows through an existing rear-edge corridor."""
from pathlib import Path
REVIEW=Path(__file__).resolve().parent
helper=(REVIEW/'route_bezier_trials.py').read_text().split('results=[]')[0]
exec(compile(helper,str(REVIEW/'route_bezier_trials.py'),'exec'),globals())
results=[]
for hid,r,R,shift in [('H04',2.5,8,0),('H04_splitA',1.4,6,-4),('H04_splitB',1.4,6,4)]:
 if hid!='H04' and any(x['id']=='H04' and x['status']=='PASS' for x in results):break
 ea,a,aa=endpoint('motion_J4',r);eb,b,ab=endpoint('imu_J1',r)
 delta=np.array([shift,0,0]);ea+=delta;a+=delta;eb+=delta;b+=delta
 counts=dict(tried=0,curvature=0,collision=0);best=None;max_free=0;closest=None;start=time.time()
 for x,y,z,up,h1,h2,down,tan in itertools.product([12,16,8,0,-8,-14,24,30],[-66,-67,-68,-69],[110,114,118,122,126],[16,24,32,40],[12,20,28],[12,20,28],[12,20,28],[(0,0,-1),(-.5,.4,-1),(-.3,.2,-1)]):
  counts['tried']+=1;k=np.array([x,y,z]);t=np.array(tan,dtype=float);t/=np.linalg.norm(t)
  c1=[a,a+aa*up,k-t*h1,k];c2=[k,k+t*h2,b+ab*down,b]
  mr=min(curve_radius(c1),curve_radius(c2))
  if mr<R:counts['curvature']+=1;continue
  curve=np.vstack([bezier(c1,np.linspace(0,1,121)),bezier(c2,np.linspace(0,1,121))[1:]])
  pts=resample(curve,.6);nf=0
  for p in pts:
   if not all_free(p,r+.3):break
   nf+=1
  fraction=nf/len(pts)
  if fraction>max_free:max_free=fraction;closest=dict(controls_mm=[np.array(c1).tolist(),np.array(c2).tolist()],passed_fraction=fraction,first_blocked=pts[nf].tolist() if nf<len(pts) else None)
  if nf<len(pts):counts['collision']+=1;continue
  hs=solid_hits(curve,r)
  if hs:counts['collision']+=1;continue
  best=dict(id=hid,status='PASS',curve_mm=curve.tolist(),controls_mm=[np.array(c1).tolist(),np.array(c2).tolist()],bundle_diameter_allocation_mm=2*r,minimum_curvature_radius_sampled_mm=mr,required_radius_mm=R,exit_faces_mm=[ea.tolist(),eb.tolist()],length_mm=float(np.linalg.norm(np.diff(curve,axis=0),axis=1).sum()),method='Tangent-continuous two-cubic candidate; no structural changes',data_status='ASSUMED cable envelope')
  active.append(best);break
 result=best or dict(id=hid,status='BLOCKED',closest_candidate=closest)
 result['search']=dict(**counts,elapsed_s=time.time()-start);results.append(result)
 print('PIECEWISE',hid,result['status'],result['search'],flush=True)
 (REVIEW/'imu_piecewise_progress.json').write_text(json.dumps(results,indent=2)+'\n')
(REVIEW/'imu_piecewise_routes.json').write_text(json.dumps(dict(revision=P['revision'],source_blend_sha256=source_hash,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,attempts=results,status='BLOCKED',cut_lengths_released=False),indent=2)+'\n')
