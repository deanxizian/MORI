"""Replay the four-wire sequence with every nominal bare terminal present.

The path planner checks the active wire and its terminal against structures,
but not all terminal-to-wire pairs. This audit closes that finite-screening
omission, retains the 0.3mm screening result separately from nonpenetration,
and checks the static start/end conductors against the assembly fixtures.
No generic margin is silently reduced to make the sequence pass.
"""
from pathlib import Path
OC_SCRIPT=Path(__file__).resolve();OC_ROOT=OC_SCRIPT.parent
OC_HELPER=OC_ROOT/'plan_CAM_direct_angle_forming.py';__file__=str(OC_HELPER)
exec(compile(OC_HELPER.read_text().split('\nda_grid=',1)[0],str(OC_HELPER),'exec'),globals())
__file__=str(OC_SCRIPT)
OC_OUT=L2_OUT/'outer_first_forming';oc_path=json.loads((OC_OUT/'screen.json').read_text())
assert oc_path['status']=='PASS' and oc_path['source_main_sha256']==source_hash
oc_order=tuple(oc_path['wire_order']);oc_started=time.time();oc_rows=[];oc_static=[]
oc_saved=np.load(OC_OUT/'curves.npz');oc_max_identity=0.
for slot in range(4):
    for phase in [0.,1.]:
        st_angle_max=0.;fc_amplitude=9.;p,u,e,_=oe_static[slot,phase]
        hit=ow_active_solids(slot,phase,p,u,e)
        oc_static.append({'slot':slot,'phase':phase,'status':'PASS' if hit is None else 'BLOCKED','failure':hit})

for stage_row in oc_path['stages']:
    stage=stage_row['stage'];active=oc_order[stage]
    for node in stage_row['path']:
        f=node['fraction'];st_angle_max=node['side_angle_deg'];fc_amplitude=node['amplitude_mm']
        base,u,e=fc_curve(f);curves=[];contacts=[];params=[];errors=[]
        key=f'stage{stage}_f{f:.6f}'
        if key in oc_saved:
            actual=base+[xx[active]-xx[0],0.,0.]
            oc_max_identity=max(oc_max_identity,float(np.linalg.norm(actual-oc_saved[key],axis=1).max()))
        for slot in range(4):
            phase=f if slot==active else (1. if oc_order.index(slot)<stage else 0.)
            angle=node['side_angle_deg'] if slot==active else 0.
            if slot==active:p=base+[xx[slot]-xx[0],0.,0.];v=u;err=e
            else:p,v,err,_=oe_static[slot,phase]
            curves.append(p);params.append(v);errors.append(err)
            st_angle_max=angle;_,tr=ft_frame(phase,p[-1])
            contacts.append(pw_obstacle(f'bare_contact_{slot}','free',ft_box.transform(tr)))
        wire_rows=[];contact_rows=[]
        for slot in range(4):
            for other,target in enumerate(contacts):
                # Only a short local interval at its own crimp is excluded.
                # Nonlocal portions and every other wire remain in the test.
                keep=params[slot]<=fc_end-2. if slot==other else np.ones(len(params[slot]),bool)
                p=curves[slot][keep];hits={}
                for margin in [0.,.3]:
                    hits[str(margin)]=fc_wire_check(p,errors[slot],np.zeros(len(p)),target,margin)
                wire_rows.append({'wire_slot':slot,'contact_slot':other,
                    'nonpenetration':'PASS' if hits['0.0'] is None else 'BLOCKED',
                    'clearance_0_3mm':'PASS' if hits['0.3'] is None else 'BLOCKED','failures':hits})
            for name,sample,err in [('yaw_fan',pw_fans[slot],pw_fan_errors[slot]),
                                    ('body_prefix',body_samples[slot+1,0],body_error)]:
                for other,target in enumerate(contacts):
                    p=sample[0];hits={}
                    for margin in [0.,.3]:hits[str(margin)]=fc_wire_check(p,err,np.zeros(len(p)),target,margin)
                    wire_rows.append({'wire_group':name,'wire_slot':slot,'contact_slot':other,
                        'nonpenetration':'PASS' if hits['0.0'] is None else 'BLOCKED',
                        'clearance_0_3mm':'PASS' if hits['0.3'] is None else 'BLOCKED','failures':hits})
        for a,b in itertools.combinations(range(4),2):
            ma,mb=contacts[a][2],contacts[b][2]
            volume=max(0.,float((ma^mb).volume()));gap=float(ma.min_gap(mb,2.))
            contact_rows.append({'slots':[a,b],'intersection_mm3':volume,'gap_capped_2mm':gap,
                'nonpenetration':'PASS' if volume<1e-7 else 'BLOCKED',
                'clearance_0_3mm':'PASS' if volume<1e-7 and gap>=.3-1e-6 else 'BLOCKED'})
        nonpenetration=all(r['nonpenetration']=='PASS' for r in wire_rows+contact_rows)
        margin=all(r['clearance_0_3mm']=='PASS' for r in wire_rows+contact_rows)
        oc_rows.append({'stage':stage,'active_slot':active,'fraction':f,
            'amplitude_mm':node['amplitude_mm'],'side_angle_deg':node['side_angle_deg'],
            'nominal_nonpenetration':'PASS' if nonpenetration else 'BLOCKED',
            'clearance_0_3mm':'PASS' if margin else 'BLOCKED','wire_contact_checks':wire_rows,'contact_pairs':contact_rows})
        print('OUTER_FIRST_CONTACTS',stage,f,oc_rows[-1]['nominal_nonpenetration'],oc_rows[-1]['clearance_0_3mm'],flush=True)
assert oc_max_identity<1e-8
nominal=all(r['nominal_nonpenetration']=='PASS' for r in oc_rows) and all(r['status']=='PASS' for r in oc_static)
margin=all(r['clearance_0_3mm']=='PASS' for r in oc_rows)
report={'status':'PASS' if nominal and margin else 'BLOCKED',
    'scope':'Finite waypoint check of all nominal contacts versus every free/upstream/body CAM conductor and each other',
    'source_main_sha256':source_hash,'script_sha256':sha(OC_SCRIPT),'helper_sha256':sha(OC_HELPER),
    'source_path_sha256':sha(OC_OUT/'screen.json'),'nominal_nonpenetration':'PASS' if nominal else 'BLOCKED',
    'clearance_0_3mm':'PASS' if margin else 'BLOCKED','rows':oc_rows,'static_wire_fixture_checks':oc_static,
    'saved_path_replay_maximum_mm':oc_max_identity,'waypoint_count':len(oc_rows),
    'contact_dimensions_mm':ft_dims.tolist(),'contact_shape_evidence':fc_terminal['contact_shape_evidence'],
    'own_crimp_local_arc_exclusion_mm':2.,'continuous_motion':'NOT_TESTED','real_contact_compatibility':'NOT_TESTED',
    'terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-oc_started}
(OC_OUT/'contacts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('OUTER_FIRST_CONTACTS_DONE',report['status'],report['nominal_nonpenetration'],len(oc_rows),flush=True)
