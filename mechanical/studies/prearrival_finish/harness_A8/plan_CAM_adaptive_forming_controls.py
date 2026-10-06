"""Find a finite path through temporary height/side-angle controls.

Each stage forms one wire, with already formed and upright neighbours kept
in place. Candidate controls interpolate between waypoints; midpoint checks
are still finite evidence, never continuous qualification. No geometry edit.
"""
from pathlib import Path
AC_SCRIPT=Path(__file__).resolve();AC_ROOT=AC_SCRIPT.parent
AC_HELPER=AC_ROOT/'plan_CAM_one_wire_forming_envelope.py';__file__=str(AC_HELPER)
exec(compile(AC_HELPER.read_text().split('\n# First compare the configuration',1)[0],str(AC_HELPER),'exec'),globals())
__file__=str(AC_SCRIPT)
AC_OUT=L2_OUT/'adaptive_forming';AC_OUT.mkdir(exist_ok=True);ac_started=time.time()
ac_grid=[(a,b) for a in [0.,3.,6.,7.5,9.,10.5,12.,13.5,15.,18.,21.,24.] for b in [0.,8.,16.,24.,32.,40.,48.,56.,64.,72.,80.]]
ac_attempts=[];ac_stages=[];ac_curves={};ac_failed=None;ac_total_checks=0;ac_cache={}


def ac_check(stage,t,amp,angle):
    global ac_total_checks
    key=(stage,round(t,10),round(amp,8),round(angle,8))
    if key not in ac_cache:
        result,p=oe_check(amp,angle,stage,t);ac_total_checks+=1;ac_cache[key]=(result,p)
    return ac_cache[key]


for stage in range(4):
    path=[];old_t=0.;old=(9.,40.);first,_=ac_check(stage,0.,*old)
    assert first['status']=='PASS',first
    path.append({'fraction':0.,'amplitude_mm':old[0],'maximum_side_angle_deg':old[1]})
    for t in np.linspace(.025,1.,40):
        t=round(float(t),8);found=None;attempts=[]
        candidates=list(dict.fromkeys([old]+sorted(ac_grid,key=lambda q:((q[0]-old[0])/3.)**2+((q[1]-old[1])/16.)**2)))
        for amp,angle in candidates:
            node,p=ac_check(stage,t,amp,angle)
            if node['status']!='PASS':attempts.append({'controls':[amp,angle],'failure':node});continue
            edge=[];edge_ok=True
            for mix in [.25,.5,.75]:
                f=old_t+(t-old_t)*mix;a=old[0]+(amp-old[0])*mix;b=old[1]+(angle-old[1])*mix
                mid,mp=ac_check(stage,f,a,b)
                edge.append({'fraction':f,'amplitude_mm':a,'maximum_side_angle_deg':b,**mid})
                if mid['status']!='PASS':edge_ok=False;break
            if not edge_ok:attempts.append({'controls':[amp,angle],'failure':edge[-1]});continue
            found=(amp,angle,p,edge);break
        ac_attempts.append({'stage':stage,'fraction':t,'failed_controls':attempts})
        if found is None:
            ac_failed={'stage':stage,'fraction':t,'previous_controls':old,'tested_candidates':len(candidates)}
            print('ADAPTIVE_FORMING_NO_EDGE',ac_failed,flush=True);break
        amp,angle,p,edge=found
        path.append({'fraction':t,'amplitude_mm':amp,'maximum_side_angle_deg':angle,'finite_edge_checks':edge})
        ac_curves[f'stage{stage}_f{t:.6f}']=p
        print('ADAPTIVE_FORMING',stage,t,amp,angle,'discarded',len(attempts),'checks',ac_total_checks,'sec',round(time.time()-ac_started,1),flush=True)
        old_t=t;old=(amp,angle)
    ac_stages.append({'stage':stage,'active_slot':stage,'status':'PASS' if path[-1]['fraction']==1. else 'BLOCKED','path':path})
    if ac_failed:break
np.savez_compressed(AC_OUT/'partial_curves.npz',**ac_curves)
complete=len(ac_stages)==4 and all(s['status']=='PASS' for s in ac_stages)
report={'status':'PASS' if complete else 'BLOCKED','scope':'Finite greedy search with quarter/midpoint edge checks; no continuous or completeness proof',
    'source_main_sha256':source_hash,'script_sha256':sha(AC_SCRIPT),'helper_sha256':sha(AC_HELPER),
    'source_fixed_workspace_sha256':sha(OE_OUT/'screen.json'),'stages':ac_stages,'attempts':ac_attempts,'first_unresolved_step':ac_failed,
    'wire_order':[0,1,2,3],'wire_OD_mm':OD,'surface_clearance_mm':.3,'finite_checks':ac_total_checks,
    'controller_interpolation':'Linear interpolation of amplitude and maximum_side_angle between stage waypoints; inherited sine lateral window',
    'curves_sha256':sha(AC_OUT/'partial_curves.npz'),'continuous_motion':'NOT_TESTED','search_exhaustive':False,
    'contacts_handling':'NOT_TESTED','terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-ac_started}
(AC_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ADAPTIVE_FORMING_DONE',report['status'],ac_failed,flush=True)
