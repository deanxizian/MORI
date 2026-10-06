"""Construct continuous rigid PH approaches for later body-harness endpoints.

Pull 8 mm along each native axis, then take one straight lateral route out of
the assembled-body footprint. This checks the plug space, not attached wires.
"""
from pathlib import Path
APP_SCRIPT=Path(__file__).resolve();APP_HELPER=APP_SCRIPT.parent/'screen_CAM_later_body_connections.py'
prefix=APP_HELPER.read_text().split('\nstarted=time.time();rows=',1)[0]
__file__=str(APP_HELPER);exec(compile(prefix,str(APP_HELPER),'exec'),globals());__file__=str(APP_SCRIPT)
APP_OUT=LATER_OUT/'connector_approach';APP_OUT.mkdir(exist_ok=True)
targets=physical_targets(shellpose(15,0,14))
xy_los=np.min([lo[:2] for _,lo,hi,_ in targets.values()]+[d['points'][:,:2].min(0)-OD/2-.3 for d in cam_data.values()],axis=0)
xy_his=np.max([hi[:2] for _,lo,hi,_ in targets.values()]+[d['points'][:,:2].max(0)+OD/2+.3 for d in cam_data.values()],axis=0)
started=time.time();rows=[]
for group in sorted(deferred):
    for port in pairings[group]:
        m=plug[port].m;axis=np.asarray(port_pins[port]['axis']);lift=axis*8
        native=native_names[port.split('_')[0]];domain={(port,native):m^phys[native]}
        axial=manifold.Manifold.batch_hull([m,m.translate(lift.tolist())])
        axial_hit=check_shapes({port:axial},np.zeros(3),targets,domain)
        trials=[];selected=None
        if not axial_hit:
            for degrees in [270,90,0,180,315,225,45,135]:
                d=np.array([math.cos(math.radians(degrees)),math.sin(math.radians(degrees)),0.])
                shift=lift.copy();distance=0
                for distance in range(2,182,2):
                    shift=lift+d*distance;b=np.asarray(m.translate(shift.tolist()).bounding_box())
                    if np.any(b[:2]>xy_his+.3) or np.any(b[3:5]<xy_los-.3):break
                else:raise RuntimeError('Failed to leave horizontal obstacle bounds')
                lateral=manifold.Manifold.batch_hull([m.translate(lift.tolist()),m.translate(shift.tolist())])
                hit=check_shapes({port:lateral},np.zeros(3),targets,{})
                trial=dict(angle_deg=degrees,lateral_distance_mm=float(distance),final_translation_mm=shift.tolist(),status='BLOCKED' if hit else 'PASS',failure=hit)
                trials.append(trial)
                if not hit and selected is None:selected=trial
        row=dict(harness=group,port=port,status='PASS' if selected else 'BLOCKED',axis=axis.tolist(),
            axial_withdrawal_mm=8.,axial_sweep_status='BLOCKED' if axial_hit else 'PASS',axial_failure=axial_hit,
            lateral_trials=trials,selected=selected)
        rows.append(row);print('LATER_CONNECTOR_APPROACH',port,row['status'],selected,axial_hit,flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Continuous conservative rigid connector sweeps only, with upper shell held 15deg/14mm and CAM full material present',
    script_sha256=sha(APP_SCRIPT),helper_sha256=sha(APP_HELPER),source_main_sha256=source_hash,protected_sources=protected,
    source_objects=209,present_source_objects=122,deferred_harnesses=sorted(deferred),rows=rows,
    horizontal_exterior_bounds_mm=[xy_los.tolist(),xy_his.tolist()],sweep_method='Convex hull of both translated endpoints contains every intermediate rigid position; conservative if housing is nonconvex',
    CAM_wire_check='Nearest sampled source-curve distances with local chord and half-sample bounds against the entire swept housing',
    source_split_report_sha256=sha(membership_path),full_CAM_arrays_sha256=sha(STOCK_OUT/'full_wires.npz'),
    native_mating_overlap='Original final own-board mating volume excluded only for the initial axial segment; no exception in lateral approaches',
    attached_H01_H02_H04_wires='NOT_TESTED',tools_and_hands='NOT_TESTED',actual_connector_fit='ASSUMED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(APP_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/n)==h for n,h in protected.items())
print('LATER_CONNECTOR_APPROACH_DONE',report['status'],round(time.time()-started,2),flush=True)
