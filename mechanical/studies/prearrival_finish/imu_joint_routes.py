"""Jointly allocate both IMU half-bundles through the existing rear corridor."""
from pathlib import Path
REVIEW=Path(__file__).resolve().parent
helper=(REVIEW/'route_bezier_trials.py').read_text().split('results=[]')[0]
exec(compile(helper,str(REVIEW/'route_bezier_trials.py'),'exec'),globals())
distance_code=(REVIEW/'body_routes_current.py').read_text().split('def segment_distance')[1].split('\ncrowding=[]')[0]
exec('def segment_distance'+distance_code,globals())

radius=1.4;required_radius=6.0;wire_margin=.3
pools={};search=[]
for name,shift,x_values in [('H04_splitA',-4,[-18,-20,-16,-14,-22]),('H04_splitB',4,[-14,-12,-16,-10,-18])]:
 ea,a,aa=endpoint('motion_J4',radius);eb,b,ab=endpoint('imu_J1',radius)
 delta=np.array([shift,0,0]);ea+=delta;a+=delta;eb+=delta;b+=delta
 pool=[];families=set();counts=dict(tried=0,curvature=0,collision=0);started=time.time()
 # Focus around the earlier viable rear-left corridor; unlike the prior
 # greedy search, neither IMU half is frozen while building the other pool.
 for x,y,z,up,h1,h2,down in itertools.product(x_values,[-65,-65.5,-66,-66.5],[114,110,118],[24,28,32],[28,20,24],[28,20,24],[12,16,20]):
  family=(x,y,z,up)
  if family in families:continue
  counts['tried']+=1;k=np.array([x,y,z]);t=np.array([0.,0.,-1.])
  c1=[a,a+aa*up,k-t*h1,k];c2=[k,k+t*h2,b+ab*down,b]
  mr=min(curve_radius(c1),curve_radius(c2))
  if mr<required_radius:counts['curvature']+=1;continue
  curve=np.vstack([bezier(c1,np.linspace(0,1,121)),bezier(c2,np.linspace(0,1,121))[1:]])
  if not all(all_free(p,radius+.3) for p in resample(curve,.6)):
   counts['collision']+=1;continue
  hits=solid_hits(curve,radius)
  if hits:counts['collision']+=1;continue
  pool.append(dict(id=name,curve_mm=curve.tolist(),controls_mm=[np.array(c1).tolist(),np.array(c2).tolist()],
      bundle_diameter_allocation_mm=2*radius,minimum_curvature_radius_sampled_mm=mr,required_radius_mm=required_radius,
      exit_faces_mm=[ea.tolist(),eb.tolist()],rigid_hits=hits))
  families.add(family)
  if len(pool)>=80:break
 pools[name]=pool;search.append(dict(id=name,**counts,accepted=len(pool),elapsed_s=time.time()-started))
 print('IMU_POOL',search[-1],flush=True)

pair_trials=[];selected=None
for ia,a in enumerate(pools['H04_splitA']):
 for ib,b in enumerate(pools['H04_splitB']):
  ap=np.array(a['curve_mm']);bp=np.array(b['curve_mm']);failed=None;minimum=2*radius+wire_margin
  for p,q in zip(ap,ap[1:]):
   if failed:break
   for r,s in zip(bp,bp[1:]):
    if np.any(np.maximum(p,q)+minimum<np.minimum(r,s)) or np.any(np.maximum(r,s)+minimum<np.minimum(p,q)):continue
    d=segment_distance(p,q,r,s)
    if d<2*radius+wire_margin:
     failed=dict(distance_mm=d,a_segment=[p.tolist(),q.tolist()],b_segment=[r.tolist(),s.tolist()]);break
  pair_trials.append(dict(a=ia,b=ib,collision=failed))
  if failed is None:selected=[a,b];break
 if selected:break
out=dict(status='PASS' if selected else 'BLOCKED',scope='Two IMU half-bundles plus previous H01/H02/H03 only, not complete harness',
 revision=P['revision'],source_blend_sha256=source_hash,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,
 search=search,pair_trials=pair_trials,selected=selected,pools=pools,
 centreline_spacing_requirement_mm=2*radius+wire_margin,
 assumed_wire_diameter_mm=2*radius,required_bend_radius_mm=required_radius,
 main_applied=False,cut_lengths_released=False,
 limits=['Cable size, splitting and bend radius are explicit allocations, not selected vendor wire data',
         'H05 branches, terminals/fanout, clips and moving head cables are not included',
         'Curvature uses analytic derivatives at finite samples; tube clearance uses dense polyline/solid checks'])
(REVIEW/'imu_joint_routes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('IMU_JOINT_FINAL',out['status'],len(pair_trials),flush=True)
