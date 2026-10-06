"""Temporarily lower pin 4's middle plane, retaining tangent R7 bends.

No interfaces or print solids change. Entire source wire lengths remain in
the calculation; the terminal-side stock supplies the temporary extra path.
"""
from pathlib import Path
PULSE_SCRIPT=Path(__file__).resolve()
PULSE_HELPER=PULSE_SCRIPT.parent/'screen_CAM_feed_lift_transition.py'
__file__=str(PULSE_HELPER)
exec(compile(PULSE_HELPER.read_text().split('\nfor pin in range(1,5):',1)[0],str(PULSE_HELPER),'exec'),globals())
__file__=str(PULSE_SCRIPT)
prior_path=OUT/'screen.json';prior=json.loads(prior_path.read_text())
assert prior['script_sha256']==sha(PULSE_HELPER) and prior['status']=='BLOCKED'
for p,digest in prior['source_files'].items():assert sha(PROJECT/p)==digest
OUT=ORDER_OUT/'feed_lift_pulse';OUT.mkdir(exist_ok=True)
base_variant=variant_curve

# The existing offset builder already handles both directions. Its caller
# previously assumed a nonnegative height only when calculating horizontal
# run; change that scalar to absolute height, preserving signed endpoints.
elevated_path=PULSE_SCRIPT.parent/'screen_CAM_elevated_bridge_feed.py'
function_text=elevated_path.read_text().split('\ndef make_elevated_curve(',1)[1].split('\n\nstarted = time.time()',1)[0]
function_text='def make_elevated_curve('+function_text
old='turn = math.acos(1-lift/(2*radius)) if lift <= 2*radius else math.pi/2'
assert function_text.count(old)==1
function_text=function_text.replace(old,'turn = math.acos(1-abs(lift)/(2*radius)) if abs(lift) <= 2*radius else math.pi/2')
exec(compile(function_text,str(elevated_path),'exec'),globals())
base_wire_check=wire_check
clearance_calls=[]
refine_path=PULSE_SCRIPT.parent/'refine_CAM_feed_lift_schedule.py'
refine_functions=refine_path.read_text().split('\ndef densify(',1)[1].split('\nendpoint=next(',1)[0]
exec(compile('def densify('+refine_functions,str(refine_path),'exec'),globals())
rebuild_path=PULSE_SCRIPT.parent/'screen_CAM_feed_lift_schedule.py'
rebuild=rebuild_path.read_text().split('\nfor pin in range(1,4):',1)[1].split('\n# The original pin-4 LSL family',1)[0]
exec(compile('for pin in range(1,4):'+rebuild,str(rebuild_path),'exec'),globals())
active_endpoint=None
amplitude=0.
exponent=1.


def variant_curve(pin,azimuth,bend_radius,family,elevation_fraction):
    if pin==4 and active_endpoint:
        u=float(bt[2,3]/18.)
        source=specifications[pin]['selected'];target=active_endpoint['parameters']
        progress=u**exponent
        azimuth=(1-progress)*source['entry_azimuth_deg']+progress*target['entry_azimuth_deg']
        bend_radius=(1-progress)*source['planar_path']['radius_mm']+progress*target['planar_radius_mm']
        height=-amplitude*math.sin(math.pi*u)
        elevation_fraction=height/(18.*u) if u>1e-12 else 0.
    return base_variant(pin,float(azimuth),float(bend_radius),family,float(elevation_fraction))


endpoint=next(c for c in screen['pools']['4'] if c['candidate_id']=='pin4_3')
pools[4]=[]
for amplitude,exponent in [(.5,1.),(1.,1.),(2.,1.),(3.,1.),(4.,1.),(2.,2.),(4.,2.)]:
    identifier=('pin4_lower_'+str(amplitude)+'_timing_'+str(exponent)).replace('.','p')
    active_endpoint=dict(endpoint,candidate_id=identifier)
    r=check_candidate(4,active_endpoint)
    r.update(temporary_lowering_peak_mm=amplitude,schedule_exponent=exponent,
             lowering_law='-peak * sin(pi * bridge_lift / 18)')
    candidate_results.append(r)
    if r['status']=='PASS':pools[4].append(r)
    print('CAM_LIFT_LOWERING',amplitude,exponent,r['status'],r['passing_positions'],r['failure'],
          round(time.time()-started,2),flush=True)
active_endpoint=None
packing=PULSE_HELPER.read_text().split('\npair_cache = {}',1)[1].split('\nreport=dict(',1)[0]
exec(compile('pair_cache = {}'+packing,str(PULSE_HELPER),'exec'),globals())
report=dict(status='PASS' if chosen else 'BLOCKED',
            scope='Finite temporary-lowering bridge-lift candidate; continuous and later stages unverified',
            script_sha256=sha(PULSE_SCRIPT),helper_sha256=sha(PULSE_HELPER),
            source_files={**prior['source_files'],str(prior_path.relative_to(PROJECT)):sha(prior_path),
                          str(elevated_path.relative_to(PROJECT)):sha(elevated_path),
                          str(refine_path.relative_to(PROJECT)):sha(refine_path),
                          str(rebuild_path.relative_to(PROJECT)):sha(rebuild_path)},
            protected_sources=protected,source_main_sha256=source_hash,
            source_prints=membership['substituted_unadopted_prints'],
            planned_positions=STEPS,sample_spacing_mm=.5,bridge_lift_mm=18.,
            shell_transform=fixed_shell.tolist(),fixed_body_wires=14,CAM_wires=4,
            body_connection_preserved=True,wire_OD_mm=OD,clearance_mm=MARGIN,
            minimum_nominal_radius_mm=7.,minimum_upright_stock_mm=5.,analytic_length_conserved=True,
            terminal_dimensions_ASSUMED_mm=[1.,1.8,4.1],
            results=candidate_results,refined_clearance_calls=clearance_calls,
            search_nodes=search_nodes,selected=chosen,selected_pairs=selected_rows,
            pair_diagnostics=[dict(a=k[0],b=k[1],**v) for k,v in pair_cache.items()],
            curves_sha256=sha(OUT/'curves.npz'),continuous_movement='NOT_TESTED',
            remaining_bridge_back_and_bench='NOT_TESTED',hands_and_fixture='NOT_TESTED',
            actual_wire_and_terminal='NOT_TESTED',main_applied=False,
            whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_LIFT_LOWERING_DONE',report['status'],[c['candidate_id'] for c in chosen] if chosen else None,
      round(time.time()-started,2),flush=True)
