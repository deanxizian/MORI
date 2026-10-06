"""Regenerate H02 solids and check the joint six-wire finite lift candidate."""
from pathlib import Path
VERIFY_SCRIPT=Path(__file__).resolve();A8=VERIFY_SCRIPT.parent
BOOT=A8/'screen_H02_preinstalled_route.py'
__file__=str(BOOT)
exec(compile(BOOT.read_text().split('\nstarted=time.time();pools=',1)[0],str(BOOT),'exec'),globals())
__file__=str(VERIFY_SCRIPT)
from interface_completion import axial
from validate import rigidtr
OUT=ORDER_OUT/'CAM_H02_joint_lift'
screen_path=OUT/'screen.json';saved=json.loads(screen_path.read_text())
assert saved['status']=='PASS' and saved['script_sha256']==sha(A8/'screen_CAM_H02_lift_copacking.py')
assert saved['curves_sha256']==sha(OUT/'curves.npz')
for p,h in saved['source_files'].items():assert sha(PROJECT/p)==h,p
chosen=saved['selected'];selected=chosen['h02']
assert len(selected)==2

# Same independent capsule construction and static checks as the received H02
# candidate; write the new shapes only within this study's own directory.
prior_verify=A8/'verify_H02_preinstalled_route.py'
construction=prior_verify.read_text().split('\nstarted=time.time();solids=',1)[1].split('\nstages=[',1)[0]
construction='started=time.time();solids='+construction
exec(compile(construction,str(prior_verify),'exec'),globals())
for row in selected:
    source=next(r for r in source_routes if r['id']==row['id'])
    assert row['curve_mm'][0]==source['curve_mm'][0]
    assert row['curve_mm'][-1]==source['curve_mm'][-1]
    assert row['from_port']==source['from_port'] and row['to_port']==source['to_port']
    rebuilt=rounded(np.asarray(row['controls_mm']),R)
    rebuilt=np.vstack([row['curve_mm'][0],rebuilt,row['curve_mm'][-1]])
    assert np.array_equal(rebuilt,np.asarray(row['curve_mm']))
assert selected[0]['id']=='H02_1' and selected[1]['id']=='H02_2'

# All 14 body wires are now present. The PH housing stays at its native body
# end, unlike the older rigid-harness installation study.
target_data=dict(all_targets)
target_data.update({'fixed_wire_'+name:data(m) for name,m in solids.items()})
full_curves=np.load(OUT/'curves.npz')
fixed_shell=np.asarray(saved['shell_transform'])
lift_rows=[]
for index,z in enumerate(np.arange(0,18.01,.5)):
    bt=trans(z=float(z));matrices=dict(core=I,upper=np.linalg.inv(fixed_shell),bridge=np.linalg.inv(bt))
    failure=rigid_check(housing,matrices,True)
    for pin in range(1,5):
        if failure:break
        points=full_curves[f'pin{pin}_pose{index}']
        # The upstream construction retains the source chord bound and all
        # newly generated arcs are tighter than this conservative allocation.
        lengths[pin-1]['curve_chord_error_mm']=.0003
        failure=wire_check(pin,points,matrices)
    lift_rows.append(dict(index=index,bridge_z_mm=float(z),status='PASS' if not failure else 'FAIL',failure=failure))
    if failure:break
print('JOINT_LIFT_SAVED_SOLIDS',lift_rows[-1],round(time.time()-started,2),flush=True)

# Recheck H02 against every rigid shell/bridge pose (no claim that the CAM
# configuration already connects those later poses).
rigid_stages=[
 ('lift',[(fixed_shell,trans(z=float(z))) for z in np.arange(0,18.01,.5)]),
 ('back',[(shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in np.linspace(0,-14,57)]),
 ('bench',[(shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in np.arange(14,140.01,.5)]),
 ('shell',[(shellpose(15*float(u),0,14*float(u)),I) for u in np.linspace(0,1,61)]),
]
upper_targets={n:data(phys[n]) for n in upper}
upper_targets.update({'Plug_'+n:data(s.m) for n,s in plug.items() if n.startswith('rear_')})
bridge_targets={n:data(phys[n]) for n in bridge}
rigid_rows=[]
for label,poses in rigid_stages:
    failure=None;checked_positions=0
    for index,(st,bt) in enumerate(poses):
        for row in selected:
            points=resample(row['curve_mm'],.04)
            for group,T,targets in [('upper',st,upper_targets),('bridge',bt,bridge_targets)]:
                q=transform_points(points,np.linalg.inv(T))
                failure=check_curve(q,targets,rad=HOD/2+.02,extra=0.)
                if failure:failure.update(wire=row['id'],group=group);break
            if failure:break
        checked_positions+=1
        if failure:break
    rigid_rows.append(dict(stage=label,status='PASS' if not failure else 'FAIL',
                           planned_positions=len(poses),checked_positions=checked_positions,failure=failure))
    print('JOINT_H02_RIGID',label,rigid_rows[-1]['status'],checked_positions,flush=True)

head_failures=[]
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        for name,s in ss.items():
            if s.group not in ['yaw','pitch']:continue
            T=np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))
            m=phys[name].transform(T[:3,:4]);box=np.asarray(m.bounding_box())
            for wid,w in solids.items():
                b=np.asarray(w.bounding_box())
                if np.any(b[:3]>=box[3:]) or np.any(b[3:]<=box[:3]):continue
                volume=max(0.,float((w^m).volume()))
                if volume>1e-5:head_failures.append(dict(wire=wid,object=name,yaw=yaw,pitch=pitch,intersection_mm3=volume))
