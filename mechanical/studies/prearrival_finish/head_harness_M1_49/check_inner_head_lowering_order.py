"""Nominal inner-head placement after body bridge/upper shell installation.

Compare a preinstalled reaction link with a link travelling with the head.
No flexible wires or undocumented SCS0009 mating details are qualified.
"""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'inner_head_lowering'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
accessfile=REST/'keeper_alternating_yaw/review.json';access=read(accessfile);assert access['status']=='PASS'
for f,h in {**access['sources'],**access['inputs']}.items():assert sha(ROOT/f)==h,f
inputs=[accessfile];absent=set(access['absent_in_inner_head_stage'])|{'Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1'}
geometry={n:s.m for n,s in ctx.ss.items()};groups={n:s.group for n,s in ctx.ss.items()}
for n,p,group in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz','body'),
                  ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz','yaw'),
                  ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz','pitch'),
                  ('connector_band',REST/'return_clamp_v3/band.npz','pitch'),('connector_head',REST/'return_clamp_v3/head.npz','pitch')]:
    inputs.append(p);a=np.load(p);geometry[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)));groups[n]=group
body_extra={n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))}
head={n for n,g in groups.items() if g in ['yaw','pitch'] and n not in absent}
link={'Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Lock_Screw'}
base_moving=head|{'Yaw_Output','Yaw_Anti_Lift_Keeper'}
rows=[]
for label,moving,deferred in [('reaction_link_preinstalled',base_moving,absent|{'Yaw_Lock_Screw'}),
                               ('reaction_link_with_head',base_moving|link,absent|{'Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut'})]:
    fixed={n:m for n,m in geometry.items() if n not in moving|deferred};fixed.update(body_extra)
    fixed_boxes={n:np.asarray(m.bounding_box()) for n,m in fixed.items()}
    mm={n:geometry[n] for n in moving};mb={n:np.asarray(m.bounding_box()) for n,m in mm.items()};first=None;count=0
    for dz in np.arange(0,90.01,.5):
        shift=np.array([0.,0,float(dz)]);hits=[];count+=1
        for n,m in mm.items():
            box=mb[n]+np.r_[shift,shift];posed=None
            for name,t in fixed.items():
                tb=fixed_boxes[name]
                if np.any(box[3:]<tb[:3]) or np.any(tb[3:]<box[:3]):continue
                if posed is None:posed=m.translate(shift.tolist())
                v=float((posed^t).volume())
                if abs(v)>1e-5:hits.append(dict(moving=n,fixed=name,overlap_mm3=v))
        if hits:
            first=dict(lift_mm=float(dz),hits=hits);break
    row=dict(case=label,status='BLOCKED' if first else 'PASS',moving=sorted(moving),not_yet_installed=sorted(deferred),
             fixed=sorted(fixed),planned_samples=181,checked_samples=count,first_failure=first,
             journal_min_z_mm=mb['Pitch_Yoke'][2],reaction_link_min_z_mm=geometry['Yaw_Reaction_Link'].bounding_box()[2])
    rows.append(row);print('INNER_HEAD_LOWERING_CASE',label,row['status'],count,first,flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if any(x['status']=='PASS' for x in rows) else 'BLOCKED',
       scope='Finite nominal rigid insertion comparison after bridge and upper body shell are fixed, no full wire deformation',
       sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
       lower_insertion_direction='Reverse of recorded 0..90mm upward withdrawal, world +Z',
       actual_transmission_stack='BLOCKED',reaction_screw_access='NOT_TESTED',
       flexible_wire_shapes='NOT_TESTED',wire_length_control='NOT_TESTED',continuous_rigid_clearance='NOT_TESTED',
       main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('INNER_HEAD_LOWERING_DONE',r['status'],r['elapsed_s'],flush=True)
