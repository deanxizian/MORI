"""Check the straight upper feed from the stored neck-exit pose.

The whole translated box is swept as one exact convex prism. Two explicitly
assumed allocations are retained; neither qualifies the actual terminal's
undimensioned projection or finished crimp. Lower loose-tail handling is open.
"""
from pathlib import Path
VF_SCRIPT=Path(__file__).resolve();VF_ROOT=VF_SCRIPT.parent
VF_HELPER=VF_ROOT/'refine_CAM_root_seating.py';__file__=str(VF_HELPER)
exec(compile(VF_HELPER.read_text().split('\nrx_rows=[];',1)[0],str(VF_HELPER),'exec'),globals())
__file__=str(VF_SCRIPT)
VF_OUT=RS_OUT/'vertical_free_feed';VF_OUT.mkdir(exist_ok=True)
vf_started=time.time();vf_target,vf_info=rs_curves(1.5)
vf_relax_file=VF_ROOT/'assembly_feed_v3/relaxation_curves.npz'
vf_relax=np.load(vf_relax_file);vf_phase=[225,135,315,45]
vf_ends=[];vf_starts=[];vf_links=[];vf_wires=[]
for slot,q in enumerate(vf_target):
    length=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum())
    start=q[0]+[0.,0.,13.];end=q[0]+[0.,0.,length]
    old=vf_relax[f'introduce_slack_10_{vf_phase[slot]}'][-1]
    delta=float(np.linalg.norm(start-old));assert delta<.00001
    vf_starts.append(start);vf_ends.append(end)
    vf_links.append(dict(slot=slot,phase_deg=vf_phase[slot],neck_last_rear_mm=old.tolist(),
        canonical_vertical_start_mm=start.tolist(),numerical_difference_mm=delta,
        comparison_limit_mm=.00001,reason='Float32 Blender rotation versus double-precision trigonometry; nominal datum match only'))
    vf_wires.append(np.linspace(q[0],end,int(math.ceil(length/.008))+1))
vf_rows=[];vf_boxes={}
for label,dims in [('old_nominal_box',np.array([.8,1.35,3.9])),
                   ('requested_space_only',np.array([1.,1.8,4.1]))]:
    for slot,(start,end) in enumerate(zip(vf_starts,vf_ends)):
        lo=start+[-dims[0]/2.,-dims[1]/2.,0.]
        hi=end+[dims[0]/2.,dims[1]/2.,dims[2]]
        sweep=box(lo,hi);failures=[];nearest={'object':None,'gap_at_least_mm':.301}
        for name,_,solid,low,high,_ in rs_targets:
            if np.any(lo>high+.301) or np.any(hi<low-.301):continue
            gap=float(sweep.min_gap(solid,.301));volume=max(0.,float((sweep^solid).volume()))
            if gap<nearest['gap_at_least_mm']:nearest={'object':name,'gap_at_least_mm':gap}
            if gap<.3 or volume>1e-7:failures.append(dict(kind='structure',object=name,gap_mm=gap,intersection_mm3=volume))
        obstacle=pw_obstacle('vertical_terminal_sweep','moving',sweep)
        for other,q in enumerate(vf_wires):
            # Own upper wire is behind the travelling terminal, not present
            # ahead of it; comparing the swept terminal with that union would
            # conflate different times. Cross-section check below covers it.
            if other!=slot:
                hit=fc_wire_check(q,0.,np.zeros(len(q)),obstacle,0.)
                if hit:failures.append(dict(kind='other_upper_wire',other=other,detail=hit))
            q=body_samples[other+1,0][0]
            hit=fc_wire_check(q,body_error,np.zeros(len(q)),obstacle,0.)
            if hit:failures.append(dict(kind='body_prefix',other=other,detail=hit))
            if other!=slot:
                b0=vf_starts[other]+[-dims[0]/2.,-dims[1]/2.,0.]
                b1=vf_ends[other]+[dims[0]/2.,dims[1]/2.,dims[2]]
                other_sweep=box(b0,b1)
                volume=max(0.,float((sweep^other_sweep).volume()))
                if volume>1e-7:failures.append(dict(kind='other_contact_sweep',other=other,intersection_mm3=volume))
        # Trailing straight wire outside the declared local 2-mm crimp
        # exclusion is always >=2 mm behind the box rear, for every position.
        own_axis_gap=2.-OD/2.
        assert own_axis_gap>.3
        row=dict(slot=slot,allocation=label,dimensions_mm=dims.tolist(),
            status='PASS' if not failures else 'BLOCKED',start_rear_mm=start.tolist(),
            end_rear_mm=end.tolist(),travel_mm=float(end[2]-start[2]),
            exact_swept_prism_bounds_mm=[lo.tolist(),hi.tolist()],
            failures=failures,nearest_structure=nearest,
            own_trailing_wire_outside_crimp_axis_gap_mm=own_axis_gap)
        vf_rows.append(row)
        print('VERTICAL_FREE_FEED',label,slot,row['status'],failures,flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in vf_rows) else 'BLOCKED',
    scope='Continuous straight translation of two stated terminal allocations above the neck; not complete loose-tail feeding',
    source_main_sha256=source_hash,script_sha256=sha(VF_SCRIPT),helper_sha256=sha(VF_HELPER),
    neck_pose_source_sha256=sha(vf_relax_file),target_seating_source_sha256=sha(RX_OUT/'verification.json'),
    neck_endpoint_links=vf_links,rows=vf_rows,wire_OD_mm=OD,ordinary_structure_margin_mm=.3,
    terminal_to_other_wire_margin_mm=0.,terminal_to_other_contact_requirement='nonpenetration',
    stage_geometry='Existing unadopted J3M/CAM study fixtures; source robot datums preserved',
    source_fixture_ids=[t[0] for t in rs_targets],uninstalled_tie_parts=sorted(rs_omitted),
    whole_interval_basis='Exact axis-aligned box translation sweep; other contacts also swept, other wires stay present',
    matched_upper_neck_endpoint='PASS',complete_neck_sequence_identity='NOT_TESTED',
    actual_terminal_profile='NOT_TESTED',body_end_slack_supply_and_hands='NOT_TESTED',
    manufactured_harness_length='BLOCKED',main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-vf_started)
(VF_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('VERTICAL_FREE_FEED_DONE',report['status'],round(time.time()-vf_started,1),flush=True)
