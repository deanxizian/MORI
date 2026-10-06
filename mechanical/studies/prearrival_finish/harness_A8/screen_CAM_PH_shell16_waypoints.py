"""Compare explicit upper-opening routes before more unconstrained searches.

All 14 fixed body conductors and other source plug allocations remain present.
The held upper shell is transformed as a group. This checks only the existing
bare PH housing envelope and conservative continuous translation sweeps.
"""
from pathlib import Path
WAYPH_SCRIPT=Path(__file__).resolve();WAYPH_HELPER=WAYPH_SCRIPT.parent/'plan_CAM_PH_shell16_entry.py'
__file__=str(WAYPH_HELPER)
exec(compile(WAYPH_HELPER.read_text().split("\nexec(compile('started=time.time();expanded=0;'+run",1)[0],str(WAYPH_HELPER),'exec'),globals())
__file__=str(WAYPH_SCRIPT)
OUT=STOCK_OUT/'PH_shell16_waypoints';OUT.mkdir(exist_ok=True)
trials=[];selected=None;t0=time.time();failures=Counter()
if not initial:
    for height in [36.,38.,40.,42.,44.,46.,48.,50.,34.,32.,30.,28.,26.,24.,22.,20.,18.,16.,52.,54.,56.,58.,60.]:
        for midx in [0.,-18.,-8.,8.]:
            for order in ['up_x_forward','x_up_forward','up_forward_x','x_up_diagonal']:
                start=np.array([0.,0.,8.]);goal=np.array([-18.,44.,72.])
                if order=='up_x_forward':pts=[start,[0.,0.,height],[midx,0.,height],[midx,44.,height],[-18.,44.,height],goal]
                elif order=='x_up_forward':pts=[start,[midx,0.,8.],[midx,0.,height],[midx,44.,height],[-18.,44.,height],goal]
                elif order=='up_forward_x':pts=[start,[0.,0.,height],[0.,44.,height],[-18.,44.,height],goal]
                else:pts=[start,[midx,0.,8.],[midx,0.,height],[-18.,44.,height],goal]
                pts=[tuple(float(x) for x in p)+(0,) for p in pts]
                pts=[p for i,p in enumerate(pts) if i==0 or p!=pts[i-1]]
                f=None;segments=[]
                for i,(a,b) in enumerate(zip(pts[:-1],pts[1:])):
                    f=edge(a,b)
                    segments.append(dict(start=list(a),end=list(b),status='BLOCKED' if f else 'PASS',failure=f))
                    if f:failures[f['obstacle']]+=1;break
                trials.append(dict(height_mm=height,midx_mm=midx,order=order,status='BLOCKED' if f else 'PASS',segments=segments))
                if not f:selected=dict(path_states=[list(p) for p in pts],trial_index=len(trials)-1);break
            if selected:break
        print('PH_EXPLICIT_HEIGHT',height,len(trials),bool(selected),round(time.time()-t0,2),flush=True)
        if selected:break
report=dict(status='PASS' if selected else 'BLOCKED',scope='Bare PH cuboid via explicit upper-opening translation segments only',
    script_sha256=sha(WAYPH_SCRIPT),helper_sha256=sha(WAYPH_HELPER),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [JOINT_DATA,JOINT_REPORT,FAST_BASE,OPENPH_HELPER]},
    shell_transform=shell_t.tolist(),bridge_pose='native/seated',source_main_sha256=source_hash,
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    all14_fixed_wires=True,other_plug_count=sum(n.startswith('Plug_') for n in targets),
    transformed_upper_members=sorted(n for n in targets if target_group[n]=='upper'),
    housing_dimensions_mm=size.tolist(),housing_evidence='ASSUMED full mated envelope; supplier outline unconfirmed',
    clearance_padding_mm=pad,initial_straight_withdrawal=dict(status='BLOCKED' if initial else 'PASS',failure=initial),
    native_overlap_exception='Initial 8 mm axial withdrawal only',trials=trials,selected=selected,
    rejection_counts=dict(failures),collision_queries=queries,exact_boolean_audits=exact_audits,
    method='Convex endpoint hull covers each complete linear translation; no rotation and no sampling-only edge acceptance',
    elapsed_s=time.time()-t0,attached_wires='NOT_TESTED',hands_and_tools='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('PH_WAYPOINTS_DONE',report['status'],len(trials),flush=True)
