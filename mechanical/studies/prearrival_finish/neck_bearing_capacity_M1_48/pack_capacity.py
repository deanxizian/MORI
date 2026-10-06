"""Simultaneous 11-conductor packing within one explicitly screened family."""
from pathlib import Path
import sys,json,math,itertools,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'));sys.path.insert(0,str(HERE))
from native_context import np,sha
from mathutils.kdtree import KDTree
from mathutils import Vector
from tapered_family import rotate
started=time.time();screen=json.loads((HERE/'screen.json').read_text())
assert sha(HERE/'curves.npz')==screen['curves_sha256']
cache=np.load(HERE/'curves.npz');fid='Z130_R10.6_F173'
ref=next(r for r in screen['references'] if r['id']==fid);error=ref['chord_error_mm']
curves={y:cache[f'{fid}_y{y}'] for y in range(-60,61,10)}
trees={}
for yaw,p in curves.items():
    tree=KDTree(len(p))
    for i,v in enumerate(p):tree.insert(Vector(v),i)
    tree.balance();trees[yaw]=tree
pairs=[]
for delta in range(5,181,5):
    best=math.inf;witness=None
    for yaw,p in curves.items():
        other=rotate(p,delta)
        d=min(float(trees[yaw].find(Vector(v))[2]) for v in other)
        lower=d-float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())-2*error-1e-4
        if lower<best:best=lower;witness=yaw
    pairs.append(dict(delta_deg=delta,centerline_lower_bound_mm=best,yaw_deg=witness))
lookup={r['delta_deg']:r['centerline_lower_bound_mm'] for r in pairs};lookup[0]=0.
def gap(a,b):
    d=abs(a['angle_deg']-b['angle_deg']);d=min(d,360-d)
    return lookup[d]-(a['OD_mm']+b['OD_mm'])/2
nodes=[{k:r[k] for k in ['kind','OD_mm','angle_deg']} for r in screen['rows'] if r['family']==fid and r['status']=='PASS']
power=[r for r in nodes if r['kind']=='power_sample'];signal=[r for r in nodes if r['kind']=='signal']
calls=0;limit=2000000;solution=None
def sig(options,chosen,need):
    global calls
    calls+=1
    if calls>limit or len(options)<need:return None
    if not need:return chosen
    for i,a in enumerate(options):
        result=sig([b for b in options[i+1:] if gap(a,b)>=.3],chosen+[a],need-1)
        if result is not None:return result
    return None
def powerpick(options,signals,chosen,need):
    global calls,solution
    calls+=1
    if calls>limit or len(options)<need or len(signals)<4:return False
    if not need:
        result=sig(signals,[],4)
        if result is not None:solution=chosen+result;return True
        return False
    for i,a in enumerate(options):
        if powerpick([b for b in options[i+1:] if gap(a,b)>=.3],
            [b for b in signals if gap(a,b)>=.3],chosen+[a],need-1):return True
    return False
powerpick(power,signal,[],7)
selected_pairs=[];outputs={}
if solution:
    assert len(solution)==11
    for i,a in enumerate(solution):
        a['allocation_id']=i
        for yaw,p in curves.items():outputs[f'wire{i}_y{yaw}']=rotate(p,a['angle_deg'])
    for a,b in itertools.combinations(solution,2):
        g=gap(a,b);assert g>=.3
        selected_pairs.append(dict(a=a['allocation_id'],b=b['allocation_id'],surface_gap_lower_bound_mm=g))
    np.savez_compressed(HERE/'packed_curves.npz',**outputs)
out=dict(status='PASS' if solution else 'BLOCKED',scope='Eleven simultaneous local curves in the larger-bearing interface capacity model',
    source_main_sha256=screen['source_main_sha256'],source_screen_sha256=sha(HERE/'screen.json'),
    script_sha256=sha(__file__),source_curves_sha256=sha(HERE/'curves.npz'),family=ref,
    selected=solution,pair_bounds=pairs,selected_pairs=selected_pairs,
    minimum_pair_gap_lower_bound_mm=min(r['surface_gap_lower_bound_mm'] for r in selected_pairs) if solution else None,
    candidate_counts={'signal':len(signal),'power_sample':len(power)},search_nodes=calls,search_limit=limit,
    solution_found=solution is not None,exhaustive_search=False,
    checked_wire_pairs=len(selected_pairs)*13,head_poses=130,
    output_curves_sha256=sha(HERE/'packed_curves.npz') if solution else None,
    complete_printed_parts='NOT_TESTED',actual_wire_selection='BLOCKED',full_endpoints='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(HERE/'packing.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('CAPACITY_PACKED',out['status'],out['minimum_pair_gap_lower_bound_mm'],solution,'seconds',round(out['elapsed_s'],1),flush=True)
