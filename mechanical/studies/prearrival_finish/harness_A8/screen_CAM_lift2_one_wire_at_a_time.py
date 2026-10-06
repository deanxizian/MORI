"""Screen a physical order: form the four free conductors one at a time.

Completed conductors stay in the+2mm shape, unformed ones stay upright. No
wire disappears from the collision checks while another wire is formed.
The nominal bare-contact handling issue remains separately unresolved.
"""
from pathlib import Path
OW_SCRIPT=Path(__file__).resolve();OW_ROOT=OW_SCRIPT.parent
OW_HELPER=OW_ROOT/'screen_CAM_lift2_forming_side_turn.py';__file__=str(OW_HELPER)
exec(compile(OW_HELPER.read_text().split('\nst_order=',1)[0],str(OW_HELPER),'exec'),globals())
__file__=str(OW_SCRIPT)
OW_OUT=L2_OUT/'one_wire_at_a_time';OW_OUT.mkdir(exist_ok=True);ow_started=time.time()
ow_order=list(dict.fromkeys([.8,.775,.825,.75,.85,.725,.7,.875,.9,.95,1.,0.]+[round(float(x),8) for x in np.linspace(0.,1.,41)]))


def ow_active_solids(slot,t,p,u,error):
    _,tr=ft_frame(t,p[-1]);r=ft_source(ft_box.transform(tr))
    if r['status']!='PASS':return {'kind':'active_contact',**r}
    for target in fc_targets:
        name=target[0]
        if name in fc_root_contacts:pieces=[(u>=4.3-1e-9,.3)]
        elif name=='CAM_bed_only':pieces=[(u<=fc_seat_start+1e-9,.3),
            ((u>=fc_seat_start-1e-9)&(u<=fc_seat_end+1e-9),0.),(u>=fc_seat_end-1e-9,.3)]
        else:pieces=[(np.ones(len(u),bool),.3)]
        for mask,margin in pieces:
            q=p[mask];hit=fc_wire_check(q,error,np.zeros(len(q)),target,margin)
            if hit:return {'kind':'active_wire',**hit}
    return None


ow_trials=[];ow_selected=None;ow_saved={}
for angle,order in [(24.,[0,1,2,3]),(32.,[0,1,2,3]),(40.,[0,1,2,3]),(-24.,[3,2,1,0])]:
    st_angle_max=angle;fc_amplitude=9.;rows=[];saved={};failed=False
    # Failure-prone fractions first, across every stage, then the remainder.
    for t in ow_order:
        for stage,slot in enumerate(order):
            phases=[1. if order.index(i)<stage else 0. for i in range(4)];phases[slot]=t
            curves=[];samples=[];errors=[];parameters=[]
            for other,f in enumerate(phases):
                p,u,e=fc_curve(f);p=p+[xx[other]-xx[0],0.,0.]
                curves.append(p);parameters.append(u);errors.append(e);samples.append(fine(p,.01))
            hit=ow_active_solids(slot,t,curves[slot],parameters[slot],errors[slot]);checks=[]
            if hit is None:
                sm=samples[slot];e=errors[slot]
                r=self_check(sm,e);checks.append({'kind':'self',**r})
                for other in range(4):
                    r=own_prefix_check(sm,pw_fans[other],e,pw_fan_errors[other]) if other==slot else pair(sm,pw_fans[other],e,pw_fan_errors[other])
                    checks.append({'kind':'yaw_fan','other_slot':other,**r})
                    r=pair(sm,body_samples[other+1,0],e,body_error);checks.append({'kind':'body_prefix','other_slot':other,**r})
                    if other!=slot:checks.append({'kind':'other_free_wire','other_slot':other,**pair(sm,samples[other],e,errors[other])})
            ok=hit is None and all(r['status']=='PASS' for r in checks)
            row={'stage':stage,'active_slot':slot,'fraction':t,'phases':phases,'status':'PASS' if ok else 'BLOCKED','solids_failure':hit,'packing':checks}
            rows.append(row)
            print('ONE_AT_A_TIME',angle,stage,t,row['status'],hit,[r for r in checks if r['status']!='PASS'][:2],flush=True)
            if not ok:failed=True;break
            for other,p in enumerate(curves):saved[f'stage{stage}_f{t:.6f}_slot{other}']=p
        if failed:break
    good=not failed and len(rows)==len(ow_order)*4
    ow_trials.append({'maximum_side_angle_deg':angle,'wire_order':order,'status':'PASS' if good else 'BLOCKED','rows':rows})
    if good:ow_selected={'maximum_side_angle_deg':angle,'wire_order':order};ow_saved=saved;break
if ow_saved:np.savez_compressed(OW_OUT/'curves.npz',**ow_saved)
report={'status':'PASS' if ow_selected else 'BLOCKED','scope':'Finite one-conductor-at-a-time motion; all other conductors remain present',
    'source_main_sha256':source_hash,'script_sha256':sha(OW_SCRIPT),'helper_sha256':sha(OW_HELPER),
    'source_failed_side_turn_sha256':sha(ST_OUT/'screen.json'),'selected':ow_selected,'planned_fractions':ow_order,'trials':ow_trials,
    'curves_sha256':sha(OW_OUT/'curves.npz') if ow_saved else None,'final_plug_lift_mm':2.,'apex_amplitude_mm':9.,
    'wire_clearance_mm':.3,'continuous_motion':'NOT_TESTED','contact_handling_margin':'BLOCKED',
    'static_free_wires_to_solids':'NOT_TESTED_SEPARATE_SCOPE','wire_to_contact':'NOT_TESTED','contact_to_contact':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-ow_started}
(OW_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ONE_WIRE_SEQUENCE_DONE',report['status'],ow_selected,flush=True)
