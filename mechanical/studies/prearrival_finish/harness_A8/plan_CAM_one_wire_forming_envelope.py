"""Couple temporary loop height and lateral angle for one-wire assembly.

Earlier tests changed one parameter at a time. Preserve those failures and
test a combined workspace change without modifying the resting wire shape,
any source part, a wire diameter or a required clearance. Cache the genuinely
fixed unformed/completed conductors; never omit them from packing checks.
"""
from pathlib import Path
OE_SCRIPT=Path(__file__).resolve();OE_ROOT=OE_SCRIPT.parent
OE_HELPER=OE_ROOT/'screen_CAM_lift2_one_wire_at_a_time.py';__file__=str(OE_HELPER)
exec(compile(OE_HELPER.read_text().split('\now_trials=[];',1)[0],str(OE_HELPER),'exec'),globals())
__file__=str(OE_SCRIPT)
OE_OUT=L2_OUT/'one_wire_workspace';OE_OUT.mkdir(exist_ok=True);oe_started=time.time()
oe_static={};oe_rows=[];oe_selected=None;oe_saved={};oe_tests=0
for phase in [0.,1.]:
    p,u,e=fc_curve(phase)
    for slot in range(4):
        q=p+[xx[slot]-xx[0],0.,0.]
        oe_static[slot,phase]=(q,u,e,fine(q,.01))


def oe_check(amp,angle,stage,t,order=(0,1,2,3)):
    global st_angle_max,fc_amplitude,oe_tests
    st_angle_max=angle;fc_amplitude=amp;slot=order[stage];oe_tests+=1
    p,u,e=fc_curve(t);p=p+[xx[slot]-xx[0],0.,0.]
    hit=ow_active_solids(slot,t,p,u,e)
    if hit:return {'status':'BLOCKED','kind':'solids','failure':hit},None
    sm=fine(p,.01);checks=[]
    r=self_check(sm,e);checks.append({'kind':'self',**r})
    if r['status']!='PASS':return {'status':'BLOCKED','kind':'packing','failure':checks[-1]},None
    for other in range(4):
        r=own_prefix_check(sm,pw_fans[other],e,pw_fan_errors[other]) if other==slot else pair(sm,pw_fans[other],e,pw_fan_errors[other])
        checks.append({'kind':'yaw_fan','other_slot':other,**r})
        if r['status']!='PASS':return {'status':'BLOCKED','kind':'packing','failure':checks[-1]},None
        r=pair(sm,body_samples[other+1,0],e,body_error);checks.append({'kind':'body_prefix','other_slot':other,**r})
        if r['status']!='PASS':return {'status':'BLOCKED','kind':'packing','failure':checks[-1]},None
        if other!=slot:
            phase=1. if order.index(other)<stage else 0.;q,qu,qe,qsm=oe_static[other,phase]
            r=pair(sm,qsm,e,qe);checks.append({'kind':'other_free_wire','other_slot':other,'phase':phase,**r})
            if r['status']!='PASS':
                i,j=r['sample_indices'];checks[-1].update(active_point_mm=sm[0][i].tolist(),other_point_mm=qsm[0][j].tolist())
                return {'status':'BLOCKED','kind':'packing','failure':checks[-1]},None
    return {'status':'PASS','checks':checks},p


# First compare the configuration that previously hit a completed wire.
# A candidate is retained only after every prescribed stage position passes.
oe_grid=[(a,b) for a in [12.,15.,18.,21.,24.,9.] for b in [40.,32.,48.,56.,64.,24.]]
oe_cases=list(dict.fromkeys([(1,.825),(1,.8),(0,.8),(2,.825),(3,.825),
    *[(stage,t) for t in [.75,.775,.85,.875,.9,.925,.95,.975] for stage in range(4)],
    *[(stage,round(float(t),8)) for t in np.linspace(0.,1.,41) for stage in range(4)]]))
for amp,angle in oe_grid:
    rows=[];saved={}
    for stage,t in oe_cases:
        result,p=oe_check(amp,angle,stage,t);rows.append({'stage':stage,'active_slot':stage,'fraction':t,**result})
        if result['status']!='PASS':break
        saved[f'stage{stage}_f{t:.6f}']=p
        if len(rows)%40==0:print('WORKSPACE_SCREEN_PROGRESS',amp,angle,len(rows),flush=True)
    good=len(rows)==len(oe_cases) and all(r['status']=='PASS' for r in rows)
    oe_rows.append({'amplitude_mm':amp,'maximum_side_angle_deg':angle,'wire_order':[0,1,2,3],
        'status':'PASS' if good else 'BLOCKED','rows':rows})
    print('WORKSPACE_SCREEN',amp,angle,oe_rows[-1]['status'],len(rows),rows[-1].get('failure'),round(time.time()-oe_started,1),flush=True)
    if good:oe_selected={'amplitude_mm':amp,'maximum_side_angle_deg':angle,'wire_order':[0,1,2,3]};oe_saved=saved;break
if oe_saved:np.savez_compressed(OE_OUT/'curves.npz',**oe_saved)
report={'status':'PASS' if oe_selected else 'BLOCKED','scope':'Finite coupled height/lateral-angle one-wire sequence with all other conductors present',
    'source_main_sha256':source_hash,'script_sha256':sha(OE_SCRIPT),'helper_sha256':sha(OE_HELPER),
    'source_previous_trial_sha256':sha(OW_OUT/'screen.json'),'selected':oe_selected,'trials':oe_rows,
    'planned_cases':[{'stage':s,'fraction':t} for s,t in oe_cases],'candidate_grid':oe_grid,
    'curves_sha256':sha(OE_OUT/'curves.npz') if oe_saved else None,'evaluated_states':oe_tests,
    'final_plug_lift_mm':2.,'assembly_yaw_pitch_deg':[0.,0.],'wire_OD_mm':OD,'required_surface_clearance_mm':.3,
    'constant_length':'PASS_ANALYTICAL_RIGID_ROTATION_OF_CONSTANT_MATERIAL_CURVE',
    'continuous_motion':'NOT_TESTED','all_contacts_handling':'NOT_TESTED','terminal_insertion':'NOT_TESTED',
    'feed_to_initial_state':'NOT_TESTED','ties':'NOT_TESTED','main_applied':False,'whole_harness':'BLOCKED',
    'manufacturing_release':False,'elapsed_s':time.time()-oe_started}
(OE_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ONE_WIRE_WORKSPACE_DONE',report['status'],oe_selected,flush=True)
