"""Refine inconclusive chord sampling without lowering the clearance target.

Inserted points lie on existing chords. The original analytic sagitta error
is retained, so subdivision does not claim a more accurate underlying curve.
Only a small temporary loose-tail movement is investigated.
"""
from pathlib import Path
REFINE16_SCRIPT=Path(__file__).resolve()
REFINE16_HELPER=REFINE16_SCRIPT.parent/'screen_shell16_temporary_tail_splay.py'
__file__=str(REFINE16_HELPER)
exec(compile(REFINE16_HELPER.read_text().split('\ntrials=[];',1)[0],str(REFINE16_HELPER),'exec'),globals())
__file__=str(REFINE16_SCRIPT)
OUT=ORDER_OUT/'shell16_refined_tail_splay';OUT.mkdir(exist_ok=True)
refinements=Counter()


def refine_chords(c,step=.02):
    p=c['points'];ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
    counts=np.maximum(1,np.ceil(ds/step).astype(int))
    pts=np.concatenate([a+(b-a)*np.arange(n)[:,None]/n for a,b,n in zip(p[:-1],p[1:],counts)]+[p[-1:]])
    assert np.max(np.linalg.norm(np.diff(pts,axis=0),axis=1))<=step+1e-9
    assert abs(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()-ds.sum())<1e-7
    return dict(c,points=pts,chord_subdivision_mm=step)


def evaluate(back,parameters):
    set_pose(-float(back));curves={};failure=None;pairs=[]
    for pin in range(1,5):
        c,failure=one(pin,parameters[pin])
        if c is not None and failure and failure['kind'] in ['wire_clearance','self_return_clearance']:
            refinements['wire_or_self']+=1
            c=refine_chords(c)
            lengths[pin-1]['curve_chord_error_mm']=c['curve_chord_error_mm']
            failure=wire_check(pin,c['points'],matrices) or self_check(c) or rigid_check(make_terminal(c,bt),matrices)
        if failure:break
        curves[pin]=c
    if not failure:
        pairs,failure=mutual_check(curves)
        if failure:
            refinements['mutual']+=1
            curves={pin:refine_chords(c) for pin,c in curves.items()}
            pairs,failure=mutual_check(curves)
    if not failure:failure=terminal_checks(curves,bt)
    return failure,curves,pairs


trials=[];chosen_splay=None;chosen_arrays={};chosen_records=[]
for splay_angle in [4.,5.,6.,-4.]:
    holds=copy.deepcopy(original_holds)
    holds[0][4]=[dict(starts[4],entry_azimuth_deg=-7.5,planar_radius_mm=8.)]
    holds[2][1]=[dict(starts[1],elevation_fraction=.5,tail_yaw_deg=splay_angle)]
    current={pin:dict(p) for pin,p in starts.items()};records=[];diagnostics=[];saved={};failure=None
    f,curves,pairs=evaluate(0.,current);assert not f,f
    for pin,c in curves.items():assert np.array_equal(c['points'],start_curves[f'pin{pin}_pose36'])
    store_record(0.,'initial',current,curves,pairs)
    exec(compile(splay_loop,str(SPLAY16_HELPER),'exec'),globals())
    row=dict(tail_yaw_deg=splay_angle,status='BLOCKED' if failure else 'PASS',
             passing_positions=len(records),furthest_back_mm=-records[-1]['bridge_y_mm'],
             failure=failure,diagnostics=diagnostics)
    trials.append(row)
    print('REFINED_TAIL_TRIAL',splay_angle,row['status'],row['furthest_back_mm'],failure,flush=True)
    if not failure:
        chosen_splay=row;chosen_arrays=saved;chosen_records=records;break
np.savez_compressed(OUT/'curves.npz',**chosen_arrays)
report=dict(status='PASS' if chosen_splay else 'BLOCKED',
    scope='Finite four-wire rear motion with refined conservative clearance bounds; final restoration not covered',
    script_sha256=sha(REFINE16_SCRIPT),helper_sha256=sha(REFINE16_HELPER),
    source_files={**graph['source_files'],str(graph_path.relative_to(PROJECT)):sha(graph_path),
                  str(rigid_all_path.relative_to(PROJECT)):sha(rigid_all_path),
                  str(SPLAY16_HELPER.relative_to(PROJECT)):sha(SPLAY16_HELPER)},
    protected_sources=protected,trials=trials,selected=chosen_splay,records=chosen_records,
    final_parameters=current if chosen_splay else None,curves_sha256=sha(OUT/'curves.npz'),
    refinements=dict(refinements),refined_chord_step_mm=.02,original_analytic_error_retained=True,
    required_surface_margin_mm=MARGIN,wire_OD_mm=OD,
    body_wire_count=14,full_nominal_lengths_preserved=True,exact_initial_boundary_match=True,
    continuous_motion='NOT_TESTED',branch_continuity_audit='NOT_TESTED',
    vertical_continuation='NOT_TESTED',loose_tail_restoration='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('REFINED_TAIL_DONE',report['status'],len(trials),round(time.time()-started,1),flush=True)
