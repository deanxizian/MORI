"""Change the timing of pin 4's bend adjustment, not parts or wire length.

Reuse the prior per-wire checked lifts; evaluate nonlinear bend timing for the
remaining wire and all six simultaneous pairs at the same 37 explicit poses.
"""
from pathlib import Path
SCHEDULE_SCRIPT=Path(__file__).resolve()
SCHEDULE_HELPER=SCHEDULE_SCRIPT.parent/'screen_CAM_feed_lift_transition.py'
__file__=str(SCHEDULE_HELPER)
exec(compile(SCHEDULE_HELPER.read_text().split('\nfor pin in range(1,5):',1)[0],str(SCHEDULE_HELPER),'exec'),globals())
__file__=str(SCHEDULE_SCRIPT)
prior_path=OUT/'screen.json'
prior=json.loads(prior_path.read_text())
assert prior['script_sha256']==sha(SCHEDULE_HELPER)
assert prior['status']=='BLOCKED'
for p,digest in prior['source_files'].items():assert sha(PROJECT/p)==digest
OUT=ORDER_OUT/'feed_lift_schedule'
OUT.mkdir(exist_ok=True)
base_variant=variant_curve
schedule_exponent=1.
active_endpoint=None


def variant_curve(pin,azimuth,bend_radius,family,elevation_fraction):
    if pin==4 and active_endpoint:
        source=specifications[pin]['selected']
        endpoint=active_endpoint['parameters']
        u=float(bt[2,3]/18.)
        progress=u**schedule_exponent
        azimuth=(1-progress)*source['entry_azimuth_deg']+progress*endpoint['entry_azimuth_deg']
        bend_radius=(1-progress)*source['planar_path']['radius_mm']+progress*endpoint['planar_radius_mm']
    return base_variant(pin,float(azimuth),float(bend_radius),family,elevation_fraction)


for pin in range(1,4):
    passed=[r for r in prior['results'] if r['pin']==pin and r['status']=='PASS']
    assert passed
    pools[pin]=passed
    for row in passed:
        p=row['endpoint_parameters'];source=specifications[pin]['selected']
        poses=[]
        for index,u in enumerate(u_values):
            bt=trans(z=18.*float(u))
            az=(1-u)*source['entry_azimuth_deg']+u*p['entry_azimuth_deg']
            radius=(1-u)*source['planar_path']['radius_mm']+u*p['planar_radius_mm']
            c,failure=base_variant(pin,float(az),float(radius),p['family'],p['elevation_fraction'])
            assert failure is None
            c['candidate_id']=f"{row['candidate_id']}_pose{index}"
            poses.append(c)
        curve_cache[row['candidate_id']]=poses
    candidate_results.extend(passed)

# The original pin-4 LSL family is retained. Start with the endpoint closest
# to the source shape and six explicit timing schedules; no blind family jump.
endpoint=next(c for c in screen['pools']['4'] if c['candidate_id']=='pin4_3')
assert endpoint['parameters']==dict(entry_azimuth_deg=0.,planar_radius_mm=10.,family='LSL',elevation_fraction=0.)
pools[4]=[]
for exponent in [2.,3.,4.,.5,.25,1.]:
    schedule_exponent=exponent
    active_endpoint=dict(endpoint,candidate_id='pin4_schedule_'+str(exponent).replace('.','p'))
    r=check_candidate(4,active_endpoint)
    r['schedule_exponent']=exponent
    candidate_results.append(r)
    if r['status']=='PASS':pools[4].append(r)
    print('CAM_LIFT_SCHEDULE',exponent,r['status'],r['passing_positions'],r['failure'],
          round(time.time()-started,2),flush=True)
active_endpoint=None

# Reuse the same pair/terminal checks and finite-stage packing implementation.
packing=SCHEDULE_HELPER.read_text().split('\npair_cache = {}',1)[1].split('\nreport=dict(',1)[0]
exec(compile('pair_cache = {}'+packing,str(SCHEDULE_HELPER),'exec'),globals())
report=dict(status='PASS' if chosen else 'BLOCKED',
            scope='Finite bridge-lift bend-timing candidate; no continuous or complete assembly proof',
            script_sha256=sha(SCHEDULE_SCRIPT),helper_sha256=sha(SCHEDULE_HELPER),
            source_files={**prior['source_files'],str(prior_path.relative_to(PROJECT)):sha(prior_path)},
            protected_sources=protected,source_main_sha256=source_hash,
            source_prints=membership['substituted_unadopted_prints'],
            planned_positions=STEPS,sample_spacing_mm=.5,bridge_lift_mm=18.,
            shell_transform=fixed_shell.tolist(),fixed_body_wires=14,CAM_wires=4,
            body_connection_preserved=True,wire_OD_mm=OD,clearance_mm=MARGIN,
            minimum_nominal_radius_mm=7.,minimum_upright_stock_mm=5.,
            analytic_length_conserved=True,terminal_dimensions_ASSUMED_mm=[1.,1.8,4.1],
            results=candidate_results,search_nodes=search_nodes,selected=chosen,selected_pairs=selected_rows,
            pair_diagnostics=[dict(a=k[0],b=k[1],**v) for k,v in pair_cache.items()],
            curves_sha256=sha(OUT/'curves.npz'),continuous_movement='NOT_TESTED',
            remaining_bridge_back_and_bench='NOT_TESTED',hands_and_fixture='NOT_TESTED',
            actual_wire_and_terminal='NOT_TESTED',main_applied=False,
            whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_LIFT_SCHEDULE_DONE',report['status'],[c['candidate_id'] for c in chosen] if chosen else None,
      round(time.time()-started,2),flush=True)
