"""Screen a local return corridor without changing final wires or hardware.

Uses the complete existing wire/contact/structure checks. Dense positions
are a search aid; only a later adaptive audit can cover intervals.
"""
from pathlib import Path
RC_SCRIPT=Path(__file__).resolve();RC_ROOT=RC_SCRIPT.parent
RC_HELPER=RC_ROOT/'refine_CAM_outer_contact_path.py';__file__=str(RC_HELPER)
exec(compile(RC_HELPER.read_text().split('\ntc_grid=',1)[0],str(RC_HELPER),'exec'),globals())
__file__=str(RC_SCRIPT)
RC_OUT=TC_OUT/'return_corridor';RC_OUT.mkdir(exist_ok=True)
rc_started=time.time();rows=[];path=[];failed=None
# Work backwards from the already stored final straight return. Use shorter
# edges through the previously missed angular crossing, and vary loop height
# rather than tolerating contact with an upstream conductor.
old_t=.875;old=(9.,0.);r,_=tc_check(3,old_t,*old);assert r['status']=='PASS'
path.append({'fraction':old_t,'amplitude_mm':old[0],'side_angle_deg':old[1]})
for t in np.linspace(.8725,.8,30):
    t=round(float(t),8)
    grid=[(a,b) for a in [9.,10.5,12.,13.5,15.,18.,21.,24.,7.5,6.,3.,0.]
          for b in [0.,3.,6.,9.,12.,18.,24.,30.,36.,42.,48.,54.,60.,-3.,-6.,-12.]]
    # The last boundary must connect exactly with the known finite path.
    if t==.8:grid=[(10.5,48.)]
    else:grid=list(dict.fromkeys([old]+sorted(grid,key=lambda q:((q[0]-old[0])/3.)**2+((q[1]-old[1])/12.)**2)))
    tries=[];found=None
    for amp,angle in grid:
        node,p=tc_check(3,t,amp,angle)
        if node['status']!='PASS':tries.append({'controls':[amp,angle],'failure':node});continue
        edge=[];ok=True
        for mix in [.25,.5,.75]:
            f=old_t+(t-old_t)*mix;a=old[0]+(amp-old[0])*mix;b=old[1]+(angle-old[1])*mix
            mid,_=tc_check(3,f,a,b);edge.append({'fraction':f,'amplitude_mm':a,'side_angle_deg':b,**mid})
            if mid['status']!='PASS':ok=False;break
        if not ok:tries.append({'controls':[amp,angle],'failure':edge[-1]});continue
        found=(amp,angle,edge);break
    rows.append({'fraction':t,'discarded_controls':tries})
    if found is None:
        failed={'fraction':t,'next_fraction':old_t,'next_controls':old,'tested':len(grid)};break
    amp,angle,edge=found;path.append({'fraction':t,'amplitude_mm':amp,'side_angle_deg':angle,'finite_edge_checks_to_next':edge})
    print('RETURN_CORRIDOR',t,amp,angle,'discarded',len(tries),'checks',tc_checks,'sec',round(time.time()-rc_started,1),flush=True)
    old_t=t;old=(amp,angle)
report={'status':'PASS' if failed is None else 'BLOCKED','scope':'Dense finite local return only, with all other wires and contacts retained',
    'source_main_sha256':source_hash,'script_sha256':sha(RC_SCRIPT),'helper_sha256':sha(RC_HELPER),
    'source_path_sha256':sha(TC_OUT/'screen.json'),'source_failure_sha256':sha(TC_OUT/'continuous/screen.json'),
    'stage':3,'path':list(reversed(path)),'attempts':rows,'unresolved':failed,'evaluated_states':tc_checks,
    'ordinary_margin_mm':.3,'bare_contact_margin_mm':0.,'continuous_motion':'NOT_TESTED','main_applied':False,
    'elapsed_s':time.time()-rc_started}
(RC_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('RETURN_CORRIDOR_DONE',report['status'],failed,flush=True)
