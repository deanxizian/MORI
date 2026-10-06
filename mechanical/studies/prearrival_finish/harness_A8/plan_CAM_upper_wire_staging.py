"""Plan all four long upright leads before bringing them into the root fan.

Keep material length by blending each unit tangent with vertical, then
renormalizing before integrating. The terminal remains on the vertical end
straight. This is a finite diagnostic candidate, not a full feed certificate.
"""
from pathlib import Path
US_SCRIPT=Path(__file__).resolve();US_ROOT=US_SCRIPT.parent
US_HELPER=US_ROOT/'refine_CAM_root_seating.py';__file__=str(US_HELPER)
exec(compile(US_HELPER.read_text().split('\nrx_rows=[];',1)[0],str(US_HELPER),'exec'),globals())
__file__=str(US_SCRIPT)
US_OUT=RS_OUT/'upright_staging';US_OUT.mkdir(exist_ok=True)
us_started=time.time();us_target,us_info=rs_curves(1.5)
us_ds=[np.linalg.norm(np.diff(q,axis=0),axis=1) for q in us_target]
us_T=[np.diff(q,axis=0)/s[:,None] for q,s in zip(us_target,us_ds)]
assert min(t[:,2].min() for t in us_T)>-1e-8
us_max_step=max(float(s.max()) for s in us_ds)
us_max_length=max(float(s.sum()) for s in us_ds)
# This is a screening allowance, not a completed integration-error proof.
us_error=.002
print('UPRIGHT_STAGING_INPUT',us_max_step,us_max_length,min(t[:,2].min() for t in us_T),flush=True)

def rs_curves(fraction):
    curves=[];info=[]
    for slot,(q,ds,t) in enumerate(zip(us_target,us_ds,us_T)):
        direction=t*fraction+np.array([0.,0.,1.])*(1.-fraction)
        direction/=np.linalg.norm(direction,axis=1)[:,None]
        p=np.vstack([q[0],q[0]+np.cumsum(ds[:,None]*direction,axis=0)])
        delta=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()-ds.sum())
        assert abs(delta)<1e-9
        meta=dict(us_info[slot]);meta.update(curve_error_bound_mm=us_error,
            root_mm=p[np.argmin(np.linalg.norm(q-np.array(us_info[slot]['root_mm']),axis=1))].tolist(),
            free_end_mm=p[-1].tolist(),polyline_length_mm=float(ds.sum()),polyline_length_change_mm=delta)
        curves.append(p);info.append(meta)
    return curves,info

us_rows=[];us_saved={}
for fraction in np.linspace(0.,1.,21):
    result,curves,info=rs_check(float(fraction))
    crimp=rx_exact_crimp(curves,info)
    if result['status']=='PASS' and crimp['status']!='PASS':result=crimp
    us_rows.append(dict(fraction=float(fraction),result=result,exact_crimp_check=crimp,curves=info))
    if any(abs(fraction-v)<1e-9 for v in [0.,.25,.5,.75,1.]):
        for slot,p in enumerate(curves):us_saved[f'f{fraction:g}_slot{slot}']=p
    print('UPRIGHT_STAGING',round(float(fraction),3),result['status'],result.get('kind'),result.get('slot'),result.get('other'),result.get('detail'),round(time.time()-us_started,1),flush=True)
np.savez_compressed(US_OUT/'curves.npz',**us_saved)
report=dict(status='PASS' if all(r['result']['status']=='PASS' for r in us_rows) else 'BLOCKED',
    scope='Twenty-one finite simultaneous tangent-blend wire staging poses, using 0.002-mm provisional sampling allowance; no continuous certificate',
    source_main_sha256=source_hash,script_sha256=sha(US_SCRIPT),helper_sha256=sha(US_HELPER),
    source_seating_sha256=sha(RX_OUT/'verification.json'),curves_sha256=sha(US_OUT/'curves.npz'),
    material_length='Each discrete segment keeps its original length',
    smooth_family_radius_basis='For unit target T with T.z >= 0, |(1-f)ez+fT| >= f; normalized-tangent derivative in arclength is at most |Tprime|',
    integration_error_proof='NOT_TESTED',continuous_motion='NOT_TESTED',
    provisional_sampling_allowance_mm=us_error,maximum_target_polyline_step_mm=us_max_step,
    maximum_target_polyline_length_mm=us_max_length,rows=us_rows,
    source_fixture_ids=[t[0] for t in fm_targets],uninstalled_tie_parts=sorted(rs_omitted),
    wire_OD_mm=OD,ordinary_structure_wire_margin_mm=.3,contact_wire_margin_mm=0.,
    initial_vertical_feed='NOT_TESTED',connection_to_neck_feed='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-us_started)
(US_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('UPRIGHT_STAGING_DONE',report['status'],round(time.time()-us_started,1),flush=True)