print('JOINT_H02_HEAD',len(head_failures),'overlaps',flush=True)

# Explicit open-body insertion, before bridge, CAM, H01 and H04. The actual
# nominal H02 wires and both source plug allocations move together.
insert_shapes={**solids,**{'Plug_'+n:plug[n].m for n in ['motion_J2','power_J13']}}
insert_targets={n:data(phys[n]) for n in core}
not_installed={'motion_J5'}|{p for g in ['H01','H02','H04'] for p in pairings[g]}
insert_targets.update({'Plug_'+n:data(s.m) for n,s in plug.items() if n not in not_installed and not n.startswith('rear_')})
insert_targets.update({'fixed_wire_'+n:(r['m'],r['lo'],r['hi'],r['tree']) for n,r in fixed.items() if n.startswith('H03_')})
own_boards={'Plug_motion_J2':'MCU_Carrier','Plug_power_J13':'Power_Module'}
domains={n:insert_shapes[n]^insert_targets[b][0] for n,b in own_boards.items()}
insert_rows=[]
for z in np.arange(0,100.01,.5):
    failure=None
    for name,shape in insert_shapes.items():
        placed=shape.translate([0,0,float(z)]);box=np.asarray(placed.bounding_box())
        for other,(m,lo,hi,_) in insert_targets.items():
            if np.any(box[:3]>=hi) or np.any(box[3:]<=lo):continue
            overlap=placed^m
            if own_boards.get(name)==other:overlap-=domains[name]
            volume=max(0.,float(overlap.volume()))
            if volume>1e-5:failure=dict(moving=name,obstacle=other,intersection_mm3=volume);break
        if failure:break
    if not failure:
        for row in selected:
            p=resample(row['curve_mm'],.04)+[0,0,float(z)]
            failure=check_curve(p,insert_targets,rad=HOD/2+.02,extra=0.)
            if failure:failure.update(wire=row['id']);break
    insert_rows.append(dict(z_mm=float(z),status='PASS' if not failure else 'FAIL',failure=failure))
    if failure:break
print('JOINT_H02_OPEN_DECK',insert_rows[-1],len(insert_rows),flush=True)
all_rows=static_rows+rigid_rows+lift_rows+insert_rows+[pair_row]
status='PASS' if all(r['status']=='PASS' for r in all_rows) and len(lift_rows)==37 and len(insert_rows)==201 and not head_failures else 'FAIL'
report=dict(status=status,scope='Regenerated H02 solids, 37 joint CAM lift positions, H02 rigid-motion and open-body insertion only',
            script_sha256=sha(VERIFY_SCRIPT),source_screen_sha256=sha(screen_path),
            protected_sources=protected,source_main_sha256=source_hash,
            source_files={str(p.relative_to(PROJECT)):sha(p) for p in [BOOT,prior_verify,A2/'ecowire_joint.json',fixed_path,screen_path,OUT/'curves.npz']},
            wire_solids_sha256=sha(OUT/'wire_solids.json'),source_prints=saved['source_prints'],
            native_endpoints_unchanged=True,static_source_objects=209,mating_allocations=len(plug),
            solids=solid_rows,static=static_rows,h02_pair=pair_row,joint_lift=lift_rows,
            joint_lift_body_wires=14,rigid_stages=rigid_rows,head_poses=130,head_solid_intersections=head_failures,
            open_deck_insertion=insert_rows,open_deck_before=['CAM','H01','H04','bridge','upper_shell'],
            nominal_h02_lengths_mm=[r['analytic_length_mm'] for r in selected],supplier_cut_lengths=None,
            actual_terminals_and_plug_fit='NOT_TESTED',continuous_motion='NOT_TESTED',
            hands_and_shape_support='NOT_TESTED',remaining_CAM_back_and_bench='NOT_TESTED',
            main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
            blender_version=bpy.app.version_string,elapsed_s=time.time()-started)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_H02_JOINT_VERIFIED',status,round(time.time()-started,2),flush=True)
