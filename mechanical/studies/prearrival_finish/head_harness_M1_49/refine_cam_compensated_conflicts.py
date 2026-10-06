"""Refine the same polylines and diagnose actual upper/lower conflicts.

Subdivision does not move a sampled curve and retains its analytic error
bound. A failed coarse bound is not itself a demonstrated intersection.
"""
from pathlib import Path
import itertools,json,sys,time,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
L=HERE/'remaining_routes/cam_compensated_loops';N=HERE/'remaining_routes/rear_power_bump'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
import numpy as np
from curve_clearance import prepared,pair
from upper_pack_geometry import refined
from bounded_curve_checks import pair_threshold
from validate import rigidtr
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text());start=time.time()
r=read(L/'loop_screen.json');n=read(N/'neck_screen.json')
for report in [r,n]:
    for f,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(L/'curves.npz')==r['curve_sha256'] and sha(N/'curves.npz')==n['curve_sha256']
loops=np.load(L/'curves.npz');neck=np.load(N/'curves.npz');cache={};low={}
def upper(pin,yaw,pitch):
    k=(pin,yaw,pitch)
    if k not in cache:cache[k]=prepared(refined(loops[f'pin{pin}_y{yaw}_p{pitch}'],.01),.3302,.0003)
    return cache[k]
def lower(slot,yaw):
    k=(slot,yaw)
    if k not in low:
        tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=neck[f'wire{slot}_y{yaw}'];p=p@tr[:3,:3].T+tr[:3,3]
        low[k]=prepared(refined(p,.01),n['OD_mm'][slot]/2,.0003)
    return low[k]
pairs=[];conflicts=[]
for old in r['pairs']:
    if old['status']=='PASS':pairs.append(old);continue
    yaw,pitch,a,b=(old[k] for k in ['yaw','pitch','a','b'])
    pairs.append(dict(yaw=yaw,pitch=pitch,a=a,b=b,**pair(upper(a,yaw,pitch),upper(b,yaw,pitch))))
print('REFINED_COMPENSATED_PAIRS',sum(x['status']!='PASS' for x in pairs),flush=True)
for old in r['lower_conflicts']:
    pin,yaw,pitch,slot=(old[k] for k in ['pin','yaw','pitch','slot'])
    result=pair_threshold(upper(pin,yaw,pitch),lower(slot,yaw))
    if result['status']!='PASS':conflicts.append(dict(pin=pin,yaw=yaw,pitch=pitch,slot=slot,**result))
deepest=[]
# Global distance for the zero-yaw witnesses, or the closest sampled yaw if no zero witness exists.
for key in sorted({(v['pin'],v['slot']) for v in conflicts}):
    candidates=[v for v in conflicts if (v['pin'],v['slot'])==key]
    row=min(candidates,key=lambda v:(abs(v['yaw']),abs(v['pitch'])))
    p,y,pt,s=(row[k] for k in ['pin','yaw','pitch','slot'])
    result=pair(upper(p,y,pt),lower(s,y));deepest.append(dict(pin=p,yaw=y,pitch=pt,slot=s,**result))
ok=not r['hits'] and not conflicts and all(x['status']=='PASS' for x in pairs+r['self_checks'])
inputs=[L/'loop_screen.json',L/'curves.npz',N/'neck_screen.json',N/'curves.npz',HERE/'upper_pack_geometry.py',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']
out=dict(status='PASS' if ok else 'BLOCKED',sources=r['sources'],inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
         scope='Same sampled curves refined to 0.01 mm spacing; no route or hardware changes.',pairs=pairs,lower_conflicts=conflicts,global_pair_examples=deepest,
         reused_native_checks=r['native_checks'],reused_self_checks=len(r['self_checks']),retained_lower_pairs=5720-len(r['lower_conflicts']),
         refined_lower_pairs=len(r['lower_conflicts']),main_changed=False,C6_main_applied=False,full_harness='BLOCKED',
         script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(L/'refined_pairs.json').write_text(json.dumps(out,indent=2)+'\n');print('REFINED_COMPENSATED_DONE',out['status'],len(conflicts),deepest,out['elapsed_s'],flush=True)
