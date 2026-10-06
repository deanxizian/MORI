"""Bounded S-bend alternatives keep wires outside the yaw collar.

Only wire curves are varied. Existing selected PCB prefixes, native solids,
wire diameter and required clearance are preserved. No upper loops implied.
"""
from pathlib import Path
import sys,json,math,itertools,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from native_context import *
from validate import rigidtr
ctx=Context();started=time.time()
d=json.loads((HERE/'packing.json').read_text())
cache=np.load(HERE/'packed_curves.npz')
R=float(sys.argv[sys.argv.index('--radius')+1]) if '--radius' in sys.argv else 7.
stem='outer_risers' if R==7 else f'outer_risers_R{R:g}'
error=R*(1-math.cos(math.pi/800))
curves={};rows=[];passing=[]
for selected in d['selected']:
    pin=selected['pin'];theta=math.radians(selected['azimuth_deg'])
    er=np.array([math.cos(theta),math.sin(theta),0.]);ez=np.array([0.,0.,1.])
    lower=selected['neck_parameters']['lower_z_mm']
    start=cache[f'pin{pin}'][selected['prefix_points']-1]
    t=np.linspace(0,math.pi/2,201)
    elbow=np.array([start+8*math.sin(q)*er+8*(1-math.cos(q))*ez for q in t])
    for target_radius,turn_z in itertools.product([27.8,28.4,29.,29.6,30.2,30.8,31.4,32.], [150.,152.,154.,156.,158.,160.]):
        if turn_z<lower+8:continue
        delta=37.6-target_radius
        angle=math.acos(1-delta/(2*R));rise=2*R*math.sin(angle)
        a=37.6*er+turn_z*ez
        line=np.linspace(elbow[-1],a,max(2,math.ceil(np.linalg.norm(a-elbow[-1])/.05)+1))
        t=np.linspace(0,angle,201)
        first=np.array([a-R*(1-math.cos(v))*er+R*math.sin(v)*ez for v in t]);mid=first[-1]
        second=np.array([mid-R*(math.cos(v)-math.cos(angle))*er+R*(math.sin(angle)-math.sin(v))*ez for v in t[::-1]])
        end=target_radius*er+193*ez
        upright=np.linspace(second[-1],end,max(2,math.ceil(np.linalg.norm(end-second[-1])/.05)+1))
        p=np.vstack([elbow,line[1:],first[1:],second[1:],upright[1:]])
        err=max(error,8*(1-math.cos(math.pi/800)))
        hit=ctx.clear(p,err)
        key=f'pin{pin}_r{target_radius}_z{turn_z}'
        row=dict(key=key,pin=pin,azimuth_deg=selected['azimuth_deg'],target_radius_mm=target_radius,
                 turn_start_z_mm=turn_z,turn_end_z_mm=turn_z+rise,minimum_radius_mm=min(8.,R),
                 error_bound_mm=err,status='BLOCKED' if hit else 'PASS',zero_pose_hit=hit,
                 analytic_length_mm=8*math.pi/2+(turn_z-lower-8)+2*R*angle+(193-turn_z-rise))
        rows.append(row)
        if hit is None:passing.append(row);curves[key]=p
    print('OUTER_RISERS_ZERO',pin,'passing',sum(r['pin']==pin for r in passing),flush=True)

moving={n:s for n,s in ctx.ss.items() if s.group in ['yaw','pitch']}
original=ctx.targets.copy()
fixed={n:t for n,t in original.items() if n not in moving}
survivors={r['key']:r for r in passing};motion_rows=[]
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        if not survivors:break
        ctx.targets=fixed.copy()
        for n,s in moving.items():
            tr=np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))
            m=s.m.transform(tr[:3,:]);bb=np.asarray(m.bounding_box())
            if bb[2]>194 or bb[5]<139:continue
            ctx.targets[n]=ctx.target(m)
        for key,row in list(survivors.items()):
            hit=ctx.clear(curves[key],row['error_bound_mm'])
            if hit:
                motion_rows.append(dict(key=key,status='BLOCKED',yaw_deg=yaw,pitch_deg=pitch,hit=hit))
                del survivors[key]
    print('OUTER_RISERS_MOTION',yaw,'remaining',len(survivors),flush=True)
    if not survivors:break
ctx.assert_unchanged()
np.savez_compressed(HERE/(stem+'_curves.npz'),**curves)
result=dict(status='PASS' if len({r['pin'] for r in survivors.values()})==4 else 'BLOCKED',
    scope='Individual alternative outer S-bend risers; no simultaneous packing, retention or upper flex loop',
    **ctx.evidence(),script_sha256=sha(__file__),source_packing_sha256=sha(HERE/'packing.json'),
    trials=rows,zero_pose_passes=len(passing),motion_first_failures=motion_rows,
    motion_survivors=list(survivors.values()),survivor_pose_count=130,
    main_applied=False,whole_harness='BLOCKED',simultaneous_packing='NOT_TESTED',
    upper_service_loop='NOT_TESTED',assembly='NOT_TESTED',elapsed_s=time.time()-started)
(HERE/(stem+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('OUTER_RISERS_DONE',result['status'],len(survivors),flush=True)
