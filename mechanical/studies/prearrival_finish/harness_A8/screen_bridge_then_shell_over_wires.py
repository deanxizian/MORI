"""Compare assembling the original bridge and shell over temporary straight leads.

The four CAM roots remain at their body connector. Only the not-yet-connected
upper tails are temporarily straightened at radius 6.8 mm. Fourteen body wires
remain present; no printed part, board, hole or wire diameter is changed.
"""
from pathlib import Path

OVER_SCRIPT=Path(__file__).resolve()
OVER_HELPER=OVER_SCRIPT.parent/'screen_CAM_PH_attached_wire_entry.py'
__file__=str(OVER_HELPER)
exec(compile(OVER_HELPER.read_text().split('\nstarted = time.time()',1)[0],str(OVER_HELPER),'exec'),globals())
__file__=str(OVER_SCRIPT)
OUT=STOCK_OUT/'bridge_then_shell_over_wires';OUT.mkdir(exist_ok=True)
original_parts={n:ss[n].m for n in core|upper|bridge}
assert all(n in ss for n in original_parts)
native_body_plugs={'Plug_'+n:s.m for n,s in plug.items() if n.startswith(('power_','motion_','imu_'))}
native_upper_plugs={'Plug_'+n:s.m for n,s in plug.items() if n.startswith('rear_')}
assert len(native_body_plugs)+len(native_upper_plugs)==len(plug)
full_body_wires={'fixed_wire_'+n:r['m'] for n,r in fixed.items()}
for n,row in joint_data.items():
    full_body_wires['fixed_wire_'+n]=manifold.Manifold(manifold.Mesh64(np.asarray(row['vertices_mm']),np.asarray(row['triangles'],dtype=np.uint64)))
assert len(full_body_wires)==14


def placed(data,t=I):
    return {n:m.transform(t[:3,:4]) for n,m in data.items()}


def pairs_hit(moving,stationary):
    boxes={n:np.asarray(m.bounding_box()) for n,m in stationary.items()}
    for name,m in moving.items():
        b=np.asarray(m.bounding_box())
        for other,obstacle in stationary.items():
            q=boxes[other]
            if np.any(b[:3]>=q[3:]) or np.any(q[:3]>=b[3:]):continue
            volume=max(0.,float((m^obstacle).volume()))
            if volume>1e-5:return dict(kind='solid_overlap',moving=name,obstacle=other,intersection_mm3=volume)
    return None


def set_wire_targets(parts):
    global target_data,target_group
    target_data={};target_group={}
    for n,m in parts.items():
        mesh=m.to_mesh64();vertices=np.asarray(mesh.vert_properties[:,:3]);faces=np.asarray(mesh.tri_verts)
        target_data[n]=(m,vertices.min(0),vertices.max(0),BVHTree.FromPolygons(vertices,faces.tolist(),all_triangles=True))
        target_group[n]='core'


temporary={};source_rows=[]
for pin in range(1,5):
    source=partial[f'pin{pin}_yaw0'];first=len(specifications[pin]['selected']['curve_mm'])-1
    index=next(i for i in range(first,len(source)) if abs(source[i,2]-147.)<1e-8)
    prefix=source[:index+1].copy()
    assert abs(np.linalg.norm(prefix[-1,:2])-6.8)<1e-8
    step_direction=prefix[-1]-prefix[-2]
    assert float(np.dot(step_direction/np.linalg.norm(step_direction),[0,0,1]))>.999
    # Analytic body prefix and the documented R8 lower quarter-circle.
    prefix_length=specifications[pin]['selected']['analytic_prefix_length_mm']+8*math.pi/2
    stock=lengths[pin-1]['full_nominal_allocation_mm']-prefix_length
    points=np.vstack([prefix,line(prefix[-1],prefix[-1]+[0,0,stock])[1:]])
    temporary[pin]=dict(points=points,pin=pin,curve_chord_error_mm=original_errors[pin-1],
        analytic_total_mm=prefix_length+stock,prefix_analytic_mm=prefix_length,stock_mm=stock,
        sampled_total_mm=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum()))
    source_rows.append(dict(pin=pin,source_prefix_points=index+1,end_of_lower_bend_mm=prefix[-1].tolist(),
        terminal_mm=points[-1].tolist(),nominal_length_mm=lengths[pin-1]['full_nominal_allocation_mm'],stock_mm=stock))
    lengths[pin-1]['curve_chord_error_mm']=original_errors[pin-1]
pair_rows,pair_failure=mutual_check(temporary)
self_failures=[self_check(c) for c in temporary.values()]
assert pair_failure is None and all(f is None for f in self_failures),(pair_failure,self_failures)
stock_terminals={pin:make_terminal(c,I) for pin,c in temporary.items()}
top=max(m.bounding_box()[5] for m in stock_terminals.values())
bridge_min=min(original_parts[n].bounding_box()[2] for n in bridge)
entry_z=math.ceil(top-bridge_min+5.)
core_solids={n:original_parts[n] for n in core}
core_solids.update(native_body_plugs)
core_solids.update(full_body_wires)
bridge_solids={n:original_parts[n] for n in bridge}
upper_solids={n:original_parts[n] for n in upper}
upper_solids.update(native_upper_plugs)


