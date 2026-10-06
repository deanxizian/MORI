"""Save reproducible route poses and narrow geometric failure witnesses."""
from pathlib import Path
WC_SCRIPT=Path(__file__).resolve();WC_ROOT=WC_SCRIPT.parent
WC_HELPER=WC_ROOT/'check_CAM_wired_cradle_insertion.py';__file__=str(WC_HELPER)
exec(compile(WC_HELPER.read_text().split('\nwi_rows=[];',1)[0],str(WC_HELPER),'exec'),globals())
__file__=str(WC_SCRIPT);WC_OUT=WC_ROOT/'cam_wired_cradle'
wc_arrays={};wc_rows=[]
for h in [0.,6.,9.,42.]:
    c,meta=wi_core(h)
    for slot in range(4):
        core=c+[xx[slot]-xx[0],0.,0.];tail=PW_OLD_TAILS[slot]+[0.,0.,h]
        wc_arrays[f'lift{h}_core{slot}']=core;wc_arrays[f'lift{h}_tail{slot}']=tail
        wc_arrays[f'fan{slot}']=pw_fans[slot][0];wc_arrays[f'body{slot}']=body_samples[slot+1,0][0]
    if h==9.:
        p=fine(np.vstack([wc_arrays['lift9.0_core0'],wc_arrays['lift9.0_tail0'][-2::-1]]),.005)
        q=pw_fans[1];err=max(meta['curve_error_mm'],tail_error)
        result=pair(p,q,err,pw_fan_errors[1]);a,b=result['sample_indices']
        wc_rows.append({'lift_mm':h,'kind':'wire_to_other_fan','slot':0,'other_slot':1,**result,
          'points_mm':[p[0][a].tolist(),q[0][b].tolist()],
          'note':'The prescribed 0.3 mm noncontact allowance fails; this row alone does not assert physical overlap.'})
    if h==42.:
        p=fine(np.vstack([wc_arrays['lift42.0_core0'],wc_arrays['lift42.0_tail0'][-2::-1]]),.005)
        best=(1.,None,None)
        for i,pt in enumerate(p[0]):
            for _,j,d in p[2].find_range(Vector(pt),min(best[0]+1e-5,OD+.05)):
                if abs(float(p[1][i]-p[1][j]))<=2.:continue
                if d<best[0]:best=(float(d),i,int(j))
        d,i,j=best;assert i is not None
        err=max(meta['curve_error_mm'],tail_error)
        # These are points on the saved chords, with analytic curve-error
        # bounds included. Negative upper bound demonstrates intersection of
        # the two nonlocal round-wire envelopes in this prescribed pose.
        upper=d-OD+2*err+1e-4
        wc_rows.append({'lift_mm':h,'kind':'self_return','slot':0,'sample_center_distance_mm':d,
            'surface_gap_upper_bound_mm':upper,'physical_envelope_overlap_demonstrated':upper<0,
            'points_mm':[p[0][i].tolist(),p[0][j].tolist()],
            'local_arclength_exclusion_mm':2.,'separated_arclength_mm':abs(float(p[1][i]-p[1][j])),
            'note':'Intersection of prescribed envelopes, not a simulated natural wire shape.'})
np.savez_compressed(WC_OUT/'review_curves.npz',**wc_arrays)
report={'status':'PASS','scope':'Reproducible witnesses of the rejected rigid-tail assembly family',
    'source_main_sha256':source_hash,'script_sha256':sha(WC_SCRIPT),'helper_sha256':sha(WC_HELPER),
    'screen_sha256':sha(WC_OUT/'screen.json'),'curves_sha256':sha(WC_OUT/'review_curves.npz'),
    'wire_OD_mm':OD,'rows':wc_rows,'main_applied':False,'whole_harness':'BLOCKED'}
(WC_OUT/'witnesses.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CAM_CRADLE_WITNESSES',json.dumps(wc_rows,ensure_ascii=False),flush=True)
