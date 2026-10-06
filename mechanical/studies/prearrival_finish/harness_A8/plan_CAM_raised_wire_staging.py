"""Raise intermediate bends before converging the upper four-wire fan.

Add the same temporary vertical length below the bends as is removed from
the existing final vertical tail. Endpoints and material length are unchanged.
This is a finite route candidate, not continuous or physical qualification.
"""
from pathlib import Path
LS_SCRIPT=Path(__file__).resolve();LS_ROOT=LS_SCRIPT.parent
LS_HELPER=LS_ROOT/'plan_CAM_upper_wire_staging.py';__file__=str(LS_HELPER)
exec(compile(LS_HELPER.read_text().split('\nus_rows=[];',1)[0],str(LS_HELPER),'exec'),globals())
__file__=str(LS_SCRIPT)
LS_OUT=RS_OUT/'raised_staging';LS_OUT.mkdir(exist_ok=True)
ls_started=time.time();ls_base_curves=rs_curves;ls_max_raise=2.

def rs_curves(fraction):
    curves,info=ls_base_curves(fraction)
    lift=ls_max_raise*math.sin(math.pi*fraction)
    for slot,p in enumerate(curves):
        if lift>1e-9:
            end=p[-1]-np.array([0.,0.,lift])
            assert lift<us_info[slot]['terminal_straight_remaining_mm']
            tail=np.vstack([p[p[:,2]<end[2]-1e-9],end])+np.array([0.,0.,lift])
            front=np.linspace(p[0],p[0]+np.array([0.,0.,lift]),int(math.ceil(lift/.008))+1)
            q=np.vstack([front[:-1],tail])
        else:q=p
        delta=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()-us_ds[slot].sum())
        assert abs(delta)<1e-8 and np.linalg.norm(q[-1]-p[-1])<1e-9
        info[slot].update(polyline_length_change_mm=delta,temporary_bend_raise_mm=lift,
            remaining_final_straight_mm=us_info[slot]['terminal_straight_remaining_mm']-lift,
            root_mm=(np.array(info[slot]['root_mm'])+[0.,0.,lift]).tolist())
        curves[slot]=q
    return curves,info

ls_trials=[];ls_saved={};ls_selected=None
for ls_max_raise in [2.,3.,4.]:
    rows=[]
    for fraction in np.linspace(0.,1.,21):
        result,curves,info=rs_check(float(fraction))
        crimp=rx_exact_crimp(curves,info)
        if result['status']=='PASS' and crimp['status']!='PASS':result=crimp
        rows.append(dict(fraction=float(fraction),result=result,exact_crimp_check=crimp,curves=info))
        if any(abs(fraction-v)<1e-9 for v in [0.,.25,.5,.75,1.]):
            for slot,p in enumerate(curves):ls_saved[f'raise{ls_max_raise:g}_f{fraction:g}_slot{slot}']=p
        print('RAISED_STAGING',ls_max_raise,round(float(fraction),3),result['status'],result.get('kind'),result.get('slot'),result.get('other'),result.get('detail'),round(time.time()-ls_started,1),flush=True)
    status='PASS' if all(r['result']['status']=='PASS' for r in rows) else 'BLOCKED'
    ls_trials.append(dict(maximum_raise_mm=ls_max_raise,status=status,rows=rows))
    if status=='PASS':ls_selected=ls_trials[-1];break
np.savez_compressed(LS_OUT/'curves.npz',**ls_saved)
report=dict(status='PASS' if ls_selected else 'BLOCKED',
    scope='Finite four-wire staging with delayed bends; continuous collision and numerical integration error are not yet certified',
    source_main_sha256=source_hash,script_sha256=sha(LS_SCRIPT),helper_sha256=sha(LS_HELPER),
    source_seating_sha256=sha(RX_OUT/'verification.json'),source_direct_staging_sha256=sha(US_OUT/'screen.json'),
    curves_sha256=sha(LS_OUT/'curves.npz'),trials=ls_trials,selected_raise_mm=ls_selected['maximum_raise_mm'] if ls_selected else None,
    source_fixture_ids=[t[0] for t in fm_targets],uninstalled_tie_parts=sorted(rs_omitted),
    wire_OD_mm=OD,ordinary_structure_wire_margin_mm=.3,contact_wire_margin_mm=0.,
    provisional_sampling_allowance_mm=us_error,
    material_length_basis='Add a lower vertical segment and remove the identical arclength from the existing upper vertical end; all discrete segments otherwise retain length',
    continuous_motion='NOT_TESTED',integration_error_proof='NOT_TESTED',
    initial_vertical_feed='NOT_TESTED',connection_to_neck_feed='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-ls_started)
(LS_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('RAISED_STAGING_DONE',report['status'],report['selected_raise_mm'],round(time.time()-ls_started,1),flush=True)
