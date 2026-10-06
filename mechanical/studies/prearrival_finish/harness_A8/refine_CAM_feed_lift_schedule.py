"""Refine conservative first-hit clearance rejections without changing routes."""
from pathlib import Path
REFINE_SCRIPT=Path(__file__).resolve()
REFINE_HELPER=REFINE_SCRIPT.parent/'screen_CAM_feed_lift_schedule.py'
__file__=str(REFINE_HELPER)
exec(compile(REFINE_HELPER.read_text().split('\nfor pin in range(1,4):',1)[0],str(REFINE_HELPER),'exec'),globals())
__file__=str(REFINE_SCRIPT)
schedule_path=OUT/'screen.json'
schedule=json.loads(schedule_path.read_text())
assert schedule['script_sha256']==sha(REFINE_HELPER)
assert schedule['status']=='BLOCKED'
OUT=ORDER_OUT/'feed_lift_refinement'
OUT.mkdir(exist_ok=True)
base_wire_check=wire_check
clearance_calls=[]


def densify(points,max_step=.015):
    difference=np.diff(points,axis=0)
    counts=np.maximum(1,np.ceil(np.linalg.norm(difference,axis=1)/max_step).astype(int))
    indices=np.repeat(np.arange(len(counts)),counts)
    before=np.r_[0,np.cumsum(counts)[:-1]]
    fractions=(np.arange(int(counts.sum()))-np.repeat(before,counts))/counts[indices]
    return np.vstack([points[indices]+difference[indices]*fractions[:,None],points[-1]])


def wire_check(pin,points,matrices):
    failure=base_wire_check(pin,points,matrices)
    if not failure or failure['kind']!='wire_clearance':return failure
    refined=densify(points)
    fine_failure=base_wire_check(pin,refined,matrices)
    row=dict(pin=pin,bridge_lift_mm=float(bt[2,3]),coarse_failure=failure,
             dense_step_mm=.015,status='BLOCKED' if fine_failure else 'PASS',refined_failure=fine_failure)
    if fine_failure and fine_failure['kind']=='wire_clearance':
        name=fine_failure['obstacle']
        _,lo,hi,tree=target_data[name]
        p=transform_points(refined,matrices[target_group[name]])
        allowance=fine_failure['required_bound_mm']
        mask=np.all(p>=lo-allowance,axis=1)&np.all(p<=hi+allowance,axis=1)
        distance,point=min((float(tree.find_nearest(Vector(q))[3]),q.tolist()) for q in p[mask])
        error=lengths[pin-1]['curve_chord_error_mm']
        witness=dict(point_in_obstacle_frame_mm=point,centreline_surface_mm=distance,
                     sampled_wire_surface_gap_mm=distance-OD/2,
                     nominal_margin_mm=MARGIN,analytic_curve_chord_error_mm=error,
                     intersection_witness=distance+error+.0001<OD/2,
                     margin_violation_witness=distance+error+.0001<OD/2+MARGIN)
        row['minimum_sample_witness']=witness
        fine_failure=dict(fine_failure,minimum_sample_witness=witness)
    clearance_calls.append(row)
    return fine_failure


endpoint=next(c for c in screen['pools']['4'] if c['candidate_id']=='pin4_3')
results=[]
for exponent in [2.,3.,4.,.5,.25,1.]:
    schedule_exponent=exponent
    active_endpoint=dict(endpoint,candidate_id='pin4_refined_'+str(exponent).replace('.','p'))
    r=check_candidate(4,active_endpoint)
    r['schedule_exponent']=exponent
    results.append(r)
    print('CAM_LIFT_REFINED',exponent,r['status'],r['passing_positions'],r['failure'],
          round(time.time()-started,2),flush=True)
report=dict(status='PASS' if any(r['status']=='PASS' for r in results) else 'BLOCKED',
            scope='Pin 4 finite-lift schedule refinement only; simultaneous four-wire assembly not certified',
            script_sha256=sha(REFINE_SCRIPT),helper_sha256=sha(REFINE_HELPER),
            source_files={**schedule['source_files'],str(schedule_path.relative_to(PROJECT)):sha(schedule_path)},
            protected_sources=protected,source_main_sha256=source_hash,
            results=results,refined_clearance_calls=clearance_calls,
            densification_preserves_source_polyline=True,source_analytic_chord_error_retained=True,
            source_prints=membership['substituted_unadopted_prints'],
            continuous_movement='NOT_TESTED',whole_harness='BLOCKED',
            main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_LIFT_REFINEMENT_DONE',report['status'],round(time.time()-started,2),flush=True)