def wire_state(parts):
    set_wire_targets(parts)
    for pin,c in temporary.items():
        f=wire_check(pin,c['points'],identity_matrices)
        if not f:f=rigid_check(stock_terminals[pin],identity_matrices)
        if f:return f
    return None


started=time.time();baseline_parts={**core_solids,**bridge_solids}
# The common own PH housing deliberately excludes its four wire roots.
baseline_wire_parts={n:m for n,m in baseline_parts.items() if n!='Plug_motion_J5'}
baseline_failure=wire_state(baseline_wire_parts)
bridge_rows=[]
if not baseline_failure:
    for lift in np.linspace(entry_z,0.,math.ceil(entry_z)+1):
        moved=placed(bridge_solids,trans(z=float(lift)))
        failure=pairs_hit(moved,core_solids)
        if not failure:failure=wire_state(moved)
        bridge_rows.append(dict(lift_mm=float(lift),status='BLOCKED' if failure else 'PASS',failure=failure))
        if len(bridge_rows)%40==0 or failure:
            print('BRIDGE_OVER_WIRES',len(bridge_rows),float(lift),'BLOCKED' if failure else 'PASS',failure,flush=True)
        if failure:break
bridge_status='PASS' if bridge_rows and not bridge_rows[-1]['failure'] and bridge_rows[-1]['lift_mm']==0 else 'BLOCKED'

# First compare rigid upper-shell routes while keeping all four temporary
# CAM tails and all fourteen core wires present. Rear/speaker harnesses are
# explicitly a later obligation, not inferred from rigid connector envelopes.
shell_trials=[]
for back in [0.,-10.,-14.,-20.,-24.]:
    poses=[]
    for z in np.arange(210.,13.99,-2.):poses.append(('lower_open_shell',shellpose(16.,back,float(z))))
    if back:
        for y in np.linspace(back,0.,math.ceil(abs(back)/.5)+1)[1:]:poses.append(('bring_forward',shellpose(16.,float(y),14.)))
    for u in np.linspace(1.,0.,61)[1:]:poses.append(('settle_shell',shellpose(16.*float(u),0.,14.*float(u))))
    rows=[]
    for index,(stage,t) in enumerate(poses):
        moved=placed(upper_solids,t)
        failure=pairs_hit(moved,baseline_parts)
        if not failure:failure=wire_state(moved)
        rows.append(dict(index=index,stage=stage,transform=t.tolist(),status='BLOCKED' if failure else 'PASS',failure=failure))
        if failure:break
    status='PASS' if len(rows)==len(poses) and not rows[-1]['failure'] else 'BLOCKED'
    shell_trials.append(dict(back_mm=back,status=status,planned_positions=len(poses),checked_positions=len(rows),rows=rows))
    print('SHELL_OVER_WIRES',back,status,len(rows),rows[-1]['failure'],flush=True)
    if status=='PASS':break

np.savez_compressed(OUT/'temporary_wires.npz',**{'pin'+str(k):c['points'] for k,c in temporary.items()})
report=dict(status='PASS' if bridge_status=='PASS' and any(q['status']=='PASS' for q in shell_trials) else 'BLOCKED',
    scope='Finite original-M1.47 bridge/shell installation over temporary central wire tails; head installation incomplete',
    script_sha256=sha(OVER_SCRIPT),helper_sha256=sha(OVER_HELPER),protected_sources=protected,
    source_main_sha256=source_hash,source_files={str(p.relative_to(PROJECT)):sha(p) for p in
        [membership_path,partial_path,datum_path,body_math_path,pack_path,JOINT_DATA,JOINT_REPORT]},
    body_core_members=sorted(core_solids),bridge_members=sorted(bridge_solids),upper_members=sorted(upper_solids),
    original_M1_47_source_solids_used=True,substituted_prints=[],fourteen_core_wires_present=True,
    temporary_tail_radius_mm=6.8,source_lower_bend_radius_mm=8.,body_root_first_straight_mm=5.,
    wire_OD_mm=OD,clearance_requirement_mm=MARGIN,lengths=source_rows,mutual_pairs=pair_rows,
    baseline_wire_status='BLOCKED' if baseline_failure else 'PASS',baseline_failure=baseline_failure,
    bridge_entry_lift_mm=entry_z,bridge_status=bridge_status,bridge_rows=bridge_rows,shell_trials=shell_trials,
    wire_sha256=sha(OUT/'temporary_wires.npz'),wire_root_own_housing_exception='Only own PH removed from wire checks; body rigid checks retain it',
    continuous_motion='NOT_TESTED',native_PH_mating='NOT_TESTED',loose_terminal_envelope='ASSUMED',
    temporary_wire_forming='NOT_TESTED',yaw_unit_over_tails='NOT_TESTED',later_wire_relaxation='NOT_TESTED',
    rear_speaker_harnesses='NOT_TESTED',tools_and_hands='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('BRIDGE_SHELL_OVER_DONE',report['status'],bridge_status,round(time.time()-started,2),baseline_failure,flush=True)
