"""Global all-sample distance bounds for the selected 11 partial routes."""
from pathlib import Path
import sys,json,itertools,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import np,sha
from common import P
from mathutils.kdtree import KDTree
from mathutils import Vector
start=time.time();read=lambda n:json.loads((HERE/n).read_text())
proof=read('current_source_verification.json');assert proof['status']=='PASS'
for p,h in proof['sources'].items():assert sha(PROJECT/p)==h,p
for p,h in proof['inputs'].items():assert sha(HERE/p)==h,p
selected=read('body_layered_four_screen.json');local=read('spaced_entry_screen.json')
neck=np.load(HERE/'spaced_entry_candidates.npz');full=np.load(HERE/'body_layered_four_candidates.npz')
by_slot={r['slot']:r for r in selected['selected']};rows=[]
error=local['results'][0]['max_chord_error_mm']
for yaw in range(-60,61,10):
    current=[]
    for i,allocation in enumerate(P['neck_harness_capacity']['wire_allocations']):
        r=by_slot.get(i);p=full[f'pin{r["pin"]}_y{yaw}'] if r else neck[f'case0_wire{i}_y{yaw}']
        t=KDTree(len(p))
        for k,v in enumerate(p):t.insert(Vector(v),k)
        t.balance()
        current.append(dict(points=p,tree=t,radius=allocation['OD_mm']/2,error=max(error,r['chord_error_mm']) if r else error,
            step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())))
    for i,j in itertools.combinations(range(11),2):
        a=current[i];b=current[j]
        # Query all vertices. No threshold-based point clipping is used when
        # reporting a numerical global minimum larger than the required gap.
        d,k=min((float(b['tree'].find(Vector(p))[2]),k) for k,p in enumerate(a['points']))
        lower=d-a['radius']-b['radius']-(a['step']+b['step'])/2-a['error']-b['error']-1e-4
        rows.append(dict(a=i,b=j,yaw=yaw,gap_lower_bound_mm=lower,point_mm=a['points'][k].tolist(),status='PASS' if lower>=.3 else 'BLOCKED'))
    print('GLOBAL_LOWER_GAP_YAW',yaw,flush=True)
minimum=min(rows,key=lambda r:r['gap_lower_bound_mm'])
result=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    source_blend_sha256=proof['source_blend_sha256'],sources=proof['sources'],
    proof_sha256=sha(HERE/'current_source_verification.json'),
    inputs={name:sha(HERE/name) for name in ['spaced_entry_candidates.npz','body_layered_four_candidates.npz','body_layered_four_screen.json','spaced_entry_screen.json']},
    rows=rows,minimum=minimum,required_surface_gap_mm=.3,
    scope='Global sampled-polyline minimum for all715pairs, with both half-steps/chord errors deducted; finite poses only',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(HERE/'lower_global_gap.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('GLOBAL_LOWER_GAP',result['status'],minimum,flush=True)
