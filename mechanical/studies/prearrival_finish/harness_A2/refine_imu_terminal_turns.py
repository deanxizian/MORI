# -*- coding: utf-8 -*-
"""Target the diagnosed pin1/2 convergence without changing any solid or datum.

Only one terminal cubic's axial control distance is varied per run. The
native exit, five-millimetre straight and tangent-continuous join remain.
These are independent study curves, not an adopted harness or cut lengths.
"""
from pathlib import Path
import json,hashlib,time,collections
STAGE=Path(__file__).resolve().parent
code=(STAGE/'imu_individual_routes.py').read_text().split('choices=[')[0]
exec(compile(code,str(STAGE/'imu_individual_routes.py'),'exec'),globals())
UPPER='--upper' in sys.argv
input_file=STAGE/('imu_targeted_assembly_pools.json' if UPPER else 'imu_refined_assembly_pools.json')
diagnostic_file=STAGE/('imu_targeted_assembly_joint_diagnostic.json' if UPPER else 'imu_refined_assembly_joint_diagnostic.json')
data=json.loads(input_file.read_text())
diag=json.loads(diagnostic_file.read_text())
pair=next(r for r in diag['pair_diagnostics'] if set(r['pins'])=={'1','2'})
selected={str(p):i for p,i in pair['candidates']}
pools={};search=[];start=time.time()
for pin in ['1','2']:
    row=data['pools'][pin][selected[pin]]
    c1,c2=map(np.asarray,row['cubic_controls_mm'])
    direction=c1[1]-c1[0] if UPPER else c2[2]-c2[3]
    nominal=np.linalg.norm(direction);direction/=nominal
    pool=[];counts=collections.Counter();blockers=collections.Counter()
    for shift in np.arange(-5.,12.01,.25):
        if abs(shift)<.001:continue
        counts['tried']+=1
        cc1=c1.copy();cc2=c2.copy()
        if UPPER:cc1[1]=cc1[0]+direction*(nominal+shift)
        else:cc2[2]=cc2[3]+direction*(nominal+shift)
        if min(radius_at_samples(cc1),radius_at_samples(cc2))<R+.02:
            counts['curvature_reject']+=1;continue
        curve=np.vstack([bezier(cc1,np.linspace(0,1,181)),bezier(cc2,np.linspace(0,1,181))[1:]])
        name,where=check_points(resample(curve,.24))
        if name:
            counts['space_reject']+=1;blockers[name]+=1;continue
        r1,q1=extrema_radius(cc1);r2,q2=extrema_radius(cc2)
        if min(r1,r2)<R+.02:
            counts['extrema_reject']+=1;continue
        full=np.vstack([row['curve_mm'][0],curve,row['curve_mm'][-1]])
        new=dict(row,curve_mm=full.tolist(),cubic_controls_mm=[cc1.tolist(),cc2.tolist()],
            minimum_curvature_radius_mm=min(r1,r2),curvature_extrema_parameters=[q1,q2],
            geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),
            source_filtered_pool_index=selected[pin],
            refinement='Only '+('upper' if UPPER else 'lower')+' axial control distance varied around diagnosed closest pin1/2 pair')
        new['upper_terminal_control_shift_mm' if UPPER else 'terminal_control_shift_mm']=float(shift)
        pool.append(new)
    pools[pin]=pool;search.append(dict(pin=pin,candidates=len(pool),**counts,blockers=dict(blockers)))
    print('IMU_TERMINAL_REFINE',search[-1],time.time()-start,flush=True)
out=dict(source_blend_sha256=source_hash,source_six_wire_sha256=data['source_six_wire_sha256'],
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [input_file,diagnostic_file]},
    status='PASS' if all(pools.values()) else 'BLOCKED',
    scope='Only pin1/2 static curve additions; assembly screen and eight-wire selection still required',
    pools=pools,search=search,elapsed_s=time.time()-start,main_modified=False,extra_print_holes=False)
(STAGE/('imu_upper_turn_pools.json' if UPPER else 'imu_terminal_turn_pools.json')).write_text(json.dumps(out,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
