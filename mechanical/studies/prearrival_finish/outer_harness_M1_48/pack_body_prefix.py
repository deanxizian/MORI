"""Select four compatible body-to-neck paths with original J5 pin numbers."""
from pathlib import Path
import sys,json,math,itertools,time,hashlib
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=HERE/'body_prefix_pools.json';d=json.loads(source.read_text())
assert sha(PROJECT/'mechanical/mori_v1_2.blend')==d['source_main_sha256']
cache_path=HERE/'body_prefix_curves.npz';cache=np.load(cache_path)
STEP=.06;OD=d['wire_OD_mm'];GAP=d['surface_gap_mm'];NEED=OD+GAP
started=time.time()

def resample(v):
    out=[]
    for a,b in zip(v,v[1:]):
        length=float(np.linalg.norm(b-a))
        if length<1e-10:continue
        out.append(np.linspace(a,b,max(1,math.ceil(length/STEP))+1)[:-1])
    p=np.vstack(out+[v[-1:]]);ds=np.linalg.norm(np.diff(p,axis=0),axis=1);s=np.r_[0.,np.cumsum(ds)]
    t=KDTree(len(p))
    for i,x in enumerate(p):t.insert(Vector(x),i)
    t.balance();return p,s,t,float(max(ds))

available={};self_rows=[]
for key,pool in d['pools'].items():
    for r in pool:
        cid=r['curve_key'];p,s,tree,step=resample(cache[cid]);error=r['error_bound_mm']
        assert r['minimum_curvature_radius_mm']>=d['required_radius_mm']
        required=NEED+step+2*error+1e-5;hit=None
        for i,x in enumerate(p):
            candidates=[(j,dist) for _,j,dist in tree.find_range(Vector(x),required) if abs(s[j]-s[i])>2.]
            if candidates:
                j,dist=min(candidates,key=lambda q:q[1]);hit=dict(indices=[i,j],sampled_distance_mm=float(dist),arclength_separation_mm=float(abs(s[i]-s[j])));break
        self_rows.append(dict(id=cid,status='BLOCKED' if hit else 'PASS',nonlocal_hit=hit,
                              adjacent_arc_length_exclusion_mm=2.,analytic_minimum_radius_mm=r['minimum_curvature_radius_mm']))
        if hit is None:available[cid]=dict(record=r,points=p,tree=tree,step=step)
    print('OUTER_SELF',key,'kept',sum(x.startswith(key+'_') for x in available),flush=True)

pair_cache={}
def compatible(a,b):
    key=tuple(sorted([a,b]))
    if key in pair_cache:return pair_cache[key]['status']=='PASS'
    A,B=available[a],available[b]
    if len(A['points'])>len(B['points']):A,B=B,A
    allowance=(A['step']+B['step'])/2+A['record']['error_bound_mm']+B['record']['error_bound_mm']+1e-5
    minimum=math.inf;witness=None
    for x in A['points']:
        _,j,dist=B['tree'].find(Vector(x))
        if dist<minimum:minimum=float(dist);witness=[x.tolist(),B['points'][j].tolist()]
        if minimum<NEED:break
    gap=minimum-allowance-OD
    pair_cache[key]=dict(a=a,b=b,status='PASS' if gap>=GAP else 'BLOCKED',
        surface_gap_lower_bound_mm=gap,sampled_distance_mm=minimum,point_pair_mm=witness,
        scope='PASS bounds every pair of continuous curves; BLOCKED is one conservative clearance witness.')
    return gap>=GAP

by_pin={pin:sorted([cid for cid,c in available.items() if c['record']['pin']==pin],
                  key=lambda cid:available[cid]['record']['analytic_body_neck_length_mm']) for pin in range(1,5)}
order=sorted(by_pin,key=lambda n:len(by_pin[n]));counts=dict(nodes=0,complete=0,limit=150000);best=None
def search(chosen,phases):
    global best
    counts['nodes']+=1
    if counts['nodes']>counts['limit']:return False
    if len(chosen)==4:best=chosen[:];counts['complete']+=1;return True
    pin=order[len(chosen)]
    for cid in by_pin[pin]:
        phase=available[cid]['record']['azimuth_deg']
        if phase in phases:continue
        if all(compatible(cid,prev) for prev in chosen) and search(chosen+[cid],phases|{phase}):return True
    return False
search([],set())
selected=[] if best is None else [dict(candidate_id=cid,**available[cid]['record']) for cid in sorted(best,key=lambda cid:available[cid]['record']['pin'])]
selected_pairs=[] if best is None else [pair_cache[tuple(sorted([a,b]))] for a,b in itertools.combinations(best,2)]
if best:
    np.savez_compressed(HERE/'packed_curves.npz',**{f'pin{r["pin"]}':cache[r['candidate_id']] for r in selected})
result=dict(status='PASS' if best else 'BLOCKED',scope='Four complete body-root to neck-staging curves, not the full head harness',
    source_main_sha256=d['source_main_sha256'],source_pools_sha256=sha(source),source_curves_sha256=sha(cache_path),
    script_sha256=sha(__file__),wire_OD_mm=OD,surface_gap_requirement_mm=GAP,point_spacing_max_mm=STEP,
    native_input_evidence=d['sources'],self_checks=self_rows,pair_checks=list(pair_cache.values()),search=counts,
    selected=selected,selected_pairs=selected_pairs,source_candidates=len(available),
    total_body_neck_length_mm=sum(r['analytic_body_neck_length_mm'] for r in selected) if selected else None,
    head_motion='NOT_TESTED',assembly='NOT_TESTED',upper_service_loop='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',supplier_cut_lengths_released=False,elapsed_s=time.time()-started,
    limitations=['The first compatible set is selected; no global shortest-length claim.',
                'PCB pin identity is preserved. Phase assignment only chooses internal routing.',
                'No clip, tie, terminal insertion or hand/tool access is implied by installed curves.'])
(HERE/'packing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('OUTER_PACKING_DONE',result['status'],counts,'pairs',len(pair_cache),'seconds',round(time.time()-started,1),flush=True)
