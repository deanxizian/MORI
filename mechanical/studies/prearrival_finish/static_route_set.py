"""Choose compatible route candidates jointly; no model/port/PCB edits."""
from pathlib import Path
import random
REVIEW=Path(__file__).resolve().parent
helper=(REVIEW/'route_bezier_trials.py').read_text().split('results=[]')[0]
exec(compile(helper,str(REVIEW/'route_bezier_trials.py'),'exec'),globals())
specs=[('H01','power_J17','motion_J1',1.6,6,0),('H02','motion_J2','power_J13',1.35,6,0),('H03','motion_J3','power_J14',1.35,6,0),('H05_splitA','motion_J7','power_J10',1.4,6,-4),('H05_splitB','motion_J7','power_J10',1.4,6,4)]
pools={};stats={};rng=random.Random(461)
for hid,pa,pb,r,R,shift in specs:
 ea,a,aa=endpoint(pa,r);eb,b,ab=endpoint(pb,r)
 if shift:ea+=np.array([shift,0,0]);a+=np.array([shift,0,0]);eb+=np.array([0,shift,0]);b+=np.array([0,shift,0])
 controls=[]
 if hid.startswith('H05'):controls=list(candidates(hid,a,b,aa,ab))
 else:
  xs=[-24,-12,0,12,24,36] if hid=='H01' else [8,16,24,32,40,48]
  for h1,h2,x,y,z in itertools.product([8,12,16,20,28],[8,12,16,20,28],xs,[-48,-36,-24,-12,0,12],[134,142,150,158]):
   mid=np.array([x,y,z]);controls.append([a,a+aa*h1,mid,mid,b+ab*h2,b])
 rng.shuffle(controls);pool=[];seen=set();count=0;start=time.time()
 for c in controls:
  count+=1;mr=curve_radius(c)
  if mr<R:continue
  curve=bezier(c,np.linspace(0,1,121));pts=resample(curve,.5)
  if not all(rigid_free(p,r+.3) for p in pts):continue
  key=tuple(np.rint(curve[[30,60,90]].ravel()/1.5).astype(int))
  if key in seen:continue
  seen.add(key);pool.append(dict(id=hid,curve_mm=curve.tolist(),controls_mm=np.array(c).tolist(),bundle_diameter_allocation_mm=r*2,minimum_analytic_curvature_radius_sampled_mm=mr,required_radius_mm=R,exit_faces_mm=[ea.tolist(),eb.tolist()],from_port=pa,to_port=pb,length_mm=float(np.linalg.norm(np.diff(curve,axis=0),axis=1).sum())))
  if len(pool)>=100:break
 pools[hid]=sorted(pool,key=lambda x:x['length_mm']);stats[hid]=dict(candidates=len(pool),tried=count,elapsed_s=time.time()-start)
 print('ROUTE_POOL',hid,stats[hid],flush=True)
 (REVIEW/'static_route_pool_progress.json').write_text(json.dumps(stats,indent=2)+'\n')
curves={(k,i):resample(r['curve_mm'],.5) for k,ps in pools.items() for i,r in enumerate(ps)}
cache={}
def compatible(ka,ia,kb,ib):
 key=(ka,ia,kb,ib)
 if key not in cache:
  a=curves[ka,ia];b=curves[kb,ib];required=(pools[ka][ia]['bundle_diameter_allocation_mm']+pools[kb][ib]['bundle_diameter_allocation_mm'])/2+.55
  # Every sampled polyline point is <=0.25mm from a segment point; the
  #0.55mm extra protects the subsequent exact segment check's0.3mm margin.
  dist=float(np.min(np.linalg.norm(a[:,None,:]-b[None,:,:],axis=2)))
  cache[key]=dist>=required
 return cache[key]
order=sorted(pools,key=lambda k:len(pools[k]));attempts=0
def search(selected):
 global attempts
 if len(selected)==len(order):return selected
 k=order[len(selected)]
 for i in range(len(pools[k])):
  attempts+=1
  if attempts>500000:return None
  if all(compatible(k,i,kb,ib) for kb,ib in selected):
   found=search(selected+[(k,i)])
   if found:return found
 return None
selected=search([]);routes=[]
if selected:
 for k,i in selected:
  row=pools[k][i];hs=solid_hits(row['curve_mm'],row['bundle_diameter_allocation_mm']/2)
  row.update(status='PASS' if not hs else 'FAIL',solid_hits=hs,data_status='ASSUMED cable envelope; native port datums',method='Joint finite candidate selection; analytical Bezier derivatives sampled241 points')
  routes.append(row)
out=dict(revision=P['revision'],source_blend_sha256=source_hash,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,status='PASS' if len(routes)==5 and all(r['status']=='PASS' for r in routes) else 'BLOCKED',status_scope='Five static body route envelopes only; not complete harness',routes=routes,search=stats,combinations_visited=attempts,pair_candidates_checked=len(cache),new_structure=False,cut_lengths_released=False,limits=['Terminal fanout and fixation are still required','Cable properties and crimped exits are not manufacturer-qualified','Does not include IMU, rear branches, actuator cables, or moving-head loops'])
(REVIEW/'static_route_set.json').write_text(json.dumps(out,indent=2)+'\n');print('STATIC_SET',out['status'],len(routes),attempts,flush=True)
