"""Screen temporary four-wire staging in the original bridge's left opening.

Only the four free wires are rerouted. Original M1.47 solids and all fourteen
body wires remain. Passing this screen does not release a harness drawing.
"""
from pathlib import Path
import copy

LEFT_SCRIPT=Path(__file__).resolve()
LEFT_HELPER=LEFT_SCRIPT.parent/'screen_bridge_then_shell_over_wires.py'
__file__=str(LEFT_HELPER)
exec(compile(LEFT_HELPER.read_text().split('\nstarted=time.time();',1)[0],str(LEFT_HELPER),'exec'),globals())
__file__=str(LEFT_SCRIPT)
OUT=STOCK_OUT/'bridge_left_tail_staging';OUT.mkdir(exist_ok=True)
base_specs=copy.deepcopy(specifications)
base_original_errors=original_errors.copy()
baseline_parts={**core_solids,**bridge_solids}
baseline_wire_parts={n:m for n,m in baseline_parts.items() if n!='Plug_motion_J5'}
set_wire_targets(baseline_wire_parts)


def quarter_tail(pin,endpoint_xy):
    angle=math.radians(base_specs[pin]['selected']['azimuth_deg'])
    radial=np.array([math.cos(angle),math.sin(angle),0.])
    start=np.r_[endpoint_xy,147.]+8*radial-[0.,0.,8.]
    theta=np.linspace(0.,math.pi/2,253)
    return np.array([start-8*math.sin(a)*radial+[0.,0.,8*(1-math.cos(a))] for a in theta])


def candidate_curve(pin,endpoint_xy,parameters):
    specification=copy.deepcopy(base_specs[pin])
    specification['tail']=quarter_tail(pin,endpoint_xy)
    specification['tail_analytic_length_mm']=8*math.pi/2
    entry_azimuth,planar_radius,family=parameters
    specification['selected']['entry_azimuth_deg']=entry_azimuth
    specification['selected']['planar_path']['radius_mm']=planar_radius
    specification['selected']['planar_path']['family']=family
    specifications[pin]=specification
    return make_curve(pin,I)


def curve_failure(pin,curve):
    lengths[pin-1]['curve_chord_error_mm']=curve['curve_chord_error_mm']
    return (wire_check(pin,curve['points'],identity_matrices) or self_check(curve)
            or rigid_check(make_terminal(curve,I),identity_matrices))


started=time.time();trials=[];selected=None;selected_curves=None;saved={}
for outer,inner,y in [(-7.,-4.,4.8),(-7.,-4.,4.2),(-6.5,-3.5,4.8),(-7.,-4.5,5.2)]:
    endpoints={1:[outer,-y],2:[outer,y],3:[inner,-y],4:[inner,y]}
    options={};local=[]
    for pin in range(1,5):
        orig=base_specs[pin]['selected'];plane=orig['planar_path']
        parameters=[(orig['entry_azimuth_deg'],plane['radius_mm'],plane['family'])]
        parameters += [(orig['entry_azimuth_deg']+offset,radius,family)
            for offset in [0.,-15.,15.] for radius in [7.,9.,12.]
            for family in [plane['family'],'LSL','LSR','RSL','RSR','LRL-1','LRL-2','RLR-1','RLR-2']]
        unique=list(dict.fromkeys(parameters));choices=[];failures=[]
        for p in unique:
            curve,failure=candidate_curve(pin,endpoints[pin],p)
            if not failure:failure=curve_failure(pin,curve)
            failures.append(dict(parameters=p,failure=failure))
            if not failure:choices.append((p,curve))
            if len(choices)>=6:break
        options[pin]=choices
        local.append(dict(pin=pin,candidates_checked=len(failures),valid_candidates=len(choices),failures=failures))
        print('LEFT_TAIL_PIN',outer,inner,y,pin,len(choices),len(failures),round(time.time()-started,1),flush=True)
        if not choices:break
    combinations_checked=0;pair_failure=None
    if len(options)==4 and all(options.values()):
        for combo in itertools.product(*(options[p] for p in range(1,5))):
            combinations_checked+=1
            curves={p:combo[p-1][1] for p in range(1,5)}
            pairs,pair_failure=mutual_check(curves)
            if not pair_failure:
                pair_failure=terminal_checks(curves,I)
            if not pair_failure:
                selected=dict(endpoints=endpoints,parameters={p:combo[p-1][0] for p in range(1,5)},
                    pairs=pairs,outer_x_mm=outer,inner_x_mm=inner,y_mm=y)
                selected_curves=curves;break
    trials.append(dict(endpoints=endpoints,individual=local,combinations_checked=combinations_checked,
        last_pair_failure=pair_failure,status='PASS' if selected else 'BLOCKED'))
    if selected:break

bridge_rows=[];relaxation=[]
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
        if len(bridge_rows)%40==0 or failure:print('LEFT_BRIDGE',len(bridge_rows),float(lift),failure,flush=True)
        if failure:break
    # Restore the four original diagonal upper positions after the bridge is
    # seated. Same free material length; no head/yaw unit or upper shell yet.
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
            pairs=pairs,curves=[{k:v for k,v in c.items() if k!='points'} for c in curves.values()]))
        if index%20==0 or failure:print('LEFT_RELAX',index,failure,flush=True)
        if failure:break

bridge_pass=bool(bridge_rows and not bridge_rows[-1]['failure'] and bridge_rows[-1]['lift_mm']==0.)
relax_pass=bool(len(relaxation)==81 and not relaxation[-1]['failure'])
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS' if bridge_pass and relax_pass else 'BLOCKED',
    scope='Finite original bridge installation and subsequent free-tail redistribution only',
    script_sha256=sha(LEFT_SCRIPT),helper_sha256=sha(LEFT_HELPER),protected_sources=protected,
    source_main_sha256=source_hash,trials=trials,selected=selected,bridge_rows=bridge_rows,
    bridge_status='PASS' if bridge_pass else 'BLOCKED',relaxation=relaxation,
    redistribution_status='PASS' if relax_pass else 'BLOCKED',wire_sha256=sha(OUT/'curves.npz'),
    wire_OD_mm=OD,wire_clearance_mm=MARGIN,terminal_space_mm=[1,1.8,4.1],terminal_allowance_mm=.31,
    terminal_evidence='ASSUMED',fixed_body_wire_count=14,substituted_prints=[],
    original_body_plugs=len(native_body_plugs),upper_shell='Absent',
    full_nominal_allocations_mm=[r['full_nominal_allocation_mm'] for r in lengths],
    temporary_wire_forming='NOT_TESTED',continuous_motion='NOT_TESTED',
    upper_shell_installation='NOT_TESTED',head_installation='NOT_TESTED',
    hands_and_tools='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('LEFT_TAIL_DONE',report['status'],bridge_pass,relax_pass,round(time.time()-started,2),flush=True)
