"""Head-cradle lowering with an unlocked straight CAM departure.

Keep the final core and neck fan in place. As the CAM/cradle is lifted by h,
extend only its initially downward straight departure by h. The added length
must come from a loose body end; that body reserve is NOT yet represented or
qualified here. Ties are not tightened until the cradle is seated.
"""
from pathlib import Path
SD_SCRIPT=Path(__file__).resolve();SD_ROOT=SD_SCRIPT.parent
SD_HELPER=SD_ROOT/'check_CAM_wired_cradle_insertion.py';__file__=str(SD_HELPER)
exec(compile(SD_HELPER.read_text().split('\nwi_rows=[];',1)[0],str(SD_HELPER),'exec'),globals())
__file__=str(SD_SCRIPT)
SD_OUT=SD_ROOT/'cam_sliding_departure';SD_OUT.mkdir(exist_ok=True)
sd_core0,sd_meta0=wi_core(0.)

def sd_tail(slot,h):
    original=PW_OLD_TAILS[slot]
    if h==0:return original.copy()
    extra=wi_line(original[0]+[0.,0.,h],original[0],step=.025)
    return np.vstack([extra[:-1],original])

sd_rows=[];sd_curves={};sd_started=time.time()
for h in [0.,42.,21.,6.,9.,12.,15.,18.,24.,27.,30.,33.,36.,39.,3.]:
    geometry=wi_geometry(h);failure=None;wire_samples={};wire_min=math.inf
    row={'lift_mm':h,'geometry':geometry,'additional_head_wire_length_each_mm':h,
         'length_source':'Requires equal payout from loose body-side wire; no stretch and no final cut length change'}
    if geometry['status']=='PASS':
        for slot in range(4):
            core=sd_core0+[xx[slot]-xx[0],0.,0.];tail=sd_tail(slot,h)
            assert np.linalg.norm(tail[-1]-core[-1])<1e-8
            assert np.linalg.norm(tail[0]-(PW_OLD_TAILS[slot][0]+[0,0,h]))<1e-8
            for kind,p,err in [('core',core,sd_meta0['curve_error_mm']),('tail',tail,tail_error)]:
                failure=wi_source(p,err,h,kind,slot)
                if failure:break
            if failure:break
            joined=np.vstack([core,tail[-2::-1]]);sample=fine(joined,.01);error=max(sd_meta0['curve_error_mm'],tail_error)
            result=pw_pack(sample,error,slot,0)
            if result['status']!='PASS':failure={'kind':'packing','slot':slot,**result};break
            wire_min=min(wire_min,result['minimum_fan_body_gap_bound_mm'])
            wire_samples[slot]=(sample,error);sd_curves[f'lift{h:g}_slot{slot}']=joined
        if not failure:
            for a,b in itertools.combinations(range(4),2):
                aa,ea=wire_samples[a];bb,eb=wire_samples[b];result=pair(aa,bb,ea,eb)
                wire_min=min(wire_min,result['gap_bound_mm'])
                if result['status']!='PASS':failure={'kind':'mutual_wire','slots':[a,b],**result};break
    else:failure={'kind':'rigid_geometry'}
    row.update(status='BLOCKED' if failure else 'PASS',failure=failure,
               minimum_pack_gap_mm=wire_min if math.isfinite(wire_min) else None)
    sd_rows.append(row)
    print('SLIDING_DEPARTURE',h,row['status'],failure,'elapsed',round(time.time()-sd_started,2),flush=True)
    np.savez_compressed(SD_OUT/'curves.npz',**sd_curves)
    result={'status':'PASS' if all(r['status']=='PASS' for r in sd_rows) else 'BLOCKED',
        'scope':'15 sampled CAM/cradle heights with unlocked variable straight departure; final core/fan unchanged; requires unvalidated body-side payout',
        'source_main_sha256':source_hash,'script_sha256':sha(SD_SCRIPT),'helper_sha256':sha(SD_HELPER),
        'source_tail_sha256':sha(SD_ROOT/'cam_fan_in/short_tail_v2/tails.npz'),
        'rows':sd_rows,'planned_heights_mm':list(range(0,43,3)),'curves_sha256':sha(SD_OUT/'curves.npz'),
        'moving_ids':list(wi_moving),'fixed_ids':list(wi_fixed),'not_yet_fitted':wi_excluded,
        'maximum_additional_head_length_each_mm':42.,'total_harness_length_conservation':'BLOCKED_BODY_RESERVE_NOT_MODELED',
        'ties_during_lowering':'Present as geometric envelopes only; not tensioned; sliding friction/pull force NOT_TESTED',
        'continuous_motion':'NOT_TESTED','body_loose_reserve':'NOT_TESTED',
        'full_threading_tightening':'NOT_TESTED','main_applied':False,'whole_harness':'BLOCKED',
        'manufacturing_release':False,'elapsed_s':time.time()-sd_started}
    (SD_OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert len(sd_rows)==15 and sha(source)==source_hash
print('SLIDING_DEPARTURE_DONE',result['status'],flush=True)
