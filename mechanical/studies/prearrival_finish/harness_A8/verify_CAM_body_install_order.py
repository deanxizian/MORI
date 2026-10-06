"""Dense source-inclusive check for the CAM-first body sequence candidate."""
from pathlib import Path
DENSE_SCRIPT=Path(__file__).resolve();DENSE_HELPER=DENSE_SCRIPT.parent/'screen_CAM_body_install_order.py'
prefix=DENSE_HELPER.read_text().split('\nstarted=time.time();trials=',1)[0]
__file__=str(DENSE_HELPER);exec(compile(prefix,str(DENSE_HELPER),'exec'),globals());__file__=str(DENSE_SCRIPT)
DENSE_OUT=ORDER_OUT
stages=[
 ('bridge_lift_shell_held',[(shellpose(15,0,14),trans(z=float(z))) for z in np.arange(0,18.01,.5)]),
 ('body_bridge_back',[(shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in np.linspace(0,-14,57)]),
 ('body_bridge_bench',[(shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in np.arange(14,140.01,.5)]),
 ('body_shell_settle',[(shellpose(15*float(u),0,14*float(u)),I) for u in np.linspace(0,1,61)]),
]
started=time.time();trials=[]
for label,deferred in [('defer_H01_H02_H04',{'H01','H02','H04'}),('defer_H01_to_H04',set(pairings))]:
    absent_wires={'fixed_wire_'+n for n in fixed if n.split('_')[0] in deferred}
    absent_plugs={'Plug_'+n for group in deferred for n in pairings[group]}
    target_data={n:d for n,d in all_targets.items() if n not in absent_wires|absent_plugs}
    rows=[]
    for stage,poses in stages:
        fail=None;checked=0
        for i,(st,bt) in enumerate(poses):
            matrices={'core':bt,'upper':np.linalg.inv(st)@bt,'bridge':I}
            fail=rigid_check(housing,matrices,True)
            if not fail:
                for pin,pts in wire.items():
                    fail=wire_check(pin,pts,matrices) or rigid_check(terminals[pin],matrices)
                    if fail:break
            checked+=1
            if fail:
                fail.update(index=i,shell_transform=st.tolist(),bridge_transform=bt.tolist());break
        row=dict(stage=stage,status='BLOCKED' if fail else 'PASS',checked_positions=checked,planned_positions=len(poses),failure=fail)
        rows.append(row);print('DENSE_CAM_BODY',label,stage,row['status'],checked,round(time.time()-started,2),flush=True)
    trials.append(dict(label=label,deferred_harness_groups=sorted(deferred),deferred_wire_ids=sorted(absent_wires),
        deferred_mating_allocations=sorted(absent_plugs),status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',rows=rows))
target_data=all_targets
report=dict(status='PASS' if any(r['status']=='PASS' for r in trials) else 'BLOCKED',
    scope='408 finite stages for a CAM-first wire order; full four-wire lengths and common PH housing included; deferred harnesses must still be installed',
    script_sha256=sha(DENSE_SCRIPT),helper_sha256=sha(DENSE_HELPER),source_main_sha256=source_hash,protected_sources=protected,
    source_coarse_report_sha256=sha(ORDER_OUT/'screen.json'),source_split_report_sha256=sha(membership_path),
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],source_objects=209,present_source_objects=122,
    full_four_wire_arrays_sha256=sha(STOCK_OUT/'full_wires.npz'),nominal_CAM_lengths_mm=[r['full_nominal_allocation_mm'] for r in lengths],
    wire_OD_mm=OD,wire_clearance_allocation_mm=MARGIN,source_chord_bounds_mm=[r['curve_chord_error_mm'] for r in lengths],
    trials=trials,continuous_motion='NOT_TESTED',CAM_plug_axial_mating='ASSUMED_ORIGINAL_DOMAIN_ONLY',
    deferred_wire_installation='NOT_TESTED',later_yaw_installation_over_stock='NOT_TESTED',tools_and_hands='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(DENSE_OUT/'dense.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/n)==h for n,h in protected.items())
print('DENSE_CAM_BODY_DONE',report['status'],round(time.time()-started,2),flush=True)
