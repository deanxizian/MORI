"""Bounded coupled-offset/tilt bench routes on the current C5 native throat.

M1.46's old narrow throat had a failed tilt search. This checks upward coupled
routes on current M1.52 solids; initial.py checks both straight directions.
"""
from pathlib import Path
import sys,json,time,math
OUT=Path(__file__).resolve().parent;PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import P,manifold
from mathutils import Matrix
ctx=Context();started=time.time();assert P['revision']=='V1.2-M1.52'
fixture=ctx.ss['Pitch_Yoke'].m
names=['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Lock_Screw']
moving=manifold.Manifold()
for n in names:moving+=ctx.ss[n].m
max_radius=0.;checks=0

def matrix(pz,dy,angle,dz):
    p=(0,0,pz)
    return np.asarray(Matrix.Translation((0,dy,dz))@Matrix.Translation(p)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation((0,0,-pz)))[:3,:]

def check(pz,dy,angle,dz):
    global checks
    checks+=1
    posed=moving.transform(matrix(pz,dy,angle,dz));v=max(0.,float((posed^fixture).volume()))
    gap=0 if v>1e-6 else float(posed.min_gap(fixture,.5))
    return dict(pivot_z_mm=pz,offset_y_mm=dy,angle_x_deg=angle,lift_mm=dz,overlap_mm3=v,gap_mm=gap)

def path(pz,dy,angle,direction,rot_step=.5,lift_step=.5):
    rows=[];first=None
    count=max(int(math.ceil(abs(angle)/rot_step)),int(math.ceil(abs(dy)/.25)),1)
    for u in np.linspace(0,1,count+1):
        r=check(pz,float(dy*u),float(angle*u),0.);rows.append(r)
        if r['overlap_mm3']>1e-6:first=r;break
    if not first:
        for d in np.arange(lift_step,130.001,lift_step):
            r=check(pz,dy,angle,float(d*direction));rows.append(r)
            if r['overlap_mm3']>1e-6:first=r;break
    return dict(status='BLOCKED' if first else 'PASS',first_collision=first,checked_samples=len(rows),
                minimum_sampled_gap_mm=min(r['gap_mm'] for r in rows),poses=rows)

cases=[(168,2,-6,1),(168,2,-4,1),(168,2,-8,1),(168,1,-8,1),(168,3,-4,1)]
cases += [(pz,dy,angle,1) for pz in [160,168,175] for dy in [0,1,2,3]
          for angle in [-4,-6,-8,-10,4,6,8,10] if (pz,dy,angle,1) not in cases]
rows=[];selected=None
for pz,dy,angle,direction in cases:
    r=path(pz,dy,angle,direction)
    rows.append(dict(pivot_z_mm=pz,offset_y_mm=dy,angle_x_deg=angle,direction=direction,
                     **{k:v for k,v in r.items() if k!='poses'}))
    print('CURRENT_TILT',len(rows),pz,dy,angle,r['status'],r['checked_samples'],r['first_collision'],flush=True)
    if r['status']=='PASS' and r['minimum_sampled_gap_mm']>.02:
        selected=dict(parameters=rows[-1],screen_poses=r['poses']);break
ctx.assert_unchanged()
r=dict(revision=P['revision'],source_blend_sha256=ctx.source_hash,sources=ctx.sources,
       status='PASS' if selected else 'BLOCKED',scope='Finite coupled tilt/offset bench screen only; no complete assembly or continuous-path proof',
       moving=names,fixture=['Pitch_Yoke'],rows=rows,selected=selected,total_poses=checks,
       main_changed=False,C6_applied=False,actual_horn_interface='BLOCKED',full_reaction_preassembly='BLOCKED',
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'tilt_search.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CURRENT_TILT_DONE',r['status'],len(rows),checks,r['elapsed_s'],flush=True)
