"""Compare coordinated early bends instead of independent per-wire timing."""
from pathlib import Path
COUPLED16_SCRIPT=Path(__file__).resolve();COUPLED16_HELPER=COUPLED16_SCRIPT.parent/'merge_shell16_back20_wires.py'
coupled_source=COUPLED16_HELPER.read_text();coupled_marker='\nfor k in range(21):'
assert coupled_source.count(coupled_marker)==1
__file__=str(COUPLED16_HELPER)
exec(compile(coupled_source.split(coupled_marker,1)[0],str(COUPLED16_HELPER),'exec'),globals())
__file__=str(COUPLED16_SCRIPT)
import copy
coupled_loop='for k in range(21):'+coupled_source.split(coupled_marker,1)[1].split('\nnp.savez_compressed',1)[0]
OUT=ORDER_OUT/'shell16_coupled_hold_timing';OUT.mkdir(exist_ok=True)
original_holds=copy.deepcopy(holds)
specs=[('paired_at0',0,None),('paired_at2',2,None),('paired_at2_p4_forward15',2,15.),
       ('paired_at2_p4_rear15',2,-15.),('paired_at2_p4_forward30',2,30.),('paired_at2_p4_rear30',2,-30.),
       ('original_p4_late15',None,15.),('original_p4_late_rear15',None,-15.)]
trials=[];chosen_trial=None;chosen_arrays={};chosen_records=[]
for timing_name,pair_at,p4_angle in specs:
    holds=copy.deepcopy(original_holds)
    if pair_at is not None:
        for h in holds.values():h[1]=[];h[2]=[]
        for pin in [1,2]:
            holds[pair_at][pin]=[dict(starts[pin],elevation_fraction=f) for f in [.75,.5]]
    if p4_angle is not None:
        holds[2][4]=[dict(starts[4],entry_azimuth_deg=p4_angle,planar_radius_mm=8.)]
    current={pin:dict(p) for pin,p in starts.items()};records=[];diagnostics=[];saved={};failure=None
    f,curves,pairs=evaluate(0.,current);assert f is None
    for pin,c in curves.items():assert np.array_equal(c['points'],start_curves[f'pin{pin}_pose36'])
    store_record(0.,'initial',current,curves,pairs)
    exec(compile(coupled_loop,str(COUPLED16_HELPER),'exec'),globals())
    entry=dict(name=timing_name,paired_lowering_at_back_mm=pair_at,pin4_angle_deg=p4_angle,
               status='BLOCKED' if failure else 'PASS',checked_positions=len(records),
               furthest_back_mm=-records[-1]['bridge_y_mm'],failure=failure,diagnostics=diagnostics)
    trials.append(entry)
    print('SHELL16_COUPLED_TIMING',timing_name,entry['status'],entry['furthest_back_mm'],failure,flush=True)
    if not failure:
        chosen_trial=entry;chosen_arrays=saved;chosen_records=records;break
np.savez_compressed(OUT/'curves.npz',**chosen_arrays)
report=dict(status='PASS' if chosen_trial else 'BLOCKED',scope='Finite coordinated wire reshaping, not continuous or complete assembly',
    script_sha256=sha(COUPLED16_SCRIPT),helper_sha256=sha(COUPLED16_HELPER),
    source_files={**graph['source_files'],str(graph_path.relative_to(PROJECT)):sha(graph_path),str(rigid_all_path.relative_to(PROJECT)):sha(rigid_all_path)},
    protected_sources=protected,trials=trials,selected=chosen_trial,records=chosen_records,
    final_parameters=current if chosen_trial else None,curves_sha256=sha(OUT/'curves.npz'),
    body_wire_count=14,full_nominal_lengths_preserved=True,exact_initial_boundary_match=True,
    continuous_motion='NOT_TESTED',vertical_continuation='NOT_TESTED',complete_attached_assembly='BLOCKED',
    main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_COUPLED_TIMING_DONE',report['status'],len(trials),flush=True)
