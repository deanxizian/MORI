"""Bound continuous upper-wire clearance during the proposed 42mm lowering.

All added points lie on an existing downward straight from CAM. In the fixed
frame, every intermediate upper-wire shape is a prefix/subset of the h42
shape. In the moving frame, the departure extension is a straight subset;
the original core/tail translate by -h. Translation-distance bounds permit
adaptive continuous checks without pretending samples alone prove clearance.
"""
from pathlib import Path
SC_SCRIPT=Path(__file__).resolve();SC_ROOT=SC_SCRIPT.parent
SC_HELPER=SC_ROOT/'check_CAM_sliding_departure.py';__file__=str(SC_HELPER)
exec(compile(SC_HELPER.read_text().split('\nsd_rows=[];',1)[0],str(SC_HELPER),'exec'),globals())
__file__=str(SC_SCRIPT)
sc_begin=time.time();sc_screen=json.loads((SD_OUT/'screen.json').read_text())
assert sc_screen['status']=='PASS' and len(sc_screen['rows'])==15
sc_contact_names={'CAM_catalogue_housing','CAM_UART_4P','Pitch_Cradle','CAM_connector_tie_head','CAM_connector_tie_band'}
sc_moving=[pw_obstacle(n,'moving',m) for n,m in wi_moving.items()]
sc_fixed=[pw_obstacle(n,'fixed',m) for n,m in wi_fixed.items()]
sc_static=[];sc_paths={}
for slot in range(4):
    core=sd_core0+[xx[slot]-xx[0],0,0];tail=PW_OLD_TAILS[slot]
    split=tail[0]-[0,0,5.]
    k=int(np.argmin(np.linalg.norm(tail-split,axis=1)))
    assert np.linalg.norm(tail[k]-split)<1e-7
    assert np.max(np.abs(tail[:k+1,:2]-tail[0,:2]))<1e-7
    sc_paths[slot]=(core,tail[k:],tail[:k+1],wi_line(split,split-[0,0,42.]))
    # Fixed targets: the maximum extension contains every intermediate path.
    for kind,p,error in [('core',core,sd_meta0['curve_error_mm']),('tail_max',sd_tail(slot,42.),tail_error)]:
        for name,_,m,lo,hi,tree in sc_fixed:
            q=p
            if kind=='core' and name in ['Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band']:
                grip=(abs(q[:,0]-xx[slot])<1e-5)&(abs(q[:,1]+1.5)<1e-5)&(q[:,2]<=234.3+1e-5)&(q[:,2]>=229.9-1e-5)
                q=q[~grip]
            hit=check_one(q,error,lo,hi,m,tree)
            if hit:sc_static.append({'slot':slot,'frame':'fixed','kind':kind,'obstacle':name,**hit})
    # In CAM's own frame the first5mm never moves. All possible additional
    # straight pieces are contained in the longest downward extension.
    for kind,p in [('first5mm',sc_paths[slot][2]),('extension_union',sc_paths[slot][3])]:
        for name,_,m,lo,hi,tree in sc_moving:
            if kind=='first5mm' and name in sc_contact_names:continue
            hit=check_one(p,0.,lo,hi,m,tree)
            if hit:sc_static.append({'slot':slot,'frame':'moving','kind':kind,'obstacle':name,**hit})

sc_intervals=[];sc_failures=[];sc_count=0
def sc_interval(a,b,depth):
    global sc_count
    middle=(a+b)/2;extra=(b-a)/2;failure=None;sc_count+=1
    for slot,(core,tail,_,_) in sc_paths.items():
        for kind,p,error in [('core',core,sd_meta0['curve_error_mm']),('tail_after5mm',tail,tail_error)]:
            local=p-[0,0,middle]
            for name,_,m,lo,hi,tree in sc_moving:
                hit=check_one(local,error+extra,lo,hi,m,tree)
                if hit:failure={'slot':slot,'kind':kind,'obstacle':name,**hit};break
            if failure:break
        if failure:break
    if failure and depth<12:
        sc_interval(a,middle,depth+1);sc_interval(middle,b,depth+1)
    elif failure:
        sc_failures.append({'interval_mm':[a,b],'middle_mm':middle,'translation_allowance_mm':extra,'failure':failure})
    else:sc_intervals.append({'interval_mm':[a,b],'middle_mm':middle,'translation_allowance_mm':extra,'status':'PASS'})
if not sc_static:sc_interval(0.,42.,0)
sc_intervals.sort(key=lambda x:x['interval_mm'][0])
if not sc_failures and not sc_static:
    assert sc_intervals[0]['interval_mm'][0]==0 and sc_intervals[-1]['interval_mm'][1]==42
    assert all(a['interval_mm'][1]==b['interval_mm'][0] for a,b in zip(sc_intervals,sc_intervals[1:]))
sc_max=next(r for r in sc_screen['rows'] if r['lift_mm']==42.)
report={'status':'PASS' if not sc_static and not sc_failures else 'BLOCKED',
    'scope':'Continuous geometry of the four upper CAM wires against fixed/moving solids and stored fixed-route wires, conditional on a42mm body payout per conductor',
    'source_main_sha256':source_hash,'script_sha256':sha(SC_SCRIPT),'helper_sha256':sha(SC_HELPER),
    'screen_sha256':sha(SD_OUT/'screen.json'),'curves_sha256':sha(SD_OUT/'curves.npz'),
    'fixed_and_straight_union_failures':sc_static,'adaptive_intervals':sc_intervals,'unproved_intervals':sc_failures,
    'interval_tests':sc_count,'maximum_translation_mm':42.,'required_surface_gap_mm':.3,
    'maximum_shape_packing_gap_bound_mm':sc_max['minimum_pack_gap_mm'],
    'packing_proof':'All shorter-departure paths are subsets of the maximum path; mutual and nonadjacent self distances cannot decrease on restriction. Uses stored h42 check including neck fan and current body prefix.',
    'moving_obstacle_proof':'In CAM frame original core and tail-after-first5 translate by-h. Distance is1-Lipschitz in h; half interval added to geometric clearance requirement, including chord and point-spacing bounds.',
    'bend_proof':'Only extends a collinear straight; all original bends retained, no new curvature. Does not establish cable force or life.',
    'first5mm_contact_exceptions':sorted(sc_contact_names),
    'body_reserve':'NOT_TESTED','common_PH_housing_motion':'NOT_TESTED',
    'rigid_cradle_continuous_collision':'NOT_TESTED','tie_tightening_sliding_force':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
    'elapsed_s':time.time()-sc_begin}
(SD_OUT/'continuous_upper_wires.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CONTINUOUS_SLIDING_DONE',report['status'],'static',sc_static,'intervals',len(sc_intervals),'unproved',len(sc_failures),'elapsed',time.time()-sc_begin,flush=True)
