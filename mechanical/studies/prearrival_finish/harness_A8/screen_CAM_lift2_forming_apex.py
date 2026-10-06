"""Search temporary apex lift after theA9 upstream-wire collision.

Candidate paths keep wire length, endpoint datums and all robot geometry.
Screen existing/upstream wires together with solids before expensive
continuous checking. This does not resolve bare-contact handling margins.
"""
from pathlib import Path
AP_SCRIPT=Path(__file__).resolve();AP_ROOT=AP_SCRIPT.parent
AP_HELPER=AP_ROOT/'check_CAM_forming_lift2_continuous.py';__file__=str(AP_HELPER)
exec(compile(AP_HELPER.read_text().split('\n# Independently generated finite curves',1)[0],str(AP_HELPER),'exec'),globals())
__file__=str(AP_SCRIPT)
AP_OUT=L2_OUT/'apex_revision';AP_OUT.mkdir(exist_ok=True);ap_started=time.time()
ap_rows=[];ap_saved={};ap_selected=None


def ap_pack(base,error):
    samples=[];rows=[]
    for slot in range(4):
        p=base+[xx[slot]-xx[0],0.,0.];sm=fine(p,.01);samples.append(sm)
        result=self_check(sm,error);rows.append({'kind':'self','slot':slot,**result})
        if result['status']!='PASS':return {'status':'BLOCKED','checks':rows},samples
        for other in range(4):
            r=own_prefix_check(sm,pw_fans[other],error,pw_fan_errors[other]) if slot==other else pair(sm,pw_fans[other],error,pw_fan_errors[other])
            rows.append({'kind':'yaw_fan','slot':slot,'other_slot':other,**r})
            if r['status']!='PASS':return {'status':'BLOCKED','checks':rows},samples
            r=pair(sm,body_samples[other+1,0],error,body_error)
            rows.append({'kind':'body_prefix','slot':slot,'other_slot':other,**r})
            if r['status']!='PASS':return {'status':'BLOCKED','checks':rows},samples
    for a,b in itertools.combinations(range(4),2):
        r=pair(samples[a],samples[b],error,error);rows.append({'kind':'wire_pair','slots':[a,b],**r})
        if r['status']!='PASS':return {'status':'BLOCKED','checks':rows},samples
    return {'status':'PASS','checks':rows},samples


ap_order=list(dict.fromkeys([.8,.775,.825,.75,.85,.9,.95,1.,0.]+[float(x) for x in np.linspace(0.,1.,41)]))
for amplitude in [10.5,12.,15.,18.]:
    fc_amplitude=amplitude;rows=[];saved={}
    for f in ap_order:
        p,u,error=fc_curve(f);hit=fc_test(f,f)
        packing,sm=ap_pack(p,error) if hit is None else ({'status':'NOT_TESTED'},[])
        row={'fraction':f,'solids_failure':hit,'wire_packing':packing,
             'status':'PASS' if hit is None and packing['status']=='PASS' else 'BLOCKED'}
        rows.append(row)
        print('APEX_SCREEN',amplitude,f,row['status'],hit,packing.get('checks',[None])[-1],flush=True)
        if row['status']!='PASS':break
        for slot in range(4):saved[f'f{f:.6f}_slot{slot}']=p+[xx[slot]-xx[0],0.,0.]
    good=len(rows)==len(ap_order) and all(r['status']=='PASS' for r in rows)
    ap_rows.append({'amplitude_mm':amplitude,'status':'PASS' if good else 'BLOCKED','rows':rows})
    if good:ap_saved=saved;ap_selected=amplitude;break
if ap_saved:np.savez_compressed(AP_OUT/'curves.npz',**ap_saved)
report={'status':'PASS' if ap_selected is not None else 'BLOCKED',
    'scope':'Finite specified forming positions, wires to solids and upstream conductors; contact-to-wire handling margins excluded',
    'source_main_sha256':source_hash,'script_sha256':sha(AP_SCRIPT),'helper_sha256':sha(AP_HELPER),
    'source_failed_packing_sha256':sha(L2_OUT/'packing_screen.json'),
    'source_collision_witness_sha256':sha(L2_OUT/'packing_collision_witness.json'),
    'final_plug_lift_mm':2.,'selected_amplitude_mm':ap_selected,'planned_fractions':ap_order,'trials':ap_rows,
    'curves_sha256':sha(AP_OUT/'curves.npz') if ap_saved else None,
    'wire_OD_mm':OD,'wire_surface_margin_mm':.3,'contact_to_structure_margin_mm':.3,
    'constant_total_length':'PASS_ANALYTICAL_SAME_MATERIAL_PARAMETER_FAMILY',
    'continuous_solids_and_packing':'NOT_TESTED','contact_handling_margin':'BLOCKED',
    'terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-ap_started}
(AP_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('APEX_REVISION_DONE',report['status'],ap_selected,flush=True)
