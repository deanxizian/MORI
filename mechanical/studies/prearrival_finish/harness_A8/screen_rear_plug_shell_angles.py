"""Compare shell holding angles with unchanged conservative rear plugs.

Test actual rigid groups before expensive wire checks. A new pose is never
accepted solely because its endpoints clear; its incoming release is included.
"""
from pathlib import Path
ANGLE_SCRIPT=Path(__file__).resolve()
ANGLE_HELPER=ANGLE_SCRIPT.parent/'screen_CAM_H02_shell_schedule.py'
__file__=str(ANGLE_HELPER)
exec(compile(ANGLE_HELPER.read_text().split('\nfor held_y in ',1)[0],str(ANGLE_HELPER),'exec'),globals())
__file__=str(ANGLE_SCRIPT)
OUT=ORDER_OUT/'rear_plug_shell_angles';OUT.mkdir(exist_ok=True)
rigid_records=[];candidates=[];rigid_cache={};wire_results=[];final_choice=None;final_curves={}


def pose_rigid(p):
    key=tuple(round(p[k],8) for k in ['a','y','sz','bz'])
    if key in rigid_cache:return rigid_cache[key]
    bt=trans(z=p['bz']);st=shellpose(p['a'],p['y'],p['sz'])
    up=placed(upper_rigid,st);bp=placed(bridge_rigid,bt)
    failure=collisions(up,fixed_placed) or collisions(bp,fixed_placed) or collisions(up,bp)
    rigid_cache[key]=failure
    return failure


def stages_for(angle,height,rear):
    zero=shellpose(angle,-14.,0.)
    upper_low=min(m.transform(zero[:3,:4]).bounding_box()[2] for m in upper_rigid.values())
    needed=max(18.,body_max_z+1.-upper_low-height+18.,body_max_z+1.-bridge_min_z)
    end=math.ceil(needed*2)/2
    assert end<=144.
    return [
      ('shell_release',[dict(a=angle*float(u),y=rear*float(u),sz=height*float(u),bz=0.,lift_index=0)
                        for u in np.linspace(0,1,61)]),
      ('bridge_lift',[dict(a=angle,y=rear,sz=height,bz=float(z),lift_index=i)
                      for i,z in enumerate(np.arange(0,18.01,.5))]),
      ('shell_back_bridge_held',[dict(a=angle,y=float(y),sz=height,bz=18.,lift_index=36)
                                for y in np.linspace(rear,-14.,int(math.ceil(abs(-14.-rear)/.25))+1)]),
      ('vertical_separated_shell',[dict(a=angle,y=-14.,sz=height+float(z)-18.,bz=float(z))
                                   for z in np.arange(18.,end+.01,.5)]),
    ]


# Finite design comparisons, not an exhaustive feasibility proof. Prioritize
# a modest angle change before more lift, which raises the rear plug toward
# the deck. No package dimensions or primary geometry are changed.
for angle,height,rear in itertools.product([16.,18.,20.,22.,25.,30.],[14.,15.,16.,18.],[0.,-2.,-7.,-14.]):
    phases=stages_for(angle,height,rear);failure=None;stages=[]
    for label,poses in phases:
        for index,p in enumerate(poses):
            failure=pose_rigid(p)
            if failure:break
        stages.append(dict(stage=label,planned_positions=len(poses),checked_positions=index+1,
                           status='BLOCKED' if failure else 'PASS',failure=failure,
                           last_pose=poses[index]))
        if failure:break
    row=dict(angle_deg=angle,height_mm=height,held_y_mm=rear,status='BLOCKED' if failure else 'PASS',stages=stages)
    rigid_records.append(row)
    if not failure:
        candidates.append((row,phases))
        print('REAR_PLUG_RIGID_CANDIDATE',angle,height,rear,round(time.time()-started,2),flush=True)
        if len(candidates)>=4:break
    if len(rigid_records)%24==0:print('REAR_PLUG_RIGID_PROGRESS',len(rigid_records),len(candidates),round(time.time()-started,2),flush=True)
for info,phases in candidates:
    saved={};rows=[];stages=[];failure=None
    for label,poses in phases:
        first=len(rows)
        for index,p in enumerate(poses):
            failure,curves,pairs=check_pose(label,index,p)
            rows.append(dict(stage=label,index=index,pose=p,status='BLOCKED' if failure else 'PASS',failure=failure,pairs=pairs))
            for pin,c in curves.items():saved[f'{label}_pin{pin}_pose{index}']=c['points']
            if failure:break
        stages.append(dict(stage=label,planned_positions=len(poses),checked_positions=len(rows)-first,
                           status='BLOCKED' if failure else 'PASS',failure=failure))
        if failure:break
    result=dict(angle_deg=info['angle_deg'],height_mm=info['height_mm'],held_y_mm=info['held_y_mm'],
                status='BLOCKED' if failure else 'PASS',stages=stages,rows=rows)
    wire_results.append(result)
    print('REAR_PLUG_WIRE_RESULT',result['angle_deg'],result['height_mm'],result['held_y_mm'],result['status'],stages[-1],flush=True)
    if not failure:
        final_choice=result;final_curves=saved;break
np.savez_compressed(OUT/'curves.npz',**final_curves)
report=dict(status='PASS' if final_choice else 'BLOCKED',
    scope='Finite shell path with unchanged conservative plug envelopes, fixed body wires and saved CAM/H02 lift',
    script_sha256=sha(ANGLE_SCRIPT),helper_sha256=sha(ANGLE_HELPER),
    source_files={**joint['source_files'],str(joint_path.relative_to(PROJECT)):sha(joint_path),
                  str(joint_check_path.relative_to(PROJECT)):sha(joint_check_path),
                  str((JOINT/'curves.npz').relative_to(PROJECT)):sha(JOINT/'curves.npz'),
                  str((JOINT/'wire_solids.json').relative_to(PROJECT)):sha(JOINT/'wire_solids.json')},
    source_main_sha256=source_hash,protected_sources=protected,
    source_prints=membership['substituted_unadopted_prints'],
    installed_body_plugs=sorted(body_plugs),installed_upper_plugs=sorted(upper_plugs),
    deferred_head_plugs=deferred_plugs,body_wire_count=14,
    rigid_candidates=rigid_records,rigid_clear_candidates=len(candidates),rigid_pose_cache_count=len(rigid_cache),
    wire_results=wire_results,selected=final_choice,curves_sha256=sha(OUT/'curves.npz'),
    geometry_unchanged=True,plug_envelopes_unchanged=True,
    continuous_assembly='NOT_TESTED',full_harness='BLOCKED',
    actual_parts_and_hands='NOT_TESTED',main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('REAR_PLUG_SHELL_ANGLE_DONE',report['status'],len(rigid_records),len(candidates),round(time.time()-started,2),flush=True)
