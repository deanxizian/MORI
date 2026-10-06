"""Test a prescribed inward/upward continuation from each neck staging end.

No print is changed. A failed candidate identifies its actual contact; it
does not rule out another route or stand in for a yaw/pitch service loop.
"""
from pathlib import Path
import sys, json, math, itertools, time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from native_context import *
from validate import rigidtr
ctx=Context();started=time.time()
selection=json.loads((HERE/'packing.json').read_text())
verification=json.loads((HERE/'verification.json').read_text())
assert selection['status']==verification['status']=='PASS'
cache=np.load(HERE/'packed_curves.npz')
paths={};parameters={};saved={}
for r in selection['selected']:
    pin=r['pin'];a=math.radians(r['azimuth_deg'])
    er=np.array([math.cos(a),math.sin(a),0.]);ez=np.array([0.,0.,1.])
    start=cache[f'pin{pin}'][-1]
    # Existing documented study staging radius; remains an allocation.
    inside_radius=6.8;R=7.;height=193.
    bend_start=(inside_radius+R)*er+168*ez
    line=np.linspace(start,bend_start,math.ceil(np.linalg.norm(start-bend_start)/.05)+1)
    t=np.linspace(0,math.pi/2,201)
    bend=np.array([bend_start-er*R*math.sin(v)+ez*R*(1-math.cos(v)) for v in t])
    tail=np.linspace(bend[-1],inside_radius*er+height*ez,361)
    curve=np.vstack([line,bend[1:],tail[1:]])
    paths[pin]=curve;saved[f'pin{pin}']=curve
    parameters[pin]=dict(angle_deg=r['azimuth_deg'],inward_straight_mm=float(np.linalg.norm(start-bend_start)),
        bend_radius_mm=R,staging_radius_mm=inside_radius,staging_z_mm=height,
        analytic_length_mm=float(np.linalg.norm(start-bend_start)+math.pi*R/2+height-175),
        error_bound_mm=float(R*(1-math.cos(math.pi/800))))

moving={n:s for n,s in ctx.ss.items() if s.group in ['yaw','pitch']}
fixed={n:t for n,t in ctx.targets.items() if n not in moving}
corners={n:np.array(list(itertools.product(*zip(s.lo,s.hi)))) for n,s in moving.items()}
rows=[]
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        ctx.targets=fixed.copy()
        for n,s in moving.items():
            tr=rigidtr(yaw,pitch if s.group=='pitch' else 0)
            mat=np.asarray(tr);bb=corners[n]@mat[:3,:3].T+mat[:3,3]
            if bb[:,2].min()>194 or bb[:,2].max()<167:continue
            ctx.targets[n]=ctx.target(s.m.transform(mat[:3,:]))
        for pin,p in paths.items():
            hit=ctx.clear(p,parameters[pin]['error_bound_mm'])
            rows.append(dict(pin=pin,yaw_deg=yaw,pitch_deg=pitch,status='BLOCKED' if hit else 'PASS',hit=hit))
    print('UPPER_ENTRY_YAW',yaw,'failed',sum(r['status']=='BLOCKED' for r in rows),flush=True)

ctx.assert_unchanged()
np.savez_compressed(HERE/'upper_entry_curves.npz',**saved)
result=dict(status='BLOCKED' if any(r['status']=='BLOCKED' for r in rows) else 'PASS',
    scope='Four prescribed fixed inward/R7/upward continuations; not an assembled or complete moving harness',
    **ctx.evidence(),source_packing_sha256=sha(HERE/'packing.json'),script_sha256=sha(__file__),
    source_verified_body_sha256=sha(HERE/'verification.json'),parameters=parameters,rows=rows,
    bend_radius_mm=7.,head_poses=130,wire_to_wire='NOT_TESTED',
    native_main_unchanged=True,main_applied=False,whole_harness='BLOCKED',
    upper_service_loop='NOT_TESTED',assembly='NOT_TESTED',elapsed_s=time.time()-started)
(HERE/'upper_entry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('UPPER_ENTRY_DONE',result['status'],flush=True)
