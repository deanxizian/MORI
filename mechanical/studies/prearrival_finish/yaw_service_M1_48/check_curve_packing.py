"""Full four-wire mutual checks, and bounded nonlocal self-return screening.

No part model is changed. Self checks exclude short local arc neighbours and
are reported separately from the bend-radius evidence, never as wire life.
"""
from pathlib import Path
import hashlib,json,itertools,time,math
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
main=PROJECT/'mechanical/mori_v1_2.blend';main_hash=sha(main)
source=HERE/'internal_full_curves.npz';curves=np.load(source)
report=json.loads((HERE/'internal_candidate.json').read_text())
assert report['source_main_sha256']==main_hash
started=time.time();pairs=[];selves=[]
error=.0003;need=.6604+.3;numeric=.0001

def sample(p,step):
    s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    t=np.linspace(0.,s[-1],int(math.ceil(s[-1]/step))+1)
    q=np.column_stack([np.interp(t,s,p[:,k]) for k in range(3)])
    kd=KDTree(len(q))
    for i,v in enumerate(q):kd.insert(Vector(v),i)
    kd.balance()
    return q,t,kd,float(np.diff(t).max())

for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
    fine={}
    for pin in range(1,5):
        p=curves[f'pin{pin}_y{yaw}_p{pitch}']
        fine[pin]=sample(p,.02)
        q,t,tree,step=sample(p,.3)
        bound=need+step+2*error+numeric
        hit=None
        for i,v in enumerate(q):
            remote=[(j,d) for _,j,d in tree.find_range(Vector(v),bound)
                    if abs(t[j]-t[i])>2.3]
            if remote:
                j,d=min(remote,key=lambda x:x[1]);hit=dict(sample_indices=[i,j],distance_mm=float(d),
                                                         arc_separation_mm=float(abs(t[j]-t[i])))
                break
        selves.append(dict(pin=pin,yaw_deg=yaw,pitch_deg=pitch,status='BLOCKED' if hit else 'PASS',hit=hit,
                           local_arc_exclusion_mm=2.3+step,
                           scope='Only nonlocal returns; smaller local spans require bend-radius evidence'))
    for a,b in itertools.combinations(range(1,5),2):
        pa,_,_,sa=fine[a];pb,_,tree,sb=fine[b]
        minimum=math.inf
        for v in pa:
            _,j,d=tree.find(Vector(v))
            minimum=min(minimum,float(d))
        gap=minimum-(sa+sb)/2-2*error-numeric-.6604
        pairs.append(dict(a=a,b=b,yaw_deg=yaw,pitch_deg=pitch,
                          status='PASS' if gap>=.3 else 'BLOCKED',surface_gap_lower_bound_mm=gap))
    if pitch==25:print('PACKING_YAW',yaw,'pair_blocks',sum(r['status']!='PASS' for r in pairs),
                      'self_blocks',sum(r['status']!='PASS' for r in selves),flush=True)
assert sha(main)==main_hash
out=dict(status='PASS' if all(r['status']=='PASS' for r in pairs+selves) else 'BLOCKED',
         scope='Four complete route polylines at 130 poses: mutual gaps and nonlocal self returns',
         source_main_sha256=main_hash,source_curves_sha256=sha(source),script_sha256=sha(__file__),
         head_poses=130,wire_instances=520,mutual_checks=pairs,nonlocal_self_checks=selves,
         minimum_pair_gap_lower_bound_mm=min(r['surface_gap_lower_bound_mm'] for r in pairs),
         wire_OD_mm=.6604,surface_gap_mm=.3,curve_error_bound_mm=error,
         required_local_radius_mm=6.9342,independent_radius_proof='NOT_TESTED',
         full_material_installed_motion='NOT_TESTED',whole_harness='BLOCKED',main_applied=False,
         supplier_cut_lengths_released=False,elapsed_s=time.time()-started)
(HERE/'curve_packing.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PACKING_DONE',out['status'],out['minimum_pair_gap_lower_bound_mm'],flush=True)
