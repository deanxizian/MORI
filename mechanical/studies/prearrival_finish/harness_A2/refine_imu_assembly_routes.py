# -*- coding: utf-8 -*-
"""Refine valid existing-structure routes, preserving all hardware and holes."""
from pathlib import Path
import json,hashlib,sys,time,collections
STAGE=Path(__file__).resolve().parent
code=(STAGE/'imu_individual_routes.py').read_text().split('choices=[')[0]
exec(compile(code,str(STAGE/'imu_individual_routes.py'),'exec'),globals())
inputs=[STAGE/'imu_assembly_pools.json',STAGE/'imu_side_assembly_pools.json']
datasets=[json.loads(p.read_text()) for p in inputs]
assert all('Nearest-face-normal sign is not used' in d['method'] for d in datasets)
rng=np.random.default_rng(8902);pools={};search=[];start=time.time()
for pin in range(1,9):
    seeds=[r for d in datasets for r in d['pools'][str(pin)]]
    pool=seeds[:];counts=collections.Counter();blockers=collections.Counter()
    for _ in range(10000 if seeds else 0):
        row=seeds[int(rng.integers(len(seeds)))];c1,c2=map(np.asarray,row['cubic_controls_mm'])
        k=c1[-1];tan=c2[1]-k;tan/=np.linalg.norm(tan)
        delta=np.array([rng.uniform(-3.5,3.5),rng.uniform(-1.0,1.0),rng.uniform(-3.5,3.5)])
        kk=k+delta;h1=np.linalg.norm(c1[-2]-k)+rng.uniform(-3,3);h2=np.linalg.norm(c2[1]-k)+rng.uniform(-3,3)
        cc1=c1.copy();cc2=c2.copy();cc1[-1]=cc2[0]=kk;cc1[-2]=kk-tan*h1;cc2[1]=kk+tan*h2
        cc1[1,2]+=rng.uniform(-3,3);cc2[2,2]+=rng.uniform(-3,3)
        counts['tried']+=1
        if min(radius_at_samples(cc1),radius_at_samples(cc2))<R+.02:
            counts['curvature_reject']+=1;continue
        curve=np.vstack([bezier(cc1,np.linspace(0,1,181)),bezier(cc2,np.linspace(0,1,181))[1:]])
        n,p=check_points(resample(curve,.24))
        if n:counts['space_reject']+=1;blockers[n]+=1;continue
        r1,q1=extrema_radius(cc1);r2,q2=extrema_radius(cc2)
        if min(r1,r2)<R+.02:counts['extrema_reject']+=1;continue
        full=np.vstack([row['curve_mm'][0],curve,row['curve_mm'][-1]])
        new=dict(row,curve_mm=full.tolist(),cubic_controls_mm=[cc1.tolist(),cc2.tolist()],
            minimum_curvature_radius_mm=min(r1,r2),curvature_extrema_parameters=[q1,q2],
            geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),
            refinement='Bounded local controls around corrected assembly-safe single-curve seeds')
        pool.append(new)
        if len(pool)>=240:break
    pools[str(pin)]=pool;search.append(dict(pin=pin,seeds=len(seeds),candidates=len(pool),**counts,blockers=dict(blockers)))
    print('REFINE_IMU_POOL',search[-1],time.time()-start,flush=True)
    (STAGE/'imu_refined_progress.json').write_text(json.dumps(search,indent=2)+'\n')
out=dict(source_blend_sha256=source_hash,source_six_wire_sha256=datasets[0]['source_six_wire_sha256'],
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
    status='PASS' if all(pools.values()) else 'BLOCKED',scope='Static single-curve pool; refined candidates require full assembly recheck',
    pools=pools,search=search,elapsed_s=time.time()-start,main_modified=False,extra_print_holes=False)
(STAGE/'imu_refined_pools.json').write_text(json.dumps(out,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
