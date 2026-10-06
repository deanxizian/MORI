"""Inspect current root-seating datums without changing any source geometry."""
from pathlib import Path
RS_SCRIPT=Path(__file__).resolve();RS_ROOT=RS_SCRIPT.parent
RS_HELPER=RS_ROOT/'check_CAM_sequential_continuous.py';__file__=str(RS_HELPER)
exec(compile(RS_HELPER.read_text().split('\n# Static mixed states',1)[0],str(RS_HELPER),'exec'),globals())
__file__=str(RS_SCRIPT)
RS_OUT=TC_OUT/'root_seating';RS_OUT.mkdir(exist_ok=True)
rows=[];arrays={}
for slot in range(4):
    free,_,error,_=oe_static[slot,0.]
    fan,arcs,_,step=pw_fans[slot]
    arrays[f'fan_{slot}']=fan;arrays[f'free_{slot}']=free
    rows.append(dict(slot=slot,fan_start_mm=fan[0].tolist(),fan_end_mm=fan[-1].tolist(),
        fan_length_mm=float(arcs[-1]),fan_bounds_mm=[fan.min(0).tolist(),fan.max(0).tolist()],
        free_start_mm=free[0].tolist(),free_end_mm=free[-1].tolist(),free_polyline_length_mm=float(np.linalg.norm(np.diff(free,axis=0),axis=1).sum()),
        endpoint_mismatch_mm=float(np.linalg.norm(fan[-1]-free[0])),
        fan_sample_error_mm=pw_fan_errors[slot],free_sample_error_mm=error))
objects=[]
for name,group,solid,lo,hi,_ in fm_targets:
    if np.any(lo>np.array([10,15,245])) or np.any(hi<np.array([-20,-20,210])):continue
    objects.append(dict(object=name,group=group,bounds_mm=[lo.tolist(),hi.tolist()]))
np.savez_compressed(RS_OUT/'initial_curves.npz',**arrays)
report=dict(status='PASS',scope='Read-only coordinates for root-seating path design; no assembly result',
    source_main_sha256=source_hash,script_sha256=sha(RS_SCRIPT),helper_sha256=sha(RS_HELPER),
    source_forming_sha256=sha(TC_OUT/'negative_complete/screen.json'),rows=rows,nearby_objects=objects,
    curves_sha256=sha(RS_OUT/'initial_curves.npz'),root_seating='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(RS_OUT/'layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ROOT_SEATING_LAYOUT',json.dumps({'rows':rows,'nearby_objects':objects}),flush=True)
