"""Install the bare bridge over wires; fit its bearing after tail redistribution.

The reaction socket floor prevents a direct pass through the assembled bearing
and bridge. This study changes their installation order, not their geometry.
"""
from pathlib import Path
BARE_SCRIPT=Path(__file__).resolve()
BARE_HELPER=BARE_SCRIPT.parent/'screen_bridge_left_tail_staging.py'
__file__=str(BARE_HELPER)
exec(compile(BARE_HELPER.read_text().split('\nstarted=time.time();trials',1)[0],str(BARE_HELPER),'exec'),globals())
__file__=str(BARE_SCRIPT)
OUT=STOCK_OUT/'bridge_before_bearing';OUT.mkdir(exist_ok=True)
bearing_solid=bridge_solids.pop('Yaw_Bearing')
baseline_parts={**core_solids,**bridge_solids}
baseline_wire_parts={n:m for n,m in baseline_parts.items() if n!='Plug_motion_J5'}
set_wire_targets(baseline_wire_parts)


def reportable(curves):
    return [{k:v for k,v in c.items() if k!='points'} for c in curves.values()]


started=time.time();trials=[];selected=None;selected_curves=None;saved={}
for staging_radius in [11.5,11.,12.,13.]:
    endpoints={}
    for pin in range(1,5):
        angle=math.radians(base_specs[pin]['selected']['azimuth_deg'])
        endpoints[pin]=[staging_radius*math.cos(angle),staging_radius*math.sin(angle)]
    options={};local=[]
    for pin in range(1,5):
        orig=base_specs[pin]['selected'];plane=orig['planar_path']
        parameters=[(orig['entry_azimuth_deg'],plane['radius_mm'],plane['family'])]
        parameters += [(orig['entry_azimuth_deg']+offset,radius,family)
            for offset in [0.,-15.,15.] for radius in [7.,9.,12.]
            for family in [plane['family'],'LSL','LSR','RSL','RSR','LRL-1','LRL-2','RLR-1','RLR-2']]
        choices=[];failures=[]
        for p in list(dict.fromkeys(parameters)):
            curve,failure=candidate_curve(pin,endpoints[pin],p)
            if not failure:failure=curve_failure(pin,curve)
            failures.append(dict(parameters=p,failure=failure))
            if not failure:choices.append((p,curve))
            if len(choices)>=6:break
        options[pin]=choices
        local.append(dict(pin=pin,candidates_checked=len(failures),valid_candidates=len(choices),failures=failures))
        print('BARE_TAIL_PIN',staging_radius,pin,len(choices),len(failures),round(time.time()-started,1),flush=True)
        if not choices:break
    combinations_checked=0;pair_failure=None
    if len(options)==4 and all(options.values()):
        for combo in itertools.product(*(options[p] for p in range(1,5))):
            combinations_checked+=1
            curves={p:combo[p-1][1] for p in range(1,5)}
            pairs,pair_failure=mutual_check(curves)
            if not pair_failure:pair_failure=terminal_checks(curves,I)
            if not pair_failure:
                selected=dict(endpoints=endpoints,parameters={p:combo[p-1][0] for p in range(1,5)},
                    pairs=pairs,staging_radius_mm=staging_radius,curves=reportable(curves))
                selected_curves=curves;break
    trials.append(dict(staging_radius_mm=staging_radius,individual=local,combinations_checked=combinations_checked,
        last_pair_failure=pair_failure,status='PASS' if selected else 'BLOCKED'))
    if selected:break

