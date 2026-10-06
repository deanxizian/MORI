"""Finite packing screen of the +2mm forming family, preserving failures.

Check wires, upstream CAM conductors and nominal contacts separately. The
catalogue contact-box-to-neighbour gap must not be hidden by a wire PASS.
This assembly screen holds the robot at zero yaw/pitch; it is not motion QA.
"""
from pathlib import Path
FP_SCRIPT=Path(__file__).resolve();FP_ROOT=FP_SCRIPT.parent
FP_HELPER=FP_ROOT/'check_CAM_forming_lift2_continuous.py';__file__=str(FP_HELPER)
exec(compile(FP_HELPER.read_text().split('\n# Independently generated finite curves',1)[0],str(FP_HELPER),'exec'),globals())
__file__=str(FP_SCRIPT)
fp_started=time.time();fp_rows=[];fp_contact_rows=[]
for fraction in np.linspace(0.,1.,41):
    fraction=float(fraction);base,u,error=fc_curve(fraction);samples=[];contacts=[];results=[]
    for slot in range(4):
        p=base+[xx[slot]-xx[0],0.,0.];sm=fine(p,.01);samples.append(sm)
        result=self_check(sm,error);results.append({'kind':'wire_self','slot':slot,**result})
        for other in range(4):
            r=own_prefix_check(sm,pw_fans[other],error,pw_fan_errors[other]) if other==slot else pair(sm,pw_fans[other],error,pw_fan_errors[other])
            results.append({'kind':'wire_to_yaw_fan','slot':slot,'other_slot':other,**r})
            r=pair(sm,body_samples[other+1,0],error,body_error)
            results.append({'kind':'wire_to_body_prefix','slot':slot,'other_slot':other,**r})
        _,tr=ft_frame(fraction,p[-1]);contacts.append(pw_obstacle(f'bare_contact_{slot}','free',ft_box.transform(tr)))
    for a,b in itertools.combinations(range(4),2):
        results.append({'kind':'wire_pair','slots':[a,b],**pair(samples[a],samples[b],error,error)})
    contact_checks=[]
    for slot in range(4):
        for other,target in enumerate(contacts):
            p=base+[xx[slot]-xx[0],0.,0.];parameter=u
            if slot==other:
                # The last2mm reaches its own crimp by definition. Keep
                # the nonlocal return and all other wires fully checked.
                mask=u<=fc_end-2.;p=p[mask];parameter=u[mask]
            hits={}
            for margin in [0.,.3]:
                h=fc_wire_check(p,error,np.zeros(len(p)),target,margin)
                hits[str(margin)]=h
            contact_checks.append({'wire_slot':slot,'contact_slot':other,
                'nonpenetration':'PASS' if not hits['0.0'] else 'BLOCKED',
                'clearance_0_3mm':'PASS' if not hits['0.3'] else 'BLOCKED','hits':hits})
    fp_rows.append({'fraction':fraction,'status':'PASS' if all(r['status']=='PASS' for r in results) else 'BLOCKED','checks':results})
    fp_contact_rows.append({'fraction':fraction,'checks':contact_checks})
    print('LIFT2_FORMING_PACK',fraction,fp_rows[-1]['status'],'contact physical failures',sum(r['nonpenetration']!='PASS' for r in contact_checks),flush=True)
wirepass=all(r['status']=='PASS' for r in fp_rows)
contactpass=all(x['nonpenetration']=='PASS' for r in fp_contact_rows for x in r['checks'])
report={'status':'BLOCKED','scope':'Finite41-position packing screen; nominal contacts fail0.3mm mutual margin',
    'source_main_sha256':source_hash,'script_sha256':sha(FP_SCRIPT),'helper_sha256':sha(FP_HELPER),
    'source_finite_screen_sha256':sha(L2_OUT/'screen.json'),
    'wire_packing_status':'PASS' if wirepass else 'BLOCKED','wire_rows':fp_rows,
    'contact_to_wire_nonpenetration':'PASS' if contactpass else 'BLOCKED','contact_rows':fp_contact_rows,
    'contact_to_contact_gap_mm':1.-ft_dims[0],'contact_to_contact_nonpenetration':'PASS_ANALYTICAL',
    'contact_to_contact_0_3mm_margin':'BLOCKED','assembly_yaw_pitch_deg':[0.,0.],
    'wire_OD_mm':OD,'required_surface_clearance_mm':.3,'same_wire_local_arc_exclusion_mm':2.,
    'own_crimp_local_arc_exclusion_mm':2.,'continuous_packing':'NOT_TESTED',
    'contact_shape_evidence':fc_terminal['contact_shape_evidence'],
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-fp_started}
(L2_OUT/'packing_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LIFT2_FORMING_PACK_DONE',report['wire_packing_status'],report['contact_to_wire_nonpenetration'],flush=True)
