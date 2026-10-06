"""Verify the modest 16-degree shell pose and compare continuation order."""
from pathlib import Path
FEED_SCRIPT=Path(__file__).resolve()
FEED_HELPER=FEED_SCRIPT.parent/'screen_rear_plug_shell_angles.py'
__file__=str(FEED_HELPER)
exec(compile(FEED_HELPER.read_text().split('\nfor angle,height,rear in ',1)[0],str(FEED_HELPER),'exec'),globals())
__file__=str(FEED_SCRIPT)
angle_report_path=ORDER_OUT/'rear_plug_shell_angles/screen.json'
angle_report=json.loads(angle_report_path.read_text())
assert angle_report['script_sha256']==sha(FEED_HELPER)
source=next(r for r in angle_report['rigid_candidates'] if r['angle_deg']==16. and r['height_mm']==14. and r['held_y_mm']==0.)
assert all(r['status']=='PASS' for r in source['stages'][:2])
OUT=ORDER_OUT/'shell16_joint_feed';OUT.mkdir(exist_ok=True)
all_rows=[];saved={};phase_rows=[]


def check_pose(label,index,pose):
    global bt,matrices
    bt=trans(y=pose.get('by',0.),z=pose['bz'])
    st=shellpose(pose['a'],pose['y'],pose['sz'])
    matrices=dict(core=I,upper=np.linalg.inv(st),bridge=np.linalg.inv(bt))
    up=placed(upper_rigid,st);bp=placed(bridge_rigid,bt)
    failure=(collisions(up,fixed_placed) or collisions(bp,fixed_placed)
             or collisions(up,bp) or rigid_check(housing,matrices,True))
    curves={};pairs=[]
    if failure:return failure,curves,pairs
    for pin,params in starts.items():
        if 'lift_index' in pose:
            assert pose.get('by',0.)==0.
            c=curve_for_lift(pin,pose['lift_index'])
        else:
            c,failure=variant_curve(pin,params['entry_azimuth_deg'],params['planar_radius_mm'],
                                    params['family'],params['elevation_fraction'])
            if failure:break
            if index==0:
                assert np.array_equal(c['points'],start_curves[f'pin{pin}_pose36'])
        lengths[pin-1]['curve_chord_error_mm']=c['curve_chord_error_mm']
        failure=(wire_check(pin,c['points'],matrices) or self_check(c)
                 or rigid_check(make_terminal(c,bt),matrices))
        if failure:break
        curves[pin]=c
    if failure is None:pairs,failure=mutual_check(curves)
    if failure is None:failure=terminal_checks(curves,bt)
    return failure,curves,pairs


def check_stage(label,poses,save_prefix=''):
    rows=[];curves_out={};previous=None;failure=None
    for index,p in enumerate(poses):
        failure,curves,pairs=check_pose(label,index,p)
        angles={pin:np.asarray(c['planar_angles_rad']) for pin,c in curves.items() if 'planar_angles_rad' in c}
        if not failure and previous:
            for pin,values in angles.items():
                if pin in previous and np.max(np.abs(values-previous[pin]))>math.pi:
                    failure=dict(kind='arc_branch_jump',pin=pin);break
        previous=angles
        rows.append(dict(index=index,pose=p,status='BLOCKED' if failure else 'PASS',failure=failure,pairs=pairs))
        for pin,c in curves.items():curves_out[f'{save_prefix}{label}_pin{pin}_pose{index}']=c['points']
        if failure:break
        if index%30==0:print('SHELL16_STAGE',label,index,round(time.time()-started,2),flush=True)
    return dict(stage=label,status='BLOCKED' if failure else 'PASS',planned_positions=len(poses),
                checked_positions=len(rows),failure=failure,rows=rows),curves_out


for label,poses in stages_for(16.,14.,0.)[:2]:
    row,curves=check_stage(label,poses);phase_rows.append(row);saved.update(curves)
    if row['status']!='PASS':break
prefix_pass=len(phase_rows)==2 and all(r['status']=='PASS' for r in phase_rows)
continuations=[]
if prefix_pass:
    shell_top=max(m.transform(shellpose(16.,0.,14.)[:3,:4]).bounding_box()[5] for m in upper_rigid.values())
    bridge_only_end=math.ceil((max(body_max_z,shell_top)+1.-bridge_min_z)*2)/2
    together_end=stages_for(16.,14.,0.)[-1][1][-1]['bz']
    continuations_spec=[
        ('bridge_only',[dict(a=16.,y=0.,sz=14.,bz=float(z))
                        for z in np.arange(18.,bridge_only_end+.01,.5)]),
        ('together_vertical',[dict(a=16.,y=0.,sz=float(z-4.),bz=float(z))
                              for z in np.arange(18.,together_end+.01,.5)]),
    ]
    # A short shared diagonal avoids relative bridge/shell shear. It is only
    # a compared partial route unless its separate vertical continuation also passes.
    for raise_mm in [2.,4.,8.,14.]:
        continuations_spec.append((f'diagonal_back14_up{raise_mm:g}',
            [dict(a=16.,y=-14.*float(u),by=-14.*float(u),sz=14.+raise_mm*float(u),bz=18.+raise_mm*float(u))
             for u in np.linspace(0,1,57)]))
    for label,poses in continuations_spec:
        row,curves=check_stage(label,poses,save_prefix='after_')
        continuations.append(row);saved.update(curves)
        print('SHELL16_CONTINUATION',label,row['status'],row['checked_positions'],row['failure'],flush=True)
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS' if prefix_pass else 'BLOCKED',
    scope='Incoming shell release and six-wire lift prefix only; continuations separately reported',
    script_sha256=sha(FEED_SCRIPT),helper_sha256=sha(FEED_HELPER),
    source_files={**joint['source_files'],str(joint_path.relative_to(PROJECT)):sha(joint_path),
                  str(joint_check_path.relative_to(PROJECT)):sha(joint_check_path),
                  str(angle_report_path.relative_to(PROJECT)):sha(angle_report_path),
                  str((JOINT/'curves.npz').relative_to(PROJECT)):sha(JOINT/'curves.npz'),
                  str((JOINT/'wire_solids.json').relative_to(PROJECT)):sha(JOINT/'wire_solids.json')},
    source_main_sha256=source_hash,protected_sources=protected,
    source_prints=membership['substituted_unadopted_prints'],
    installed_body_plugs=sorted(body_plugs),installed_upper_plugs=sorted(upper_plugs),
    body_wire_count=14,prefix_stages=phase_rows,continuation_diagnostics=continuations,
    curves_sha256=sha(OUT/'curves.npz'),full_nominal_wire_allocations_preserved=True,
    conservative_plug_envelopes_unchanged=True,continuous_assembly='NOT_TESTED',
    complete_attached_assembly='BLOCKED',physical_hands_support='NOT_TESTED',
    main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_JOINT_FEED_DONE',report['status'],round(time.time()-started,2),flush=True)
