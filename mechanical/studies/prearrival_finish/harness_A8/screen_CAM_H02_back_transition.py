"""Continue the verified six-wire lift into the 14 mm rearward bridge move."""
from pathlib import Path
BACK_SCRIPT=Path(__file__).resolve()
BACK_HELPER=BACK_SCRIPT.parent/'screen_CAM_feed_lift_transition.py'
__file__=str(BACK_HELPER)
exec(compile(BACK_HELPER.read_text().split('\nfor pin in range(1,5):',1)[0],str(BACK_HELPER),'exec'),globals())
__file__=str(BACK_SCRIPT)
JOINT=ORDER_OUT/'CAM_H02_joint_lift'
joint_path=JOINT/'screen.json';joint_check_path=JOINT/'verification.json'
joint=json.loads(joint_path.read_text());joint_check=json.loads(joint_check_path.read_text())
assert joint['status']==joint_check['status']=='PASS'
assert joint_check['source_screen_sha256']==sha(joint_path)
assert joint_check['wire_solids_sha256']==sha(JOINT/'wire_solids.json')
for d in [joint,joint_check]:
    for p,h in d['source_files'].items():assert sha(PROJECT/p)==h
for name,raw in json.loads((JOINT/'wire_solids.json').read_text()).items():
    m=manifold.Manifold(manifold.Mesh64(np.asarray(raw['vertices_mm']),np.asarray(raw['triangles'],dtype=np.uint64)))
    v=np.asarray(raw['vertices_mm']);f=np.asarray(raw['triangles'])
    target_data['fixed_wire_'+name]=(m,v.min(0),v.max(0),BVHTree.FromPolygons(v,f.tolist(),all_triangles=True))
start_curves=np.load(JOINT/'curves.npz')
starts={c['pin']:c['endpoint_parameters'] for c in joint['selected']['cam']}
end_path=ORDER_OUT/'feed_pose_packing/rear14_lift18/screen.json'
end=json.loads(end_path.read_text())
assert end['status']=='PASS' and end['script_sha256']==sha(BACK_SCRIPT.parent/'screen_CAM_feed_pose_packing.py')
for p,h in end['source_files'].items():assert sha(PROJECT/p)==h
OUT=ORDER_OUT/'CAM_H02_back_transition';OUT.mkdir(exist_ok=True)
STEPS=57;u_values=np.linspace(0.,1.,STEPS)


def check_back(pin,endpoint):
    global bt,matrices
    start=starts[pin];finish=endpoint['parameters']
    assert start['family']==finish['family']
    poses=[];failure=None;previous=None;maximum_motion=0.;max_length_error=0.
    for index,u in enumerate(u_values):
        bt=trans(y=-14.*float(u),z=18.)
        st=shellpose(15.,-14.*float(u),14.)
        matrices=dict(core=I,upper=np.linalg.inv(st),bridge=np.linalg.inv(bt))
        p={key:float((1-u)*start[key]+u*finish[key]) for key in ['entry_azimuth_deg','planar_radius_mm','elevation_fraction']}
        curve,failure=variant_curve(pin,p['entry_azimuth_deg'],p['planar_radius_mm'],start['family'],p['elevation_fraction'])
        if failure:break
        if index==0:assert np.array_equal(curve['points'],start_curves[f'pin{pin}_pose36'])
        curve['candidate_id']=f"{endpoint['candidate_id']}_back{index}"
        samples=material_samples(curve);angles=np.asarray(curve['planar_angles_rad'])
        if previous:
            jump=float(np.max(np.abs(angles-previous['angles'])))
            displacement=float(np.linalg.norm(samples-previous['samples'],axis=1).max())
            maximum_motion=max(maximum_motion,displacement)
            if jump>math.pi:
                failure=dict(kind='arc_branch_jump',maximum_angle_change_rad=jump,material_sample_displacement_mm=displacement)
                break
        previous=dict(angles=angles,samples=samples)
        max_length_error=max(max_length_error,abs(curve['sampled_total_mm']-curve['analytic_total_mm']))
        lengths[pin-1]['curve_chord_error_mm']=curve['curve_chord_error_mm']
        failure=wire_check(pin,curve['points'],matrices) or self_check(curve)
        if failure:break
        failure=rigid_check(make_terminal(curve,bt),matrices)
        if failure:break
        poses.append(curve)
    record=dict(candidate_id=endpoint['candidate_id'],pin=pin,status='BLOCKED' if failure else 'PASS',
                starting_parameters=start,endpoint_parameters=finish,passing_positions=len(poses),
                planned_positions=STEPS,first_failure_index=len(poses) if failure else None,failure=failure,
                exact_previous_stage_boundary_match=True,
                maximum_sampled_material_motion_mm=maximum_motion,maximum_polyline_length_error_mm=max_length_error)
    if not failure:curve_cache[endpoint['candidate_id']]=poses
    return record


results=[];pools={}
for pin in range(1,5):
    candidates=[c for c in end['pools'][str(pin)] if c['parameters']['family']==starts[pin]['family']]
    rows=[check_back(pin,c) for c in candidates]
    results.extend(rows);pools[pin]=[r for r in rows if r['status']=='PASS']
    print('CAM_H02_BACK_PIN',pin,len(pools[pin]),'of',len(candidates),
          [r['failure'] for r in rows[:2] if r['failure']],round(time.time()-started,2),flush=True)
packing=BACK_HELPER.read_text().split('\npair_cache = {}',1)[1].split('\nreport=dict(',1)[0]
old='bridge_transform = trans(z=18.*float(u_values[index]))'
assert packing.count(old)==1
packing=packing.replace(old,'bridge_transform = trans(y=-14.*float(u_values[index]),z=18.)')
exec(compile('pair_cache = {}'+packing,str(BACK_HELPER),'exec'),globals())
report=dict(status='PASS' if chosen else 'BLOCKED',
            scope='Finite rearward continuation of the saved six-wire lift, not full assembly',
            script_sha256=sha(BACK_SCRIPT),helper_sha256=sha(BACK_HELPER),
            source_files={**joint['source_files'],str(joint_path.relative_to(PROJECT)):sha(joint_path),
                          str(joint_check_path.relative_to(PROJECT)):sha(joint_check_path),
                          str((JOINT/'curves.npz').relative_to(PROJECT)):sha(JOINT/'curves.npz'),
                          str((JOINT/'wire_solids.json').relative_to(PROJECT)):sha(JOINT/'wire_solids.json'),
                          str(end_path.relative_to(PROJECT)):sha(end_path)},
            source_main_sha256=source_hash,protected_sources=protected,
            source_prints=membership['substituted_unadopted_prints'],
            planned_positions=STEPS,rearward_travel_mm=14.,sample_spacing_mm=.25,
            fixed_body_wires=14,CAM_wires=4,results=results,selected=chosen,selected_pairs=selected_rows,
            pair_diagnostics=[dict(a=k[0],b=k[1],**v) for k,v in pair_cache.items()],
            curves_sha256=sha(OUT/'curves.npz'),search_nodes=search_nodes,
            exact_previous_stage_boundary_match=True,analytic_full_length_conserved=True,
            continuous_motion='NOT_TESTED',later_bench_and_head_stages='NOT_TESTED',
            hands_and_actual_terminals='NOT_TESTED',main_applied=False,
            whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_H02_BACK_DONE',report['status'],None if not chosen else [c['candidate_id'] for c in chosen],
      round(time.time()-started,2),flush=True)
