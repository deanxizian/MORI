"""Compare early fourth-wire shaping without changing hardware or wire length."""
from pathlib import Path
RELIEF16_SCRIPT=Path(__file__).resolve();RELIEF16_HELPER=RELIEF16_SCRIPT.parent/'merge_shell16_back20_wires.py'
merge_source=RELIEF16_HELPER.read_text();marker='\nfor k in range(21):'
assert merge_source.count(marker)==1
__file__=str(RELIEF16_HELPER)
exec(compile(merge_source.split(marker,1)[0],str(RELIEF16_HELPER),'exec'),globals())
__file__=str(RELIEF16_SCRIPT)
merge_loop='for k in range(21):'+merge_source.split(marker,1)[1].split('\nnp.savez_compressed',1)[0]
OUT=ORDER_OUT/'shell16_fourth_wire_relief';OUT.mkdir(exist_ok=True)
baseline_path=ORDER_OUT/'shell16_back20_merged/screen.json'
baseline=json.loads(baseline_path.read_text())
assert baseline['script_sha256']==sha(RELIEF16_HELPER) and baseline['status']=='BLOCKED'
trials=[];selected_relief=None;selected_arrays={};selected_records=[];selected_diagnostics=[]
for relief_az,relief_r in [(0.,8.),(0.,7.),(0.,12.),(7.5,8.),(15.,10.),(-7.5,8.)]:
    current={pin:dict(p) for pin,p in starts.items()};records=[];diagnostics=[];saved={};failure=None
    relief_spec=dict(entry_azimuth_deg=relief_az,planar_radius_mm=relief_r,family=starts[4]['family'],elevation_fraction=0.)
    holds[0][4]=[relief_spec]
    f,curves,pairs=evaluate(0.,current);assert f is None
    for pin,c in curves.items():assert np.array_equal(c['points'],start_curves[f'pin{pin}_pose36'])
    store_record(0.,'initial',current,curves,pairs)
    exec(compile(merge_loop,str(RELIEF16_HELPER),'exec'),globals())
    entry=dict(pin4_parameters=relief_spec,status='BLOCKED' if failure else 'PASS',
               checked_positions=len(records),furthest_back_mm=-records[-1]['bridge_y_mm'],failure=failure,
               diagnostics=diagnostics)
    trials.append(entry)
    print('SHELL16_RELIEF_CANDIDATE',entry['pin4_parameters'],entry['status'],entry['furthest_back_mm'],failure,flush=True)
    if not failure:
        selected_relief=entry;selected_arrays=saved;selected_records=records;selected_diagnostics=diagnostics;break
np.savez_compressed(OUT/'curves.npz',**selected_arrays)
report=dict(status='PASS' if selected_relief else 'BLOCKED',scope='Finite four-wire merging with early fourth-wire reshaping; later vertical still excluded',
    script_sha256=sha(RELIEF16_SCRIPT),helper_sha256=sha(RELIEF16_HELPER),
    source_files={**baseline['source_files'],str(baseline_path.relative_to(PROJECT)):sha(baseline_path)},
    protected_sources=protected,trials=trials,selected=selected_relief,records=selected_records,
    final_parameters=current if selected_relief else None,curves_sha256=sha(OUT/'curves.npz'),
    body_wire_count=14,full_nominal_lengths_preserved=True,exact_initial_boundary_match=True,
    continuous_motion='NOT_TESTED',vertical_continuation='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_RELIEF_DONE',report['status'],len(trials),flush=True)
