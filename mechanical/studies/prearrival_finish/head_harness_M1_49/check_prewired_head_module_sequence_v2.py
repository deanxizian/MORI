"""Screen lifting the complete head/bridge with the body upper shell.

No cable shape or grip is represented; this only checks whether the rigid
parts permit a different order than raising the shell around a seated head.
"""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';OUT=BASE/'cam_restraints/head_module_sequence_v2'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import D
from mathutils import Matrix,Vector
ctx=Context();started=time.time()
file=ROOT/'mechanical/reports/assembly_issue_validation.json'
upper=set(json.loads(file.read_text())['body_service']['upper_shell']['moving'])
head={n for n,s in ctx.ss.items() if s.group in ['yaw','pitch']}
bridge={n for n in ctx.ss if n.startswith('Yaw_')}
removed={n for n in bridge if n in ['Yaw_Base_-1_Screw','Yaw_Base_1_Screw']}
bridge-=removed;module=head|bridge
# Lower shell and body attachment screws are fitted after this stage.
removed|={'Body_Lower'}|{n for n in ctx.ss if n.startswith(('Frame_Screw_','Shell_Screw_'))}
assert not (module&upper)
fixture=set(ctx.ss)-module-upper-removed
origin=Vector((0,0,D['body_z']))
def shellpose(angle,y,z):
    return Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-origin)
def transformed(names,tr):return {n:ctx.ss[n].m.transform(np.asarray(tr)[:3,:]) for n in names}
def collisions(m,targets):
    bb=np.asarray(m.bounding_box());hits=[]
    for n,t in targets.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
        v=float((m^t).volume())
        if abs(v)>1e-5:hits.append(dict(target=n,volume_mm3=v))
    return hits
fixed={n:ctx.ss[n].m for n in fixture};rows=[];endpoint_rows=[]
for lift in [18.,18.5,19.,19.5,20.,21.,22.,24.]:
    u=transformed(upper,shellpose(15,0,14));h=transformed(module,Matrix.Translation((0,0,lift)));hits=[]
    for n,m in u.items():hits.extend(dict(moving=n,**v) for v in collisions(m,fixed|h))
    for n,m in h.items():hits.extend(dict(moving=n,**v) for v in collisions(m,fixed))
    endpoint_rows.append(dict(lift_mm=lift,status='BLOCKED' if hits else 'PASS',hits=hits))
    print('HEAD_MODULE_ENDPOINT',lift,'BLOCKED' if hits else 'PASS',hits[:2],flush=True)
passed=[r['lift_mm'] for r in endpoint_rows if r['status']=='PASS']
selected=passed[0] if passed else 18.

paths=[('lift_together',[(shellpose(15*u,0,14*u),Matrix.Translation((0,0,selected*u))) for u in np.linspace(0,1,73)]),
       ('back14',[(shellpose(15,y,14),Matrix.Translation((0,y,selected))) for y in np.linspace(0,-14,57)]),
       ('up140',[(shellpose(15,-14,z),Matrix.Translation((0,-14,z+selected-14))) for z in np.arange(14,140.01,.5)])]
for label,poses in paths:
    failure=None;checked=0
    for i,(su,hm) in enumerate(poses):
        u=transformed(upper,su);h=transformed(module,hm);hits=[];checked+=1
        for n,m in u.items():hits.extend(dict(moving=n,**v) for v in collisions(m,fixed|h))
        for n,m in h.items():hits.extend(dict(moving=n,**v) for v in collisions(m,fixed))
        if hits:
            failure=dict(sample=i,shell_matrix=np.asarray(su).tolist(),head_matrix=np.asarray(hm).tolist(),hits=hits)
            break
    r=dict(stage=label,status='BLOCKED' if failure else 'PASS',planned_samples=len(poses),checked_samples=checked,first_failure=failure)
    rows.append(r);print('PREWIRED_HEAD_MODULE_STAGE',json.dumps(r),flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if all(x['status']=='PASS' for x in rows) else 'BLOCKED',
    scope='Sampled rigid head plus bridge and independently tilted body upper shell; no flexible wires or human access',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [file,ROOT/'mechanical/reports/head_retention_body_sequence.json']},
    endpoint_rows=endpoint_rows,selected_head_lift_mm=selected,
    correction='All yaw hardware including output/horn/lock screw follows the bridge; lower shell and its attachment screws are not yet installed',
    moving_head_module=sorted(module),moving_upper_module=sorted(upper),removed_before_motion=sorted(removed),fixed_native=sorted(fixture),rows=rows,
    flexible_wires='NOT_TESTED',grip_and_support='NOT_TESTED',fastening_access='NOT_TESTED',SCS0009_interface='BLOCKED',
    main_changed=False,approved=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('PREWIRED_HEAD_MODULE_DONE',r['status'],r['elapsed_s'],flush=True)