bridge_rows=[];relaxation=[];bearing_rows=[]
if selected:
    temporary=selected_curves
    stock_terminals={pin:make_terminal(c,I) for pin,c in temporary.items()}
    top=max(m.bounding_box()[5] for m in stock_terminals.values())
    entry_z=math.ceil(top-min(m.bounding_box()[2] for m in bridge_solids.values())+5.)
    for pin,c in temporary.items():saved[f'staged_pin{pin}']=c['points']
    for lift in np.linspace(entry_z,0.,math.ceil(entry_z)+1):
        moved=placed(bridge_solids,trans(z=float(lift)))
        failure=pairs_hit(moved,core_solids)
        if not failure:failure=wire_state(moved)
        bridge_rows.append(dict(lift_mm=float(lift),status='BLOCKED' if failure else 'PASS',failure=failure))
        if len(bridge_rows)%50==0 or failure:print('BARE_BRIDGE',len(bridge_rows),float(lift),failure,flush=True)
        if failure:break
    set_wire_targets(baseline_wire_parts)
    for index,u in enumerate(np.linspace(0.,1.,81)):
        curves={};failure=None
        for pin in range(1,5):
            angle=math.radians(base_specs[pin]['selected']['azimuth_deg'])
            native=np.array([6.8*math.cos(angle),6.8*math.sin(angle)])
            xy=(1-u)*np.array(selected['endpoints'][pin])+u*native
            c,failure=candidate_curve(pin,xy,selected['parameters'][pin])
            if not failure:failure=curve_failure(pin,c)
            if failure:break
            curves[pin]=c
            saved[f'relax{index}_pin{pin}']=c['points']
        pairs=[]
        if not failure:pairs,failure=mutual_check(curves)
        if not failure:failure=terminal_checks(curves,I)
        relaxation.append(dict(index=index,u=float(u),status='BLOCKED' if failure else 'PASS',failure=failure,
            pairs=pairs,curves=reportable(curves)))
        if index%20==0 or failure:print('BARE_RELAX',index,failure,flush=True)
        if failure:break
    if len(relaxation)==81 and not relaxation[-1]['failure']:
        temporary=curves
        stock_terminals={pin:make_terminal(c,I) for pin,c in temporary.items()}
        top=max(m.bounding_box()[5] for m in stock_terminals.values())
        entry_z=math.ceil(top-bearing_solid.bounding_box()[2]+5.)
        for lift in np.linspace(entry_z,0.,math.ceil(entry_z)+1):
            moved={'Yaw_Bearing':bearing_solid.translate([0,0,float(lift)])}
            failure=pairs_hit(moved,baseline_parts)
            if not failure:failure=wire_state(moved)
            bearing_rows.append(dict(lift_mm=float(lift),status='BLOCKED' if failure else 'PASS',failure=failure))
            if len(bearing_rows)%50==0 or failure:print('BARE_BEARING',len(bearing_rows),float(lift),failure,flush=True)
            if failure:break

bridge_pass=bool(bridge_rows and not bridge_rows[-1]['failure'] and bridge_rows[-1]['lift_mm']==0.)
relax_pass=bool(len(relaxation)==81 and not relaxation[-1]['failure'])
bearing_pass=bool(bearing_rows and not bearing_rows[-1]['failure'] and bearing_rows[-1]['lift_mm']==0.)
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS' if bridge_pass and relax_pass and bearing_pass else 'BLOCKED',
    scope='Finite bare bridge insertion, free wire redistribution, then bearing insertion only',
    script_sha256=sha(BARE_SCRIPT),helper_sha256=sha(BARE_HELPER),protected_sources=protected,
    source_main_sha256=source_hash,trials=trials,selected=selected,bridge_rows=bridge_rows,
    bridge_status='PASS' if bridge_pass else 'BLOCKED',relaxation=relaxation,
    redistribution_status='PASS' if relax_pass else 'BLOCKED',bearing_rows=bearing_rows,
    bearing_status='PASS' if bearing_pass else 'BLOCKED',wire_sha256=sha(OUT/'curves.npz'),
    wire_OD_mm=OD,wire_clearance_mm=MARGIN,terminal_space_mm=[1,1.8,4.1],terminal_allowance_mm=.31,
    terminal_evidence='ASSUMED',fixed_body_wire_count=14,substituted_prints=[],
    original_body_plugs=len(native_body_plugs),upper_shell='Absent',
    full_nominal_allocations_mm=[r['full_nominal_allocation_mm'] for r in lengths],
    temporary_wire_forming='NOT_TESTED',continuous_motion='NOT_TESTED',
    upper_shell_installation='NOT_TESTED',head_installation='NOT_TESTED',
    actual_bearing_fit_and_install_tool='NOT_TESTED',hands_and_tools='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('BARE_DONE',report['status'],bridge_pass,relax_pass,bearing_pass,round(time.time()-started,2),flush=True)
