# -*- coding: utf-8 -*-
"""Numbered IMU wire candidates through one unadopted closed deck slot."""
from pathlib import Path
import json,hashlib,sys,time,collections
STAGE=Path(__file__).resolve().parent
code=(STAGE/'imu_individual_routes.py').read_text().split('choices=[')[0]
exec(compile(code,str(STAGE/'imu_individual_routes.py'),'exec'),globals())
sys.path.insert(0,str(STAGE))
from deck_slot_candidate import apply_to_study
candidate=apply_to_study(globals())
OUT_STEM='imu_slot'
rng=np.random.default_rng(902)
da=port_pins['motion_J4'];db=port_pins['imu_J1']
pools={};search=[];start=time.time()
for pin in range(1,9):
    ea=da['pins'][str(pin)];eb=db['pins'][str(pin)]
    a=ea+5*da['axis'];b=eb+5*db['axis']
    nominal_y=-30.-2*(pin-1)
    choices=[[38.6,39.3,40.,40.7,41.4],
        [nominal_y+d for d in [-1.,-.5,0.,.5,1.]],
        [117.,118.,119.,120.,121.,122.],
        [105.,106.,107.,108.,109.],
        [6.,9.,12.,15.,18.,21.,24.,27.,30.],
        [8.,12.,16.,20.,24.,28.,32.],
        [8.,12.,16.,20.,24.,28.,32.],
        [6.,9.,12.,15.,18.,21.,24.]]
    count=collections.Counter();blocked=collections.Counter();pool=[];keys=set()
    for _ in range(70000):
        x,y,zu,zl,up,end_up,start_down,down=[c[int(rng.integers(len(c)))] for c in choices]
        k1=np.array([x,y,zu]);k2=np.array([x,y,zl]);down_axis=np.array([0.,0.,-1.])
        c1=np.array([a,a+da['axis']*up,k1-down_axis*end_up,k1])
        c2=np.array([k2,k2+down_axis*start_down,b+db['axis']*down,b])
        count['tried']+=1
        if min(radius_at_samples(c1),radius_at_samples(c2))<R+.02:
            count['curvature_reject']+=1;continue
        curve=np.vstack([bezier(c1,np.linspace(0,1,181)),k2,bezier(c2,np.linspace(0,1,181))[1:]])
        n,p=check_points(resample(curve,.24))
        if n:count['space_reject']+=1;blocked[n]+=1;continue
        r1,q1=extrema_radius(c1);r2,q2=extrema_radius(c2)
        if min(r1,r2)<R+.02:count['extrema_reject']+=1;continue
        key=(x,y,zu,zl,up,end_up,start_down,down)
        if key in keys:continue
        keys.add(key);full=np.vstack([ea,curve,eb])
        pool.append(dict(id='H04_'+str(pin),harness='H04',pin=pin,from_port='motion_J4',to_port='imu_J1',
            curve_mm=full.tolist(),cubic_controls_mm=[c1.tolist(),c2.tolist()],
            inter_cubic_straight_mm=[k1.tolist(),k2.tolist()],
            wire_OD_max_mm=OD,required_bend_radius_mm=R,terminal_straight_mm=5,
            minimum_curvature_radius_mm=min(r1,r2),curvature_extrema_parameters=[q1,q2],
            geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),
            route_side='right',method='Two tangent-continuous cubics separated by vertical slot crossing; exact terminal straights'))
        if len(pool)>=90:break
    pools[str(pin)]=pool
    search.append(dict(pin=pin,**count,candidates=len(pool),blockers=dict(blocked)))
    print('IMU_SLOT_POOL',search[-1],time.time()-start,flush=True)
    (STAGE/(OUT_STEM+'_progress.json')).write_text(json.dumps(search,indent=2)+'\n')
out=dict(revision=P['revision'],source_blend_sha256=source_hash,
    source_six_wire_sha256=hashlib.sha256((STAGE/'ecowire_joint.json').read_bytes()).hexdigest(),
    status='PASS' if all(pools.values()) else 'BLOCKED',scope='Individual curves only; slot not adopted; joint/assembly pending',
    candidate=candidate,pools=pools,search=search,elapsed_s=time.time()-start,
    main_modified=False,cut_lengths_released=False)
(STAGE/(OUT_STEM+'_pools.json')).write_text(json.dumps(out,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('IMU_SLOT_POOLS_DONE',out['status'],time.time()-start,flush=True)
