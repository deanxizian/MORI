"""Diagnose the bridge sliding over stationary, full-length CAM wire stock.

The body plug and all four existing complete wire polylines remain fixed.
Only the source bridge/shell stages move. No omitted wire, changed assembly
geometry, terminal-size reduction, or mating fit claim is permitted here.
"""
from pathlib import Path
SLIDE_SCRIPT=Path(__file__).resolve();SLIDE_HELPER=SLIDE_SCRIPT.parent/'screen_CAM_bridge_wire_stock.py'
text=SLIDE_HELPER.read_text().split('\nstages=',1)[0]
writer="np.savez_compressed(STOCK_OUT/'full_wires.npz',**{'pin'+str(k):v for k,v in wire.items()})"
assert text.count(writer)==1
text=text.replace(writer,'# Preserve original full stock arrays on read-only import.')
__file__=str(SLIDE_HELPER);exec(compile(text,str(SLIDE_HELPER),'exec'),globals());__file__=str(SLIDE_SCRIPT)
SLIDE_OUT=STOCK_OUT/'bridge_over_stock';SLIDE_OUT.mkdir(exist_ok=True)
stages=[
 ('bridge_lift_shell_held',[(shellpose(15,0,14),trans(z=float(z))) for z in np.arange(0,18.01,.5)]),
 ('body_bridge_back',[(shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in np.linspace(0,-14,57)]),
 ('body_bridge_bench',[(shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in np.arange(14,140.01,.5)]),
 ('body_shell_settle',[(shellpose(15*float(u),0,14*float(u)),I) for u in np.linspace(0,1,61)]),
]
rows=[];started=time.time()
for label,poses in stages:
    failure=None;checked=0
    for index,(st,bt) in enumerate(poses):
        matrices={'core':I,'upper':np.linalg.inv(st),'bridge':np.linalg.inv(bt)}
        failure=rigid_check(housing,matrices,True)
        if not failure:
            for pin,pts in wire.items():
                failure=wire_check(pin,pts,matrices) or rigid_check(terminals[pin],matrices)
                if failure:break
        checked+=1
        if failure:
            failure.update(index=index,shell_transform=st.tolist(),bridge_transform=bt.tolist());break
    row=dict(stage=label,status='BLOCKED' if failure else 'PASS',checked_positions=checked,
             planned_positions=len(poses),failure=failure)
    rows.append(row);print('BRIDGE_OVER_STOCK',label,row['status'],checked,failure,round(time.time()-started,2),flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite bridge/shell stages over stationary full CAM wire stock and seated common PH allocation',
    script_sha256=sha(SLIDE_SCRIPT),helper_sha256=sha(SLIDE_HELPER),source_main_sha256=source_hash,
    source_split_report_sha256=sha(membership_path),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [partial_path,datum_path,body_math_path,fixed_path,STOCK_OUT/'full_wires.npz']},
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_objects=209,present_source_objects=len(core|upper|bridge),
    mating_allocations=len(plug),fixed_wire_solids=len(fixed),lengths=lengths,
    wire_OD_mm=OD,clearance_requirement_mm=MARGIN,rows=rows,
    continuous_motion='NOT_TESTED',feed_into_bridge_before_this_state='NOT_TESTED',
    later_yaw_installation_over_stock='NOT_TESTED',full_wire_physical_shape_and_support='NOT_TESTED',
    supplier_cut_lengths=False,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    no_universal_impossibility_claim=True,elapsed_s=time.time()-started)
(SLIDE_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('BRIDGE_OVER_STOCK_DONE',report['status'],round(time.time()-started,2),flush=True)
