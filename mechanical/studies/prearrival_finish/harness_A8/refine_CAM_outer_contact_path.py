"""Refine the final wire's path with nominal bare contacts included.

The four-wire path passed wire screening, but its last contact approaches
three completed tails. Preserve that result and require nonpenetration of
all contact/wire pairs during the final stage. The generic 0.3mm catalogue
terminal packing margin remains a separate unresolved field, not a waiver.
"""
from pathlib import Path
TC_SCRIPT=Path(__file__).resolve();TC_ROOT=TC_SCRIPT.parent
TC_HELPER=TC_ROOT/'plan_CAM_direct_angle_forming.py';__file__=str(TC_HELPER)
exec(compile(TC_HELPER.read_text().split('\nda_grid=',1)[0],str(TC_HELPER),'exec'),globals())
__file__=str(TC_SCRIPT)
TC_SOURCE=L2_OUT/'outer_first_forming';TC_OUT=L2_OUT/'contact_refined_forming';TC_OUT.mkdir(exist_ok=True)
tc_old=json.loads((TC_SOURCE/'screen.json').read_text());assert tc_old['status']=='PASS'
da_order=tuple(tc_old['wire_order']);tc_started=time.time();tc_static={};tc_checks=0;tc_cache={}
for slot in range(4):
    for phase in [0.,1.]:
        st_angle_max=0.;p,u,e,sm=oe_static[slot,phase];_,tr=ft_frame(phase,p[-1])
        tc_static[slot,phase]=pw_obstacle(f'fixed_terminal_{slot}_{phase}','fixed',ft_box.transform(tr))


def tc_contacts(stage,f,amp,angle):
    global st_angle_max,fc_amplitude
    slot=da_order[stage];st_angle_max=angle;fc_amplitude=amp
    p,u,e=fc_curve(f);p=p+[xx[slot]-xx[0],0.,0.]
    _,tr=ft_frame(f,p[-1]);contact=pw_obstacle('active_terminal','moving',ft_box.transform(tr))
    # Active contact versus all free conductors, including its nonlocal own
    # wire, plus all fixed upstream conductors. Static contacts are retained.
    for other in range(4):
        phase=1. if da_order.index(other)<stage else 0.
        if other==slot:q=p[u<=fc_end-2.];qe=e
        else:q,qu,qe,_=oe_static[other,phase]
        hit=fc_wire_check(q,qe,np.zeros(len(q)),contact,0.)
        if hit:return {'status':'BLOCKED','kind':'contact_to_free_wire','other_slot':other,'failure':hit}
        for name,sm,err in [('yaw_fan',pw_fans[other],pw_fan_errors[other]),('body',body_samples[other+1,0],body_error)]:
            q=sm[0];hit=fc_wire_check(q,err,np.zeros(len(q)),contact,0.)
            if hit:return {'status':'BLOCKED','kind':'contact_to_'+name,'other_slot':other,'failure':hit}
        if other!=slot:
            fixed=tc_static[other,phase]
            hit=fc_wire_check(p,e,np.zeros(len(p)),fixed,0.)
            if hit:return {'status':'BLOCKED','kind':'wire_to_static_contact','other_slot':other,'failure':hit}
            volume=max(0.,float((contact[2]^fixed[2]).volume()))
            if volume>1e-7:return {'status':'BLOCKED','kind':'contact_to_contact','other_slot':other,'intersection_mm3':volume}
    return {'status':'PASS','scope':'nominal nonpenetration only; generic0.3mm terminal margin unresolved'}


def tc_check(stage,f,amp,angle):
    global tc_checks
    key=(stage,round(f,10),round(amp,8),round(angle,8))
    if key not in tc_cache:
        tc_checks+=1
        r=tc_contacts(stage,f,amp,angle)
        if r['status']=='PASS':r,p=oe_check(amp,angle,stage,f,da_order)
        else:p=None
        tc_cache[key]=(r,p)
    return tc_cache[key]


tc_grid=[(a,b) for a in [0.,3.,6.,7.5,9.,10.5,12.,13.5,15.,18.,21.,24.]
    for b in [0.,-3.,3.,-6.,6.,-9.,9.,-12.,12.,-18.,18.,-24.,24.,-30.,30.,-36.,36.,-42.,42.,-48.,48.,-54.,54.,-60.,60.]]
