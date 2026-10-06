"""Test a specific two-height entry around the shell roof and bridge rim.

Use the documented deferred-H01/H04 assembly stage. No part is edited.
Each segment is a complete padded convex sweep, not sampled endpoints.
"""
from pathlib import Path
STEP_PH_SCRIPT=Path(__file__).resolve()
STEP_PH_HELPER=STEP_PH_SCRIPT.parent/'screen_CAM_PH_shell16_deferred_waypoints.py'
__file__=str(STEP_PH_HELPER)
exec(compile(STEP_PH_HELPER.read_text().split('\ntrials=[];',1)[0],str(STEP_PH_HELPER),'exec'),globals())
__file__=str(STEP_PH_SCRIPT)
OUT=STOCK_OUT/'PH_shell16_stepped_entry';OUT.mkdir(exist_ok=True)
trials=[];selected=None;t0=time.time();fails=Counter()
for h0 in [36.,38.,40.,34.,32.]:
    for midx in [-18.,-14.,-10.,-6.,0.]:
        for early_y in [4.,6.,8.,10.,12.,14.,16.,18.,20.,22.,24.]:
            for h1 in [44.,46.,48.,50.,52.,42.,54.,56.,58.,60.]:
                pts=[(0.,0.,8.,0),(0.,0.,h0,0),(midx,0.,h0,0),(midx,early_y,h0,0),
                     (midx,early_y,h1,0),(midx,44.,h1,0),(-18.,44.,h1,0),(-18.,44.,72.,0)]
                pts=[p for i,p in enumerate(pts) if i==0 or p!=pts[i-1]]
                f=initial;segments=[]
                if not f:
                    for a,b in zip(pts[:-1],pts[1:]):
                        f=edge(a,b);segments.append(dict(start=list(a),end=list(b),status='BLOCKED' if f else 'PASS',failure=f))
                        if f:fails[f['obstacle']]+=1;break
                row=dict(h0_mm=h0,midx_mm=midx,early_y_mm=early_y,h1_mm=h1,status='BLOCKED' if f else 'PASS',segments=segments)
                trials.append(row)
                if not f:selected=dict(path_states=[list(p) for p in pts],trial_index=len(trials)-1);break
            if selected:break
        if selected:break
    print('PH_STEPPED_HEIGHT',h0,len(trials),bool(selected),round(time.time()-t0,2),flush=True)
    if selected:break
report=dict(status='PASS' if selected else 'BLOCKED',scope='Bare PH allocation through held upper shell before deferred H01/H04 installation',
    script_sha256=sha(STEP_PH_SCRIPT),helper_sha256=sha(STEP_PH_HELPER),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [JOINT_DATA,JOINT_REPORT,FAST_BASE,OPENPH_HELPER,WAYPH_HELPER]},
    source_main_sha256=source_hash,substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    shell_transform=shell_t.tolist(),bridge_pose='native/seated',
    target_members=sorted(targets),target_groups={n:target_group[n] for n in targets},
    present_fixed_wires=4,deferred_wire_ids=deferred_wires,deferred_plugs=deferred_plugs,
    present_other_plugs=sum(n.startswith('Plug_') for n in targets),
    housing_center_mm=center.tolist(),housing_dimensions_mm=size.tolist(),housing_evidence='ASSUMED complete mated allocation',
    clearance_padding_mm=pad,initial_straight_withdrawal=dict(status='BLOCKED' if initial else 'PASS',failure=initial),
    native_overlap_exception='Only initial 8 mm axial disengagement; no exception in later moves',
    selected=selected,trials=trials,rejection_counts=dict(fails),collision_queries=queries,exact_boolean_audits=exact_audits,
    method='Each linear segment covered by padded convex endpoint hull',elapsed_s=time.time()-t0,
    attached_CAM_wires='NOT_TESTED',later_H01_H04_installation='NOT_TESTED',hands_and_tools='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('PH_STEPPED_DONE',report['status'],selected,len(trials),flush=True)
