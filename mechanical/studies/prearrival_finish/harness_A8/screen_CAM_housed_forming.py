"""Try larger temporary loop lifts with the catalogue SH housing present."""
from pathlib import Path
HF_SCRIPT=Path(__file__).resolve();HF_ROOT=HF_SCRIPT.parent
HF_HELPER=HF_ROOT/'check_CAM_forming_terminals.py';__file__=str(HF_HELPER)
exec(compile(HF_HELPER.read_text().split('\nfor fraction in np.linspace',1)[0],str(HF_HELPER),'exec'),globals())
__file__=str(HF_SCRIPT)
HF_OUT=FM_OUT/'housed';HF_OUT.mkdir(exist_ok=True);hf_trials=[];hf_started=time.time()
for amplitude in [12.,15.,18.]:
    rows=[]
    for fraction in sorted(set(np.linspace(0.,1.,41).tolist()+np.linspace(.95,1.,26).tolist())):
        base,parameter,error,extra=fr_curve(fraction,amplitude);rot,_=ft_frame(fraction,base[-1])
        tr=np.column_stack([rot,base[-1]-rot@ft_final]);housing=bl_plug.transform(tr)
        hr=ft_source(housing);hits=[]
        if hr['status']=='PASS':
            for slot in range(4):
                hit=fr_check(base+[xx[slot]-xx[0],0.,0.],parameter,error,slot,fraction)
                if hit:hits.append(hit);break
        # The final straight's intended contact still prevents a blanket
        # 0.3mm wire-gap statement. Preserve this result, don't waive it here.
        rows.append({'fraction':fraction,'apex_extra_mm':extra,'housing':hr,'wire_hits':hits,
            'status':'PASS' if hr['status']=='PASS' and not hits else 'BLOCKED'})
    housing_pass=all(r['housing']['status']=='PASS' for r in rows)
    hf_trials.append({'amplitude_mm':amplitude,'housing_status':'PASS' if housing_pass else 'BLOCKED','rows':rows})
    print('HOUSED_FORMING',amplitude,hf_trials[-1]['housing_status'],[(r['fraction'],r['housing']['nearest_within_2mm']) for r in rows if r['housing']['status']!='PASS'],flush=True)
    if housing_pass:break
report={'status':'PASS' if hf_trials[-1]['housing_status']=='PASS' else 'BLOCKED',
 'scope':'Finite housing-to-stage-solid screen; intended wire-seat contact separately retained',
 'selected_amplitude_mm':hf_trials[-1]['amplitude_mm'] if hf_trials[-1]['housing_status']=='PASS' else None,
 'trials':hf_trials,'source_main_sha256':source_hash,'script_sha256':sha(HF_SCRIPT),'helper_sha256':sha(HF_HELPER),
 'source_contact_screen_sha256':sha(FT_OUT/'screen.json'),'continuous_motion':'NOT_TESTED',
 'terminal_insertion_into_housing':'NOT_TESTED','main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
 'elapsed_s':time.time()-hf_started}
(HF_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('HOUSED_FORMING_DONE',report['status'],report['selected_amplitude_mm'],flush=True)