stage=3;old_t=1.;old=(9.,0.);path=[{'fraction':1.,'amplitude_mm':9.,'side_angle_deg':0.}]
tc_attempts=[];tc_curves={};tc_failure=None
first,_=tc_check(stage,1.,*old);assert first['status']=='PASS',first
for t in np.linspace(.975,0.,40):
    t=round(float(t),8);found=None;attempts=[]
    inherited=next(n for n in tc_old['stages'][stage]['path'] if abs(n['fraction']-t)<1e-8)
    prior=(inherited['amplitude_mm'],inherited['side_angle_deg'])
    grid=tc_grid if t>0. else [(9.,0.)]
    candidates=list(dict.fromkeys(([prior,old] if t>0. else [])+sorted(grid,
        key=lambda q:((q[0]-old[0])/3.)**2+((q[1]-old[1])/12.)**2)))
    for amp,angle in candidates:
        node,p=tc_check(stage,t,amp,angle)
        if node['status']!='PASS':attempts.append({'controls':[amp,angle],'failure':node});continue
        edge=[];good=True
        for mix in [.25,.5,.75]:
            f=old_t+(t-old_t)*mix;a=old[0]+(amp-old[0])*mix;b=old[1]+(angle-old[1])*mix
            mid,_=tc_check(stage,f,a,b);edge.append({'fraction':f,'amplitude_mm':a,'side_angle_deg':b,**mid})
            if mid['status']!='PASS':good=False;break
        if not good:attempts.append({'controls':[amp,angle],'failure':edge[-1]});continue
        found=(amp,angle,p,edge);break
    tc_attempts.append({'stage':stage,'fraction':t,'failed_controls':attempts})
    if found is None:
        tc_failure={'stage':stage,'fraction':t,'previous_fraction':old_t,'previous_controls':old,'tested_candidates':len(candidates)}
        print('CONTACT_REFINED_NO_EDGE',tc_failure,flush=True);break
    amp,angle,p,edge=found;path.append({'fraction':t,'amplitude_mm':amp,'side_angle_deg':angle,'finite_edge_checks_to_next':edge})
    tc_curves[f'stage{stage}_f{t:.6f}']=p
    print('CONTACT_REFINED',stage,t,amp,angle,'discarded',len(attempts),'checks',tc_checks,'sec',round(time.time()-tc_started,1),flush=True)
    old_t=t;old=(amp,angle)
tc_stages=tc_old['stages'][:3]+[{'stage':stage,'active_slot':da_order[stage],
    'status':'PASS' if path[-1]['fraction']==0. else 'BLOCKED','path':list(reversed(path))}]
complete=all(s['status']=='PASS' for s in tc_stages)
tc_all_contacts=[]
if complete:
    for s in tc_stages:
        for n in s['path']:
            nodes=[n]+n.get('finite_edge_checks_to_next',[])
            for q in nodes:
                r=tc_contacts(s['stage'],q['fraction'],q['amplitude_mm'],q['side_angle_deg'])
                tc_all_contacts.append({'stage':s['stage'],'fraction':q['fraction'],**r})
    complete=all(r['status']=='PASS' for r in tc_all_contacts)
np.savez_compressed(TC_OUT/'curves.npz',**tc_curves)
report={'status':'PASS' if complete else 'BLOCKED','scope':'Four-wire finite path; last stage replanned with all bare contacts, all644 retained positions audited for contact nonpenetration',
    'source_main_sha256':source_hash,'script_sha256':sha(TC_SCRIPT),'helper_sha256':sha(TC_HELPER),
    'source_previous_path_sha256':sha(TC_SOURCE/'screen.json'),'source_previous_contacts_sha256':sha(TC_SOURCE/'contacts.json'),
    'stages':tc_stages,'wire_order':da_order,'attempts':tc_attempts,'first_unresolved_step':tc_failure,
    'new_planning_checks':tc_checks,'all_contact_positions':tc_all_contacts,
    'wire_structure_margin_mm':.3,'contact_structure_margin_mm':.3,'bare_contact_wire_nonpenetration_margin_mm':0.,
    'generic_0_3mm_contact_packing':'BLOCKED','curves_sha256':sha(TC_OUT/'curves.npz'),
    'continuous_motion':'NOT_TESTED','real_contact_compatibility':'NOT_TESTED','terminal_insertion':'NOT_TESTED',
    'feed_to_start':'NOT_TESTED','ties':'NOT_TESTED','main_applied':False,'whole_harness':'BLOCKED',
    'manufacturing_release':False,'elapsed_s':time.time()-tc_started}
(TC_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CONTACT_REFINED_DONE',report['status'],tc_failure,len(tc_all_contacts),flush=True)
