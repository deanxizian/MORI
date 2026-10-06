"""Screen yaw-carried wire corridors on native M1.48 solids.

The starts are horizontal/outward at Z168. A future planar service loop must
connect them to the actual body roots with constant material length. These
rigid upper corridors alone are not a harness or an installed cable.
"""
from pathlib import Path
import sys,json,math,itertools,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context, sha, np
from validate import rigidtr
ctx=Context();started=time.time()
carrier=sys.argv[sys.argv.index('--carrier')+1] if '--carrier' in sys.argv else 'yaw'
assert carrier in ['yaw','pitch']
stem='upper_corridors' if carrier=='yaw' else 'upper_pitch_corridors'
Z=168.;TOP=193.;R=7.;error=R*(1-math.cos(math.pi/800))
paths={};rows=[];passing={}
ez=np.array([0.,0.,1.])
for angle,radius in itertools.product(range(0,360,10),[27.8,28.4,29.,29.6,30.2,30.8,31.4,32.]):
    theta=math.radians(angle);er=np.array([math.cos(theta),math.sin(theta),0.])
    start=(radius-R)*er+Z*ez
    t=np.linspace(0,math.pi/2,201)
    arc=np.array([start+R*math.sin(v)*er+R*(1-math.cos(v))*ez for v in t])
    tail=np.linspace(arc[-1],radius*er+TOP*ez,361)
    p=np.vstack([arc,tail[1:]])
    hit=ctx.clear(p,error)
    key=f'a{angle}_r{radius}'
    row=dict(key=key,azimuth_deg=angle,outer_radius_mm=radius,start_radius_mm=radius-R,
        start_z_mm=Z,top_z_mm=TOP,bend_radius_mm=R,start_mm=start.tolist(),end_mm=p[-1].tolist(),
        length_mm=R*math.pi/2+TOP-Z-R,error_bound_mm=error,
        status='BLOCKED' if hit else 'PASS',zero_pose_hit=hit)
    rows.append(row)
    if not hit:paths[key]=p;passing[key]=row
print('UPPER_YAW_ZERO',len(passing),'of',len(rows),flush=True)
moving={n:s for n,s in ctx.ss.items() if s.group in ['yaw','pitch']}
fixed={n:t for n,t in ctx.targets.items() if n not in moving}
cases=[(y,p) for y,p in itertools.product(range(-60,61,10),range(-20,26,5))]
# Check the extremes early to avoid spending time on already-failed paths.
first=[(-60,-20),(60,25),(0,-20),(0,25),(0,0)]
cases=first+[c for c in cases if c not in first]
survivors=passing.copy();failures=[];pose_counts={key:0 for key in passing}
for index,(yaw,pitch) in enumerate(cases):
    if not survivors:break
    ctx.targets=fixed.copy()
    ty=np.asarray(rigidtr(yaw,pitch if carrier=='pitch' else 0))
    for name,s in moving.items():
        mat=np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))
        m=s.m.transform(mat[:3,:]);bb=np.asarray(m.bounding_box())
        if bb[2]>194 or bb[5]<167:continue
        ctx.targets[name]=ctx.target(m)
    for key,row in list(survivors.items()):
        p=paths[key]@ty[:3,:3].T+ty[:3,3]
        hit=ctx.clear(p,error);pose_counts[key]+=1
        if hit:
            failures.append(dict(key=key,yaw_deg=yaw,pitch_deg=pitch,hit=hit))
            del survivors[key]
    if index<5 or index%10==9:print('UPPER_YAW_POSE',index+1,yaw,pitch,'remaining',len(survivors),flush=True)

ctx.assert_unchanged()
np.savez_compressed(HERE/(stem+'.npz'),**paths)
report=dict(status='PASS' if survivors else 'BLOCKED',
    scope='Individual rigid '+carrier+'-carried upper wire corridors at finite combined yaw/pitch poses',
    carrier_group=carrier,
    **ctx.evidence(),script_sha256=sha(__file__),zero_pose_trials=rows,
    zero_pose_passes=len(passing),pose_order=cases,pose_counts=pose_counts,first_failures=failures,
    survivors=list(survivors.values()),wire_OD_mm=.6604,surface_gap_mm=.3,
    source_body_paths_sha256=sha(HERE.parent/'outer_harness_M1_48/packed_curves.npz'),
    body_connection='NOT_TESTED',constant_length_service_loop='NOT_TESTED',
    four_wire_packing='NOT_TESTED',assembly='NOT_TESTED',whole_harness='BLOCKED',
    main_applied=False,elapsed_s=time.time()-started)
(HERE/(stem+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('UPPER_YAW_DONE',report['status'],len(survivors),flush=True)
