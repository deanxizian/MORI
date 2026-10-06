"""Regenerate the11local curves with one signal moved45->43.5deg.

The1.5degree refinement clears the complete8mm bridge web in the actual print
candidate. It is a route change, not moving or scaling any purchased hardware.
All pair bounds are recomputed for the actual angle differences.
"""
from pathlib import Path
import sys,json,hashlib,math,itertools,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'));sys.path.insert(0,str(HERE))
from native_context import np,sha
from mathutils.kdtree import KDTree
from mathutils import Vector
from tapered_family import rotate
start=time.time();old=json.loads((HERE/'packing.json').read_text());screen=json.loads((HERE/'wall_clearance_capacity.json').read_text())
chosen=next(r for r in screen['rows'] if r['reserve_mm']==3.)['solution']
assert chosen and len(chosen)==11
for r in chosen:
    if r['kind']=='signal' and r['angle_deg']==45:r['angle_deg']=43.5
source=np.load(HERE/'curves.npz');curves={y:source[old['family']['id']+'_y'+str(y)] for y in range(-60,61,10)}
trees={}
for y,p in curves.items():
    tree=KDTree(len(p))
    for i,v in enumerate(p):tree.insert(Vector(v),i)
    tree.balance();trees[y]=tree
deltas=set()
for a,b in itertools.combinations(chosen,2):
    d=abs(a['angle_deg']-b['angle_deg']);deltas.add(min(d,360-d))
rows=[];lookup={}
for d in sorted(deltas):
    best=math.inf;witness=None
    for yaw,p in curves.items():
        q=rotate(p,d);dist=min(float(trees[yaw].find(Vector(v))[2]) for v in q)
        lower=dist-float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())-2*old['family']['chord_error_mm']-1e-4
        if lower<best:best=lower;witness=yaw
    lookup[d]=best;rows.append(dict(delta_deg=d,centerline_lower_bound_mm=best,yaw_deg=witness))
out={}
for i,r in enumerate(chosen):
    r['allocation_id']=i
    for yaw,p in curves.items():out[f'wire{i}_y{yaw}']=rotate(p,r['angle_deg'])
pairs=[]
for a,b in itertools.combinations(chosen,2):
    d=abs(a['angle_deg']-b['angle_deg']);g=lookup[min(d,360-d)]-(a['OD_mm']+b['OD_mm'])/2;assert g>=.3
    pairs.append(dict(a=a['allocation_id'],b=b['allocation_id'],surface_gap_lower_bound_mm=g))
np.savez_compressed(HERE/'C4_packed_curves.npz',**out)
r=dict(old);r.update(scope='RefinedC4 local curves; actual complete print clearance checked bybuild_candidate_v4.py',
    selected=chosen,selected_pairs=pairs,pair_bounds=rows,minimum_pair_gap_lower_bound_mm=min(x['surface_gap_lower_bound_mm'] for x in pairs),
    output_curves_sha256=sha(HERE/'C4_packed_curves.npz'),source_wall_screen_sha256=sha(HERE/'wall_clearance_capacity.json'),
    reserve_screen_mm=3.,refinement='Signal allocation7 rotates45to43.5deg; requires fresh actual-part checks',
    script_sha256=sha(__file__),elapsed_s=time.time()-start)
(HERE/'C4_packing.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('C4_REPACKED',r['minimum_pair_gap_lower_bound_mm'],time.time()-start,flush=True)
