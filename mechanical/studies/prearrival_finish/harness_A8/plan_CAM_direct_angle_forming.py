"""Finite forming search with an independently controlled lateral rotation.

The earlier sine window forced the side angle to nearly zero at f=.925.
Here the physical side angle is a free temporary assembly coordinate. It
must be zero at both ends. Length, wire OD, final shape and source solids
are unchanged. Every earlier/later wire remains present in the check.
This is a path search, not a continuous or hardware qualification.
"""
from pathlib import Path
DA_SCRIPT=Path(__file__).resolve();DA_ROOT=DA_SCRIPT.parent
DA_HELPER=DA_ROOT/'plan_CAM_one_wire_forming_envelope.py';__file__=str(DA_HELPER)
exec(compile(DA_HELPER.read_text().split('\n# First compare the configuration',1)[0],str(DA_HELPER),'exec'),globals())
__file__=str(DA_SCRIPT)
DA_OUT=L2_OUT/'direct_angle_forming';DA_OUT.mkdir(exist_ok=True)
da_started=time.time();da_cache={};da_checks=0;da_curves={};da_stages=[];da_attempts=[];da_failure=None
da_order=(0,1,2,3)


def st_rotation(f):
    angle=math.radians(st_angle_max);c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]]),float(st_angle_max)


def da_check(stage,f,amp,angle):
    global da_checks
    key=(stage,round(f,10),round(amp,8),round(angle,8))
    if key not in da_cache:
        da_cache[key]=oe_check(amp,angle,stage,f,da_order);da_checks+=1
    return da_cache[key]


da_grid=[(a,b) for a in [0.,3.,6.,7.5,9.,10.5,12.,13.5,15.,18.,21.,24.]
                  for b in [0.,6.,12.,18.,24.,30.,36.,42.,48.,54.,60.,66.,72.,78.,84.,90.]]
for stage in range(4):
    old_t=0.;old=(9.,0.);path=[{'fraction':0.,'amplitude_mm':old[0],'side_angle_deg':old[1]}]
    first,_=da_check(stage,0.,*old);assert first['status']=='PASS',first
    for t in np.linspace(.025,1.,40):
        t=round(float(t),8);found=None;attempts=[]
        grid=da_grid if t<1. else [(a,0.) for a in [9.,12.,6.,15.,3.,18.,0.,21.,24.]]
        # Prefer a small physical change, with a mild preference for returning
        # toward the final orientation. Never force the old sine timetable.
        candidates=list(dict.fromkeys(([old] if t<1. else [])+sorted(grid,
            key=lambda q:((q[0]-old[0])/3.)**2+((q[1]-old[1])/12.)**2+(q[1]/90.)**2)))
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
        da_attempts.append({'stage':stage,'fraction':t,'failed_controls':attempts})
        if found is None:
            da_failure={'stage':stage,'fraction':t,'previous_fraction':old_t,'previous_controls':old,'tested_candidates':len(candidates)}
            print('DIRECT_ANGLE_NO_EDGE',da_failure,flush=True);break
        amp,angle,p,edge=found
        path.append({'fraction':t,'amplitude_mm':amp,'side_angle_deg':angle,'finite_edge_checks':edge})
        da_curves[f'stage{stage}_f{t:.6f}']=p
        print('DIRECT_ANGLE',stage,t,amp,angle,'discarded',len(attempts),'checks',da_checks,'sec',round(time.time()-da_started,1),flush=True)
        old_t=t;old=(amp,angle)
    da_stages.append({'stage':stage,'active_slot':da_order[stage],
        'status':'PASS' if path[-1]['fraction']==1. else 'BLOCKED','path':path})
    if da_failure:break
np.savez_compressed(DA_OUT/'curves.npz',**da_curves)
complete=len(da_stages)==4 and all(s['status']=='PASS' for s in da_stages)
report={'status':'PASS' if complete else 'BLOCKED',
    'scope':'Finite greedy one-wire forming search with independent actual lateral angle; quarter/midpoint edge checks',
    'source_main_sha256':source_hash,'script_sha256':sha(DA_SCRIPT),'helper_sha256':sha(DA_HELPER),
    'source_previous_search_sha256':sha(L2_OUT/'adaptive_forming/screen.json'),
    'stages':da_stages,'attempts':da_attempts,'first_unresolved_step':da_failure,'wire_order':da_order,
    'wire_OD_mm':OD,'surface_clearance_mm':.3,'finite_checks':da_checks,
    'controller_interpolation':'Linear fraction, lift amplitude and actual side angle between waypoints; no imposed sine angle window',
    'curves_sha256':sha(DA_OUT/'curves.npz'),'constant_length':'PASS_ANALYTICAL_RIGID_ROTATION_OF_CONSTANT_MATERIAL_CURVE',
    'continuous_motion':'NOT_TESTED','search_exhaustive':False,'contacts_handling':'NOT_TESTED',
    'terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-da_started}
(DA_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('DIRECT_ANGLE_DONE',report['status'],da_failure,flush=True)
