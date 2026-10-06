"""Plan backwards from the required final wire placement.

Forward greedy search remained in the wrong side-angle corridor. Starting
from the required endpoint tests a different branch without changing any
source part or accepting a disconnected last step. Saved paths are reversed
back to the physical assembly direction; all checks remain finite.
"""
from pathlib import Path
RA_SCRIPT=Path(__file__).resolve();RA_ROOT=RA_SCRIPT.parent
RA_HELPER=RA_ROOT/'plan_CAM_direct_angle_forming.py';__file__=str(RA_HELPER)
exec(compile(RA_HELPER.read_text().split('\nda_grid=',1)[0],str(RA_HELPER),'exec'),globals())
__file__=str(RA_SCRIPT)
RA_OUT=L2_OUT/'reverse_angle_forming';RA_OUT.mkdir(exist_ok=True)
ra_started=time.time();ra_stages=[];ra_attempts=[];ra_curves={};ra_failure=None
ra_grid=[(a,b) for a in [0.,3.,6.,7.5,9.,10.5,12.,13.5,15.,18.,21.,24.]
    for b in [0.,-3.,3.,-6.,6.,-9.,9.,-12.,12.,-18.,18.,-24.,24.,-30.,30.,-36.,36.,-48.,48.,-60.,60.]]
for stage in range(4):
    old_t=1.;old=(9.,0.);path=[{'fraction':1.,'amplitude_mm':9.,'side_angle_deg':0.}]
    first,_=da_check(stage,1.,*old);assert first['status']=='PASS',first
    for t in np.linspace(.975,0.,40):
        t=round(float(t),8);found=None;attempts=[]
        grid=ra_grid if t>0. else [(a,0.) for a in [9.,12.,6.,15.,3.,18.,0.,21.,24.]]
        candidates=list(dict.fromkeys(([old] if t>0. else [])+sorted(grid,
            key=lambda q:((q[0]-old[0])/3.)**2+((q[1]-old[1])/12.)**2)))
        for amp,angle in candidates:
            node,p=da_check(stage,t,amp,angle)
            if node['status']!='PASS':attempts.append({'controls':[amp,angle],'failure':node});continue
            edge=[];good=True
            for mix in [.25,.5,.75]:
                f=old_t+(t-old_t)*mix;a=old[0]+(amp-old[0])*mix;b=old[1]+(angle-old[1])*mix
                mid,_=da_check(stage,f,a,b);edge.append({'fraction':f,'amplitude_mm':a,'side_angle_deg':b,**mid})
                if mid['status']!='PASS':good=False;break
            if not good:attempts.append({'controls':[amp,angle],'failure':edge[-1]});continue
            found=(amp,angle,p,edge);break
        ra_attempts.append({'stage':stage,'fraction':t,'failed_controls':attempts})
        if found is None:
            ra_failure={'stage':stage,'fraction':t,'previous_fraction':old_t,'previous_controls':old,'tested_candidates':len(candidates)}
            print('REVERSE_ANGLE_NO_EDGE',ra_failure,flush=True);break
        amp,angle,p,edge=found
        path.append({'fraction':t,'amplitude_mm':amp,'side_angle_deg':angle,'finite_edge_checks_to_next':edge})
        ra_curves[f'stage{stage}_f{t:.6f}']=p
        print('REVERSE_ANGLE',stage,t,amp,angle,'discarded',len(attempts),'checks',da_checks,'sec',round(time.time()-ra_started,1),flush=True)
        old_t=t;old=(amp,angle)
    ra_stages.append({'stage':stage,'active_slot':da_order[stage],
        'status':'PASS' if path[-1]['fraction']==0. else 'BLOCKED','path':list(reversed(path))})
    if ra_failure:break
np.savez_compressed(RA_OUT/'curves.npz',**ra_curves)
complete=len(ra_stages)==4 and all(s['status']=='PASS' for s in ra_stages)
report={'status':'PASS' if complete else 'BLOCKED',
    'scope':'Finite reverse greedy search of independent side-angle forming; saved forward assembly order',
    'source_main_sha256':source_hash,'script_sha256':sha(RA_SCRIPT),'helper_sha256':sha(RA_HELPER),
    'source_forward_search_sha256':sha(DA_OUT/'screen.json'),
    'stages':ra_stages,'attempts':ra_attempts,'first_unresolved_step':ra_failure,'wire_order':da_order,
    'wire_OD_mm':OD,'surface_clearance_mm':.3,'finite_checks':da_checks,
    'controller_interpolation':'Linear fraction, amplitude and actual side angle; reverse path orientation does not alter geometry',
    'curves_sha256':sha(RA_OUT/'curves.npz'),'constant_length':'PASS_ANALYTICAL_RIGID_ROTATION_OF_CONSTANT_MATERIAL_CURVE',
    'continuous_motion':'NOT_TESTED','search_exhaustive':False,'contacts_handling':'NOT_TESTED',
    'terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-ra_started}
(RA_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('REVERSE_ANGLE_DONE',report['status'],ra_failure,flush=True)
