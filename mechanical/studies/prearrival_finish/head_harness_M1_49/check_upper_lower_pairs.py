"""Simultaneous upper CAM loops versus all revised lower routing segments."""
from pathlib import Path
import sys,json,time,itertools
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import np,sha
from common import P
from validate import rigidtr
from curve_clearance import prepared,pair
from upper_pack_geometry import refined
read=lambda n:json.loads((HERE/n).read_text());start=time.time()
lower=read('front_lower_verification.json');upper=read('cam_upper_screen.json');front=read('front_route_screen.json')
assert lower['status']==upper['status']=='PASS'
for report in [lower,upper]:
    for p,h in report['sources'].items():assert sha(PROJECT/p)==h,p
for p,h in lower['inputs'].items():assert sha(HERE/p)==h,p
for p,h in upper['inputs'].items():assert sha(PROJECT/p)==h,p
lower_curves=np.load(HERE/'front_lower_curves.npz');neck=np.load(HERE/'front_neck_candidates.npz');up=np.load(HERE/'cam_upper_candidates.npz')
assert sha(HERE/'front_lower_curves.npz')==lower['curve_sha256']
assert sha(HERE/'cam_upper_candidates.npz')==upper['curve_sha256']
ods=[r['OD_mm'] for r in P['neck_harness_capacity']['wire_allocations']]
by_slot={r['slot']:r for r in [lower['selected']]+lower['other_selected']}
cache={}
for yaw in range(-60,61,10):
    inv=np.linalg.inv(np.asarray(rigidtr(yaw,0)))
    for i in range(11):
        row=by_slot.get(i);p=lower_curves[f'pin{row["pin"]}_y{yaw}'] if row else neck[f'wire{i}_y{yaw}']
        error=max(front['local_chord_error_mm'],row['chord_error_mm']) if row else front['local_chord_error_mm']
        # Work in yaw coordinates; rotations preserve all distances.
        cache[i,yaw]=prepared(p@inv[:3,:3].T+inv[:3,3],ods[i]/2,error)
rows=[];mutual=[];examples=[]
for pitch in range(-20,26,5):
    u=[prepared(refined(up[f'slot{i}_pitch{pitch}']),.3302,.0003) for i in range(4)]
    for i,j in itertools.combinations(range(4),2):mutual.append(dict(pitch=pitch,a=i,b=j,**pair(u[i],u[j])))
    for pin,yaw,i in itertools.product(range(1,5),range(-60,61,10),range(11)):
        r=pair(u[pin-1],cache[i,yaw]);row=dict(pin=pin,pitch=pitch,yaw=yaw,lower_slot=i,**r);rows.append(row)
        if r['status']!='PASS' and len(examples)<24:examples.append(row)
    print('UPPER_LOWER_PITCH',pitch,'failed',sum(r['status']!='PASS' for r in rows+mutual),flush=True)
out=dict(status='PASS' if all(r['status']=='PASS' for r in rows+mutual) else 'BLOCKED',
    source_blend_sha256=lower['source_blend_sha256'],sources=lower['sources'],
    inputs={n:sha(HERE/n) for n in ['front_lower_verification.json','front_lower_curves.npz','front_neck_candidates.npz','cam_upper_screen.json','cam_upper_candidates.npz','curve_clearance.py','upper_pack_geometry.py']},
    rows=rows,upper_mutual=mutual,first_failures=examples,
    scope='All four CAM upper loop/tail shapes versus all11lower wires over130poses; yaw-fixed connecting fans absent',
    full_harness='BLOCKED',main_changed=False,anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(HERE/'upper_lower_pairs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('UPPER_LOWER_DONE',out['status'],len(rows),len(mutual),flush=True)
