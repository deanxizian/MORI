"""Check an earlier shell rearward offset, including its incoming motion.

This addresses a rear-J2 allocation versus load-frame collision omitted from
older rigid-shell checks. No moving plug is omitted and no part is altered.
"""
from pathlib import Path
SCHEDULE_SCRIPT=Path(__file__).resolve()
SCHEDULE_HELPER=SCHEDULE_SCRIPT.parent/'screen_CAM_H02_shell_first.py'
__file__=str(SCHEDULE_HELPER)
exec(compile(SCHEDULE_HELPER.read_text().split('\nphases = [',1)[0],str(SCHEDULE_HELPER),'exec'),globals())
__file__=str(SCHEDULE_SCRIPT)
OUT=ORDER_OUT/'CAM_H02_shell_schedule';OUT.mkdir(exist_ok=True)
candidate_rows=[];all_saved={};selected=None


def curve_for_lift(pin,index):
    p=start_curves[f'pin{pin}_pose{index}']
    return dict(pin=pin,points=p,curve_chord_error_mm=.0003,
                candidate_id=f'pin{pin}_saved_lift{index}')


def check_pose(label,index,pose):
    global bt,matrices
    bt=trans(z=pose['bz']);st=shellpose(pose['a'],pose['y'],pose['sz'])
    matrices=dict(core=I,upper=np.linalg.inv(st),bridge=np.linalg.inv(bt))
    up=placed(upper_rigid,st);bp=placed(bridge_rigid,bt)
    failure=(collisions(up,fixed_placed) or collisions(bp,fixed_placed)
             or collisions(up,bp) or rigid_check(housing,matrices,True))
    curves={};pairs=[]
    if failure:return failure,curves,pairs
    for pin,params in starts.items():
        if 'lift_index' in pose:
            c=curve_for_lift(pin,pose['lift_index'])
        else:
            c,failure=variant_curve(pin,params['entry_azimuth_deg'],params['planar_radius_mm'],
                                    params['family'],params['elevation_fraction'])
            if failure:break
        lengths[pin-1]['curve_chord_error_mm']=c['curve_chord_error_mm']
        failure=(wire_check(pin,c['points'],matrices) or self_check(c)
                 or rigid_check(make_terminal(c,bt),matrices))
        if failure:break
        curves[pin]=c
    if failure is None:pairs,failure=mutual_check(curves)
    if failure is None:failure=terminal_checks(curves,bt)
    return failure,curves,pairs


for held_y in [-.5,-1.,-2.,-4.,-7.,-14.]:
    phases=[
        ('shell_release', [dict(a=15.*float(u),y=held_y*float(u),sz=14.*float(u),bz=0.,lift_index=0)
                           for u in np.linspace(0,1,61)]),
        ('bridge_lift', [dict(a=15.,y=held_y,sz=14.,bz=float(z),lift_index=i)
                         for i,z in enumerate(np.arange(0,18.01,.5))]),
        ('shell_back_bridge_held',[dict(a=15.,y=float(y),sz=14.,bz=18.,lift_index=36)
                                   for y in np.linspace(held_y,-14.,int(math.ceil((14.+held_y)/.25))+1)]),
        ('vertical_separated_shell',[dict(a=15.,y=-14.,sz=float(z-4.),bz=float(z))
                                     for z in np.arange(18.,endpoint_z+.01,.5)]),
    ]
    rows=[];stages=[];failure=None;saved={}
    for label,poses in phases:
        first=len(rows)
        for index,pose in enumerate(poses):
            failure,curves,pairs=check_pose(label,index,pose)
            rows.append(dict(stage=label,index=index,pose=pose,status='BLOCKED' if failure else 'PASS',
                             failure=failure,pairs=pairs))
            for pin,c in curves.items():saved[f'{label}_pin{pin}_pose{index}']=c['points']
            if failure:break
        stages.append(dict(stage=label,planned_positions=len(poses),checked_positions=len(rows)-first,
                            status='BLOCKED' if failure else 'PASS',failure=failure))
        if failure:break
    row=dict(held_shell_y_mm=held_y,status='BLOCKED' if failure else 'PASS',stages=stages,rows=rows)
    candidate_rows.append(row)
    print('CAM_SHELL_SCHEDULE',held_y,row['status'],stages[-1],round(time.time()-started,2),flush=True)
    if not failure:
        selected=held_y;all_saved=saved;break
np.savez_compressed(OUT/'curves.npz',**all_saved)
report=dict(status='PASS' if selected is not None else 'BLOCKED',
            scope='Finite incoming shell release, saved six-wire lift, shell-only shift and vertical continuation',
            script_sha256=sha(SCHEDULE_SCRIPT),helper_sha256=sha(SCHEDULE_HELPER),
            source_files={**joint['source_files'],str(joint_path.relative_to(PROJECT)):sha(joint_path),
                          str(joint_check_path.relative_to(PROJECT)):sha(joint_check_path),
                          str((JOINT/'curves.npz').relative_to(PROJECT)):sha(JOINT/'curves.npz'),
                          str((JOINT/'wire_solids.json').relative_to(PROJECT)):sha(JOINT/'wire_solids.json')},
            source_main_sha256=source_hash,protected_sources=protected,
            source_prints=membership['substituted_unadopted_prints'],
            installed_body_plugs=sorted(body_plugs),installed_upper_plugs=sorted(upper_plugs),
            deferred_head_plugs=deferred_plugs,body_wires=14,
            candidates=candidate_rows,selected_held_shell_y_mm=selected,
            curves_sha256=sha(OUT/'curves.npz'),bridge_end_z_mm=endpoint_z,
            exact_saved_lift_curves_reused=True,continuous_motion='NOT_TESTED',
            full_harness='BLOCKED',actual_parts_and_hands='NOT_TESTED',
            main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_SHELL_SCHEDULE_DONE',report['status'],selected,round(time.time()-started,2),flush=True)
