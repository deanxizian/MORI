# -*- coding: utf-8 -*-
"""Explicit rear U-turn, under-carrier straight, internal slot and lower turn.

Unadopted candidate only. Fixed native pin numbering / unselected6711 retained.
"""
from pathlib import Path
import json,hashlib,sys,time,collections
STAGE=Path(__file__).resolve().parent
code=(STAGE/'imu_individual_routes.py').read_text().split('choices=[')[0]
exec(compile(code,str(STAGE/'imu_individual_routes.py'),'exec'),globals())
sys.path.insert(0,str(STAGE))
from deck_slot_candidate import apply_to_study
candidate=apply_to_study(globals())
rng=np.random.default_rng(390);da=port_pins['motion_J4'];db=port_pins['imu_J1']
pools={};search=[];start=time.time()
theta=np.linspace(0,math.pi/2,91);utheta=np.linspace(0,math.pi,181)
for pin in range(1,9):
    ea=da['pins'][str(pin)];eb=db['pins'][str(pin)];a=ea+5*da['axis'];b=eb+5*db['axis']
    choices=[[-65.0,-65.5,-66.,-66.5,-67.,-67.5], [5.3,6.,7.,8.],
        [2.,3.,4.,5.,6.,7.,8.], [2.,3.,4.,5.,6.,7.,8.],
        [106.,107.,108.], [6.,10.,14.,18.,22.,26.,30.], [6.,10.,14.,18.,22.,26.,30.]]
    count=collections.Counter();blocked=collections.Counter();pool=[];keys=set()
    for _ in range(70000):
        yback,backR,up,topdown,zl,lowerdown,enddown=[c[int(rng.integers(len(c)))] for c in choices]
        xu=ea[0];zu=117.7;yy=-39.;rt=5.3
        k1=np.array([xu,yback,zu+backR]);p1=np.array([xu,yback+backR,zu])
        p2=np.array([xu,yy-rt,zu]);k2=np.array([xu,yy,zl])
        topR=5.4
        top_arc=np.array([[xu,a[1]-topR*(1-math.cos(t)),a[2]+topR*math.sin(t)] for t in utheta])
        kt=top_arc[-1]
        c1=np.array([kt,kt-np.array([0,0,up]),k1+np.array([0,0,topdown]),k1])
        c2=np.array([k2,k2+np.array([0,0,-lowerdown]),b+db['axis']*enddown,b])
        count['tried']+=1
        if min(radius_at_samples(c1),radius_at_samples(c2))<R+.02:
            count['curvature_reject']+=1;continue
        arc1=np.array([[xu,yback+backR*(1-math.cos(t)),zu+backR-backR*math.sin(t)] for t in theta])
        arc2=np.array([[xu,yy-rt+rt*math.sin(t),zu-rt*(1-math.cos(t))] for t in theta])
        curve=np.vstack([top_arc,bezier(c1,np.linspace(0,1,181))[1:],arc1[1:],p2,arc2[1:],k2,bezier(c2,np.linspace(0,1,181))[1:]])
        n,p=check_points(resample(curve,.24))
        if n:count['space_reject']+=1;blocked[n]+=1;continue
        r1,q1=extrema_radius(c1);r2,q2=extrema_radius(c2)
        if min(r1,r2)<R+.02:count['extrema_reject']+=1;continue
        key=(yback,backR,up,topdown,zl,lowerdown,enddown)
        if key in keys:continue
        keys.add(key);full=np.vstack([ea,curve,eb])
        pool.append(dict(id='H04_'+str(pin),harness='H04',pin=pin,from_port='motion_J4',to_port='imu_J1',
            curve_mm=full.tolist(),cubic_controls_mm=[c1.tolist(),c2.tolist()],
            circular_bends=dict(top_radius_mm=topR,rear_radius_mm=backR,slot_radius_mm=rt,steps_per_quadrant=90),
            wire_OD_max_mm=OD,required_bend_radius_mm=R,terminal_straight_mm=5,
            minimum_curvature_radius_mm=min(r1,r2,topR,backR,rt),curvature_extrema_parameters=[q1,q2],
            geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),
            route_side='right',method='Circular upper U-turn, cubic descending offset, two tangent circular quarter bends, lower cubic turn and exact terminal/under-board/slot straights'))
        if len(pool)>=110:break
    pools[str(pin)]=pool;search.append(dict(pin=pin,**count,candidates=len(pool),blockers=dict(blocked)))
    print('IMU_INNER_SLOT_POOL',search[-1],time.time()-start,flush=True)
    (STAGE/'imu_slot_progress.json').write_text(json.dumps(search,indent=2)+'\n')
out=dict(revision=P['revision'],source_blend_sha256=source_hash,
    source_six_wire_sha256=hashlib.sha256((STAGE/'ecowire_joint.json').read_bytes()).hexdigest(),
    status='PASS' if all(pools.values()) else 'BLOCKED',scope='Individual curves only; internal slot not adopted; joint/assembly pending',
    candidate=candidate,pools=pools,search=search,elapsed_s=time.time()-start,main_modified=False,cut_lengths_released=False)
(STAGE/'imu_slot_pools.json').write_text(json.dumps(out,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('IMU_INNER_SLOT_DONE',out['status'],time.time()-start,flush=True)
