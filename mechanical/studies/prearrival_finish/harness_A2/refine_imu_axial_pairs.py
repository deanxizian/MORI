# -*- coding: utf-8 -*-
"""Broaden remaining pin3..8 turns with bounded axial-control variations.

All endpoints, terminal tangents and middle joins are fixed to an already
screened seed. No printed opening or purchased geometry changes.
"""
from pathlib import Path
import json,hashlib,time,collections
STAGE=Path(__file__).resolve().parent
code=(STAGE/'imu_individual_routes.py').read_text().split('choices=[')[0]
exec(compile(code,str(STAGE/'imu_individual_routes.py'),'exec'),globals())
input_file=STAGE/'imu_dual_terminal_assembly_pools.json'
data=json.loads(input_file.read_text());pools={};search=[];start=time.time()
rng=np.random.default_rng(90721)
for pin in map(str,range(3,9)):
    seeds=data['pools'][pin];pool=[];counts=collections.Counter();blockers=collections.Counter()
    for _ in range(6000):
        idx=int(rng.integers(len(seeds)));row=seeds[idx]
        c1,c2=map(np.asarray,row['cubic_controls_mm'])
        u=c1[1]-c1[0];ul=np.linalg.norm(u);u/=ul
        v=c2[2]-c2[3];vl=np.linalg.norm(v);v/=vl
        du,dv=rng.uniform(-8.,12.,2)
        if min(ul+du,vl+dv)<=1.:continue
        counts['tried']+=1;c1=c1.copy();c2=c2.copy()
        c1[1]=c1[0]+u*(ul+du);c2[2]=c2[3]+v*(vl+dv)
        if min(radius_at_samples(c1),radius_at_samples(c2))<R+.02:
            counts['curvature_reject']+=1;continue
        curve=np.vstack([bezier(c1,np.linspace(0,1,181)),bezier(c2,np.linspace(0,1,181))[1:]])
        name,where=check_points(resample(curve,.24))
        if name:
            counts['space_reject']+=1;blockers[name]+=1;continue
        r1,q1=extrema_radius(c1);r2,q2=extrema_radius(c2)
        if min(r1,r2)<R+.02:
            counts['extrema_reject']+=1;continue
        full=np.vstack([row['curve_mm'][0],curve,row['curve_mm'][-1]])
        pool.append(dict(row,curve_mm=full.tolist(),cubic_controls_mm=[c1.tolist(),c2.tolist()],
            minimum_curvature_radius_mm=min(r1,r2),curvature_extrema_parameters=[q1,q2],
            geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),
            source_filtered_pool_index=idx,upper_terminal_control_shift_mm=float(du),terminal_control_shift_mm=float(dv),
            refinement='Bounded two-ended axial control variation; all other seed controls retained'))
        if len(pool)>=128:break
    pools[pin]=pool;search.append(dict(pin=pin,candidates=len(pool),**counts,blockers=dict(blockers)))
    print('IMU_AXIAL_PAIR_REFINE',search[-1],time.time()-start,flush=True)
out=dict(source_blend_sha256=source_hash,source_six_wire_sha256=data['source_six_wire_sha256'],
    sources={input_file.name:hashlib.sha256(input_file.read_bytes()).hexdigest()},
    status='PASS' if all(pools.values()) else 'BLOCKED',
    scope='Pin3..8 static curve additions; assembly screen and eight-wire selection still required',
    pools=pools,search=search,elapsed_s=time.time()-start,main_modified=False,extra_print_holes=False)
(STAGE/'imu_axial_pair_pools.json').write_text(json.dumps(out,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
