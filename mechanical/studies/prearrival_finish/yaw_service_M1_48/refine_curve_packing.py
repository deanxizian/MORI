"""Refine only ambiguous proximity cells from the full four-wire screening.

Unchanged wire OD, gaps and source chord errors. Uniform arc-length cells cover
the original polylines; finer points are interpolation, never route changes.
"""
from pathlib import Path
import hashlib,json,itertools,math,time
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=HERE/'internal_full_curves.npz';curves=np.load(source)
prior=json.loads((HERE/'curve_packing.json').read_text())
assert prior['source_curves_sha256']==sha(source)
started=time.time();pairs=[];selves=[]
error=.0003;numeric=.0001;OD=.6604;need=OD+.3

def at(p,s,t):return np.column_stack([np.interp(t,s,p[:,k]) for k in range(3)])
def tree_for(p,step):
    s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    t=np.linspace(0,s[-1],int(math.ceil(s[-1]/step))+1)
    q=at(p,s,t);kd=KDTree(len(q))
    for i,v in enumerate(q):kd.insert(Vector(v),i)
    kd.balance();return p,s,q,t,kd,float(np.diff(t).max())
def cell_points(p,s,t,index,step):
    lo=0. if index==0 else (t[index-1]+t[index])/2
    hi=s[-1] if index==len(t)-1 else (t[index]+t[index+1])/2
    fine=np.linspace(lo,hi,int(math.ceil((hi-lo)/step))+1)
    return at(p,s,fine),float(np.diff(fine).max())

for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
    cached={}
    for row in [r for r in prior['mutual_checks'] if r['yaw_deg']==yaw and r['pitch_deg']==pitch]:
        if row['status']=='PASS':pairs.append(row);continue
        a,b=row['a'],row['b']
        for pin in (a,b):
            if pin not in cached:cached[pin]=tree_for(curves[f'pin{pin}_y{yaw}_p{pitch}'],.02)
        p,s,q,t,_,sa=cached[a];_,_,_,_,tree,sb=cached[b]
        minimum=math.inf;refined=0
        for i,v in enumerate(q):
            d=float(tree.find(Vector(v))[2])
            lower=d-(sa+sb)/2-2*error-numeric-OD
            if lower<.3:
                points,step=cell_points(p,s,t,i,.004)
                lower=min(float(tree.find(Vector(vv))[2]) for vv in points)-(step+sb)/2-2*error-numeric-OD
                refined+=1
            minimum=min(minimum,lower)
        pairs.append(dict(a=a,b=b,yaw_deg=yaw,pitch_deg=pitch,status='PASS' if minimum>=.3 else 'BLOCKED',
                          surface_gap_lower_bound_mm=minimum,refined_cells=refined))
    for row in [r for r in prior['nonlocal_self_checks'] if r['yaw_deg']==yaw and r['pitch_deg']==pitch]:
        if row['status']=='PASS':selves.append(row);continue
        pin=row['pin'];p,s,q,t,tree,step=tree_for(curves[f'pin{pin}_y{yaw}_p{pitch}'],.3)
        ambiguous=set();bound=need+step+2*error+numeric
        for i,v in enumerate(q):
            for _,j,d in tree.find_range(Vector(v),bound):
                if j>i and t[j]-t[i]>2.3:ambiguous.add((i,j))
        minimum=math.inf;hits=[]
        for i,j in sorted(ambiguous):
            a,sa=cell_points(p,s,t,i,.004);b,sb=cell_points(p,s,t,j,.004)
            dist=np.linalg.norm(a[:,None,:]-b[None,:,:],axis=2)
            lower=float(dist.min())-(sa+sb)/2-2*error-numeric-OD
            minimum=min(minimum,lower)
            if lower<.3:hits.append(dict(cell_indices=[i,j],surface_gap_lower_bound_mm=lower))
        selves.append(dict(pin=pin,yaw_deg=yaw,pitch_deg=pitch,status='BLOCKED' if hits else 'PASS',hits=hits,
                           refined_cell_pairs=len(ambiguous),refined_region_min_gap_mm=minimum,
                           local_arc_exclusion_mm=2.3+step,
                           scope='Only nonlocal returns; smaller local spans require bend-radius evidence'))
    if pitch==25:print('REFINED_PACKING_YAW',yaw,'pair_blocks',sum(r['status']!='PASS' for r in pairs),
                      'self_blocks',sum(r['status']!='PASS' for r in selves),flush=True)
out=dict(status='PASS' if all(r['status']=='PASS' for r in pairs+selves) else 'BLOCKED',
         scope='Refined mutual and nonlocal self-return bounds for unchanged full curves at 130 poses',
         source_main_sha256=prior['source_main_sha256'],source_curves_sha256=sha(source),
         source_screen_sha256=sha(HERE/'curve_packing.json'),script_sha256=sha(__file__),
         mutual_checks=pairs,nonlocal_self_checks=selves,
         minimum_pair_gap_lower_bound_mm=min(r['surface_gap_lower_bound_mm'] for r in pairs),
         wire_OD_mm=OD,surface_gap_mm=.3,curve_error_bound_mm=error,
         independent_radius_proof='NOT_TESTED',whole_harness='BLOCKED',main_applied=False,
         elapsed_s=time.time()-started)
(HERE/'curve_packing_refined.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('REFINED_PACKING_DONE',out['status'],out['minimum_pair_gap_lower_bound_mm'],flush=True)
