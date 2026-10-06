"""Build the last-wire path using continuous interval checks during search.

Do not accept a finite-only jump between separate sides of another wire.
Every retained edge must pass the existing displacement/clearance bounds.
No main geometry, end shape, conductor size or tolerance is changed.
"""
from pathlib import Path
LC_SCRIPT=Path(__file__).resolve();LC_ROOT=LC_SCRIPT.parent
LC_HELPER=LC_ROOT/'check_CAM_sequential_continuous.py';__file__=str(LC_HELPER)
exec(compile(LC_HELPER.read_text().split('\n# Static mixed states',1)[0],str(LC_HELPER),'exec'),globals())
__file__=str(LC_SCRIPT)
LC_OUT=TC_OUT/'last_wire_continuous_search';LC_OUT.mkdir(exist_ok=True)
lc_start=time.time();lc_trials=[];lc_intervals=[];lc_path=[];lc_checks=0;lc_error=None
lc_grid=[(a,b) for a in [9.,10.5,12.,13.5,15.,18.,21.,24.,7.5,6.,3.,0.]
         for b in [0.,-3.,3.,-6.,6.,-9.,9.,-12.,12.,-18.,18.,-24.,24.,-30.,30.,
                   -36.,36.,-42.,42.,-48.,48.,-54.,54.,-60.,60.,-72.,72.,-84.,84.]]
old={'fraction':1.,'amplitude_mm':9.,'side_angle_deg':0.};lc_path.append(old)
for t in np.linspace(.975,0.,40):
    t=round(float(t),8);controls=(old['amplitude_mm'],old['side_angle_deg']);tries=[];found=None
    grid=[(9.,0.)] if t==0. else list(dict.fromkeys([controls]+sorted(lc_grid,
        key=lambda q:((q[0]-controls[0])/3.)**2+((q[1]-controls[1])/12.)**2)))
    for amp,angle in grid:
        node={'fraction':t,'amplitude_mm':amp,'side_angle_deg':angle};edge=(node,old);lc_checks+=1
        nominal=sc_test(3,edge,t,t)
        if nominal:
            tries.append({'controls':[amp,angle],'status':'BLOCKED','nominal':nominal});continue
        sc_passed=[];sc_unproved=[];sc_nominal=[]
        try:
            sc_interval(3,edge,t,old['fraction']);err=None
        except Exception as exc:err=repr(exc)
        if err is not None:
            tries.append({'controls':[amp,angle],'status':'BLOCKED','error':err,
                          'first_unproved':sc_unproved[:1],'passed_subintervals':len(sc_passed)})
            continue
        found=node;lc_intervals+=sc_passed;break
    lc_trials.append({'fraction':t,'rejected_candidates':tries})
    if found is None:
        lc_error={'fraction':t,'next':old,'tested':len(grid)};break
    old=found;lc_path.append(found)
    print('CONTINUOUS_SEARCH_NODE',t,amp,angle,'rejected',len(tries),'retained_intervals',len(lc_intervals),
          'candidate_checks',lc_checks,'seconds',round(time.time()-lc_start,1),flush=True)
    # Save genuine partial progress for interruption/recovery, never PASS.
    (LC_OUT/'progress.json').write_text(json.dumps({'status':'NOT_TESTED','complete':False,
        'path':list(reversed(lc_path)),'accepted_intervals':len(lc_intervals),
        'source_main_sha256':source_hash,'source_script_sha256':sha(LC_SCRIPT)},indent=2)+'\n')
rows=sorted(lc_intervals,key=lambda r:r['interval'][0])
coverage=bool(rows and rows[0]['interval'][0]==0. and rows[-1]['interval'][1]==1.
              and all(a['interval'][1]==b['interval'][0] for a,b in zip(rows,rows[1:])))
good=lc_error is None and coverage
result={'status':'PASS' if good else 'BLOCKED','scope':'Only last wire, other three wires fixed in completed state; adaptive continuous edge search',
    'source_main_sha256':source_hash,'script_sha256':sha(LC_SCRIPT),'helper_sha256':sha(LC_HELPER),
    'source_original_path_sha256':sha(TC_OUT/'screen.json'),
    'path':list(reversed(lc_path)),'accepted_intervals':lc_intervals,'complete_last_wire_coverage':good,
    'candidate_checks':lc_checks,'interval_tests':sc_tests,'attempts':lc_trials,'unresolved':lc_error,
    'ordinary_margin_mm':.3,'bare_contact_margin_mm':0.,'generic_0_3mm_contact_packing':'BLOCKED',
    'first_three_wires_continuous':'NOT_TESTED','terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-lc_start}
(LC_OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CONTINUOUS_SEARCH_DONE',result['status'],len(lc_intervals),lc_error,flush=True)
