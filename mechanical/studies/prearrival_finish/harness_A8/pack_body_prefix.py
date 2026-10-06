"""Choose four body wires together, retaining pin numbers and gaps.

Point-distance coverage bounds include both discretizations and both analytic
arc sagittas. Local self-neighbours below2mm arclength are covered by the
documented >=7mm path curvature; nonlocal returns are checked explicitly.
"""
from pathlib import Path
import sys,json,math,hashlib,itertools,time
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;OUT=HERE/'body_prefix_v2';ROOT=HERE.parents[3]
source=OUT/'dubins_pools.json';d=json.loads(source.read_text());start=time.time()
STEP=.04;NEED=d['wire_OD_mm']+.3

def samples(curve):
    v=np.asarray(curve);ds=np.linalg.norm(np.diff(v,axis=0),axis=1)
    parts=[]
    for a,b,L in zip(v,v[1:],ds):
        n=max(1,math.ceil(L/STEP));parts.append(np.linspace(a,b,n+1)[:-1])
    p=np.vstack(parts+[v[-1:]]);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    tree=KDTree(len(p))
    for i,pt in enumerate(p):tree.insert(Vector(pt),i)
    tree.balance();return p,s,tree,float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())

candidates={};self_rows=[]
for key,pool in d['pools'].items():
    for i,r in enumerate(pool):
        cid=key+'_'+str(i);p,s,t,step=samples(r['curve_mm']);err=r['error_bound_mm']
        required=NEED+step+2*err+1e-5
        hit=None
        for j,pt in enumerate(p):
            near=t.find_range(Vector(pt),required)
            bad=[(index,dist) for _,index,dist in near if abs(s[index]-s[j])>2.]
            if bad:
                k,dist=min(bad,key=lambda x:x[1]);hit={'indices':[j,k],'distance_mm':float(dist),'arclength_separation_mm':float(abs(s[k]-s[j]))};break
        self_rows.append({'id':cid,'status':'BLOCKED' if hit else 'PASS','nonlocal_hit':hit,
                          'excluded_local_arclength_mm':2.,'analytic_minimum_radius_mm':r['minimum_curvature_radius_mm']})
        if not hit:candidates[cid]={'record':r,'points':p,'arclength':s,'tree':t,'max_step':step}
    print('PACK_SELF',key,sum(cid.startswith(key+'_') for cid in candidates),flush=True)

pair_cache={}
def compatible(a,b):
    key=tuple(sorted([a,b]))
    if key in pair_cache:return pair_cache[key]['status']=='PASS'
    A=candidates[a];B=candidates[b]
    if len(A['points'])>len(B['points']):A,B=B,A
    allowance=(A['max_step']+B['max_step'])/2+A['record']['error_bound_mm']+B['record']['error_bound_mm']+1e-5
    minimum=math.inf;where=None
    for i,p in enumerate(A['points']):
        _,j,distance=B['tree'].find(Vector(p))
        if distance<minimum:minimum=float(distance);where=[p.tolist(),B['points'][j].tolist()]
        if minimum<NEED:break
    gap=minimum-allowance-d['wire_OD_mm']
    status='PASS' if gap>=.3 else 'BLOCKED'
    pair_cache[key]={'a':key[0],'b':key[1],'status':status,
        'surface_gap_lower_bound_mm':gap,'distance_sample_mm':minimum,'point_pair_mm':where,
        'scope':'Global minimum covered if PASS; early exit identifies one blocking point pair if BLOCKED'}
    return status=='PASS'

by_pin={pin:sorted([k for k,v in candidates.items() if v['record']['pin']==pin],key=lambda k:candidates[k]['record']['analytic_prefix_length_mm']) for pin in range(1,5)}
order=sorted(by_pin,key=lambda p:len(by_pin[p]));best=None;best_length=math.inf;search_counts={'nodes':0,'complete':0,'pruned':0}
def search(chosen,used,length):
    global best,best_length
    search_counts['nodes']+=1
    if length>=best_length:search_counts['pruned']+=1;return
    if len(chosen)==4:
        best=chosen[:];best_length=length;search_counts['complete']+=1
        print('PACK_FOUND',best,best_length,flush=True);return
    pin=order[len(chosen)]
    for cid in by_pin[pin]:
        r=candidates[cid]['record'];phase=r['azimuth_deg']
        if phase in used:continue
        if all(compatible(cid,past) for past in chosen):search(chosen+[cid],used|{phase},length+r['analytic_prefix_length_mm'])
search([],set(),0.)
selected=[] if best is None else [{'candidate_id':cid,**candidates[cid]['record']} for cid in sorted(best,key=lambda c:candidates[c]['record']['pin'])]
selected_pairs=[] if best is None else [pair_cache[tuple(sorted([a,b]))] for a,b in itertools.combinations(best,2)]
result={'status':'PASS' if best else 'BLOCKED','scope':'Four simultaneous body prefixes at mechanical zero; no complete head connection, fixing or assembly qualification',
    'source_blend_sha256':d['source_blend_sha256'],'source_pool_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'source_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'wire_OD_mm':d['wire_OD_mm'],'required_surface_gap_mm':.3,'resampling_max_chord_mm':STEP,
    'self_checks':self_rows,'pair_checks':list(pair_cache.values()),'search':search_counts,
    'selected':selected,'selected_pairs':selected_pairs,'total_prefix_length_mm':best_length if best else None,
    'elapsed_s':time.time()-start,'main_model_applied':False,'whole_harness':'BLOCKED',
    'dynamic_source_check':'NOT_TESTED','assembly_path':'NOT_TESTED','physical_retention':'NOT_TESTED',
    'cut_lengths_released':False,'limits':['Input J2 print candidate not approved; AMASS depth tolerance is conditional.',
      'Lengths end at neck staging datums; no supplier cut length or CAM reach implied.',
      'Packing checks preserve input pin order; phase assignment is an internal routing decision.']}
(OUT/'packing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('H06_BODY_PACKING',result['status'],search_counts,len(pair_cache),'seconds',round(time.time()-start,2),flush=True)
