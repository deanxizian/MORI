"""Delay the third lead's side rotation until its allocated contact clears.

The wider allocation exposes a true box overlap right after the original
start. Compare a delayed temporary rotation and repeat continuous checks;
no smaller contact, clearance waiver, or source geometry change is used.
"""
from pathlib import Path
LD_SCRIPT=Path(__file__).resolve();LD_ROOT=LD_SCRIPT.parent
LD_HELPER=LD_ROOT/'check_CAM_large_contact_forming.py';__file__=str(LD_HELPER)
exec(compile(LD_HELPER.read_text().split('\n# Finite static/end-state replay',1)[0],str(LD_HELPER),'exec'),globals())
__file__=str(LD_SCRIPT)
LD_OUT=LC_OUT/'start_delay';LD_OUT.mkdir(exist_ok=True)
ld_prior_path=LF_OUT/'continuous.json';ld_prior=json.loads(ld_prior_path.read_text())
assert ld_prior['status']=='BLOCKED' and ld_prior['script_sha256']==sha(LD_HELPER)
ld_started=time.time();ld_trials=[];ld_selected=None
ld_original=[s['path'] for s in lc_forming['stages']]


def ld_original_control(stage,f):
    path=ld_original[stage]
    edge=next((a,b) for a,b in zip(path,path[1:]) if a['fraction']-1e-10<=f<=b['fraction']+1e-10)
    return sc_control(edge,f)


def lf_unchanged(stage,edge):
    for node in edge:
        before=ld_original_control(stage,node['fraction'])
        if max(abs(before[0]-node['amplitude_mm']),abs(before[1]-node['side_angle_deg']))>1e-12:return False
    return True


for delay in (.0125,.015,.0175,.020):
    path=[];rows=[];failure=None
    for f in sorted(set([n['fraction'] for n in ld_original[2]]+[delay])):
        amp,angle=ld_original_control(2,f)
        if f<.025:angle=0. if f<=delay else -6.*(f-delay)/(.025-delay)
        path.append(dict(fraction=f,amplitude_mm=amp,side_angle_deg=angle))
    for f in np.linspace(0.,.025,81):
        f=float(f);edge=next((a,b) for a,b in zip(path,path[1:]) if a['fraction']-1e-10<=f<=b['fraction']+1e-10)
        amp,angle=sc_control(edge,f);failure,curves,contacts=lc_forming_pose(2,edge,f)
        if failure is None:
            check,_=oe_check(amp,angle,2,f,da_order)
            if check['status']!='PASS':failure=dict(kind='wire_geometry',detail=check)
        rows.append(dict(fraction=f,amplitude_mm=amp,side_angle_deg=angle,status='PASS' if failure is None else 'BLOCKED',failure=failure))
        if failure:break
    trial=dict(rotation_delay_fraction=delay,status='PASS' if failure is None else 'BLOCKED',checked_positions=len(rows),rows=rows)
    ld_trials.append(trial)
    print('LARGER_START_DELAY',delay,trial['status'],len(rows),failure,flush=True)
    if failure is None:
        ld_selected=trial;lf_paths[2]=path;break

if ld_selected:
    # Every original knot is present. Endpoint control equality therefore
    # certifies an entire unchanged affine edge, not merely a few samples.
    for stage,path in enumerate(lf_paths):
        assert {n['fraction'] for n in ld_original[stage]}.issubset({n['fraction'] for n in path})
        assert path[0]==ld_original[stage][0] and path[-1]==ld_original[stage][-1]
        for edge,f in [((path[0],path[1]),0.),((path[-2],path[-1]),1.)]:
            failure,curves,contacts=lc_forming_pose(stage,edge,f);assert failure is None,failure
            slot=da_order[stage];q,u,e=sc_curve(stage,edge,f);old,old_u,_,_=oe_static[slot,f]
            ref=np.column_stack([np.interp(u,old_u,old[:,k]) for k in range(3)])
            difference=float(np.linalg.norm(q-ref,axis=1).max());assert difference<1e-8
            lf_endpoints.append(dict(stage=stage,fraction=f,status='PASS',maximum_wire_difference_mm=difference))
    edges=[(s,a,b) for s,path in enumerate(lf_paths) for a,b in zip(path,path[1:])]
    edges.sort(key=lambda row:(lf_unchanged(row[0],row[1:]),row[0],row[1]['fraction']))
    try:
        for stage,a,b in edges:lf_interval(stage,(a,b),a['fraction'],b['fraction'])
        error=None
    except Exception as exc:error=repr(exc)
else:error='No finite startup candidate passed'

coverage=[]
for stage in range(4):
    rows=sorted([r for r in lf_pass if r['stage']==stage],key=lambda r:r['interval'][0])
    complete=bool(rows and rows[0]['interval'][0]==0. and rows[-1]['interval'][1]==1.
        and all(a['interval'][1]==b['interval'][0] for a,b in zip(rows,rows[1:])))
    coverage.append(dict(stage=stage,complete=complete,intervals=len(rows)))
status='PASS' if all(r['complete'] for r in coverage) and not lf_unproved and error is None else 'BLOCKED'
report=dict(status=status,scope='Four continuous forming stages for larger requested contact space, including delayed third-lead side rotation and minor last-lead side/height return',
    script_sha256=sha(LD_SCRIPT),helper_sha256=sha(LD_HELPER),source_main_sha256=source_hash,
    source_failed_continuous_sha256=sha(ld_prior_path),source_last_stage_candidate_sha256=sha(lf_candidate_path),
    source_original_forming_sha256=sha(lc_forming_path),continuous_math_helper_sha256=sha(LD_ROOT/'check_CAM_sequential_continuous.py'),
    trials=ld_trials,selected_delay=ld_selected['rotation_delay_fraction'] if ld_selected else None,
    stages=[dict(stage=s,active_slot=da_order[s],path=path) for s,path in enumerate(lf_paths)],
    contact_dimensions_mm=ft_dims.tolist(),contact_evidence='ASSUMED requested space; not manufacturer maximum finished/crimped terminal dimensions',
    coverage=coverage,complete_coverage=status=='PASS',passed_intervals=lf_pass,unproved_intervals=lf_unproved,error=error,
    interval_tests=lf_tests,boundary_rows=lf_endpoints,all_source_control_knots_retained=True,
    wire_certificate_reuse='Only affine edges with both controls exactly equal to original endpoints; all original knots retained. Changed wire edges repeat full wire/solid/pair/self bounds.',
    contact_contact_boundary_proof=ld_prior['contact_contact_boundary_basis'],
    contact_structure_margin_mm=.3,ordinary_wire_margin_mm=.3,contact_wire_margin_mm=0.,
    own_crimp_exclusion_mm=2.,material_length_invariant=lc_forming['material_length_invariant'],
    radius_lower_bound_mm=lc_forming['nominal_curve_radius_lower_bound_mm'],
    actual_terminal_fit='NOT_TESTED',body_material_supply='NOT_TESTED',tie_threading_and_tightening='NOT_TESTED',
    whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,elapsed_s=time.time()-ld_started)
(LD_OUT/'continuous.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LARGER_START_DELAY_DONE',status,len(lf_pass),error,round(time.time()-ld_started,1),flush=True)
