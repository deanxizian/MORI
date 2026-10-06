"""Merge saved individual back20 motions and check all four wires together."""
from pathlib import Path
MERGE16_SCRIPT=Path(__file__).resolve();MERGE16_HELPER=MERGE16_SCRIPT.parent/'screen_shell16_back20_wire_families.py'
__file__=str(MERGE16_HELPER)
exec(compile(MERGE16_HELPER.read_text().split('\npools={};results=',1)[0],str(MERGE16_HELPER),'exec'),globals())
__file__=str(MERGE16_SCRIPT)
OUT=ORDER_OUT/'shell16_back20_merged';OUT.mkdir(exist_ok=True)
graph_path=ORDER_OUT/'shell16_back20_piecewise/screen.json'
graph=json.loads(graph_path.read_text())
assert graph['status']=='PASS' and graph['script_sha256']==sha(MERGE16_SCRIPT.parent/'search_shell16_back20_piecewise.py')
for p,h in graph['source_files'].items():assert sha(PROJECT/p)==h,p
rigid_all_path=ORDER_OUT/'shell16_full_rigid_path/screen.json'
rigid_all=json.loads(rigid_all_path.read_text());assert rigid_all['status']=='PASS'
assert rigid_all['script_sha256']==sha(MERGE16_SCRIPT.parent/'verify_shell16_rigid_path.py')
current={pin:dict(p) for pin,p in starts.items()};radii=[7.,8.,10.,12.,14.,18.]
holds={k:{pin:[] for pin in range(1,5)} for k in range(21)}
for result in graph['results']:
    pin=result['pin']
    for a,b in zip(result['selected_nodes'],result['selected_nodes'][1:]):
        if a[0]==b[0]:
            p=dict(entry_azimuth_deg=starts[pin]['entry_azimuth_deg']+7.5*b[1],
                   planar_radius_mm=radii[b[2]],family=starts[pin]['family'],elevation_fraction=b[3]/4.)
            holds[a[0]][pin].append(p)

def evaluate(back,parameters):
    set_pose(-float(back));curves={};failure=None;pairs=[]
    for pin in range(1,5):
        c,failure=one(pin,parameters[pin])
        if failure:break
        curves[pin]=c
    if not failure:pairs,failure=mutual_check(curves)
    if not failure:failure=terminal_checks(curves,bt)
    return failure,curves,pairs

def blend_parameters(a,b,t):
    out={k:(1-t)*a[k]+t*b[k] for k in ['entry_azimuth_deg','planar_radius_mm','elevation_fraction']}
    assert a['family']==b['family'];out['family']=a['family'];return out

def snapshots_at_hold(k,ordering):
    work={pin:dict(p) for pin,p in current.items()};snapshots=[]
    if ordering=='simultaneous':
        chains={pin:[work[pin]]+holds[k][pin] for pin in range(1,5)}
        cycles=max(len(seq)-1 for seq in chains.values())
        for step in range(cycles):
            for t in [.25,.5,.75,1.]:
                parameters={pin:blend_parameters(seq[min(step,len(seq)-1)],seq[min(step+1,len(seq)-1)],t)
                            for pin,seq in chains.items()}
                snapshots.append(parameters)
    else:
        for pin in ordering:
            for destination in holds[k][pin]:
                previous=work[pin]
                for t in [.25,.5,.75,1.]:
                    parameters={p:dict(q) for p,q in work.items()}
                    parameters[pin]=blend_parameters(previous,destination,t);snapshots.append(parameters)
                work[pin]=destination
    return snapshots

records=[];diagnostics=[];saved={};failure=None

def store_record(k,phase,parameters,curves,pairs):
    i=len(records)
    for pin,c in curves.items():saved[f'pin{pin}_pose{i}']=c['points']
    records.append(dict(index=i,stage=phase,bridge_y_mm=-float(k),bridge_z_mm=18.,
                        parameters=parameters,pairs=pairs,
                        analytic_lengths_mm={str(p):c['analytic_total_mm'] for p,c in curves.items()}))

f,curves,pairs=evaluate(0.,current);assert f is None
for pin,c in curves.items():assert np.array_equal(c['points'],start_curves[f'pin{pin}_pose36'])
store_record(0.,'initial',current,curves,pairs)
for k in range(21):
    active=[p for p in range(1,5) if holds[k][p]]
    if active:
        options=['simultaneous']+list(itertools.permutations(active));selected=None
        for order in options:
            trial=[];f=None
            for parameters in snapshots_at_hold(k,order):
                f,curves,pairs=evaluate(k,parameters)
                if f:break
                trial.append((parameters,curves,pairs))
            diagnostics.append(dict(back_mm=k,order=order,status='BLOCKED' if f else 'PASS',passing_positions=len(trial),failure=f))
            if not f:selected=trial;break
        if selected is None:failure=f;break
        for parameters,curves,pairs in selected:store_record(k,'hold_and_reshape',parameters,curves,pairs)
        current={p:dict(q) for p,q in selected[-1][0].items()}
    if k<20:
        for t in [.25,.5,.75,1.]:
            back=k+t;failure,curves,pairs=evaluate(back,current)
            if failure:break
            store_record(back,'shared_back',current,curves,pairs)
        if failure:break
    print('SHELL16_MERGED_BACK',k,'saved',len(records),round(time.time()-started,2),flush=True)
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='BLOCKED' if failure else 'PASS',scope='Four CAM wires together at finite shared back20 and hold/reshape samples',
    script_sha256=sha(MERGE16_SCRIPT),helper_sha256=sha(MERGE16_HELPER),
    source_files={**graph['source_files'],str(graph_path.relative_to(PROJECT)):sha(graph_path),str(rigid_all_path.relative_to(PROJECT)):sha(rigid_all_path)},
    protected_sources=protected,records=records,diagnostics=diagnostics,failure=failure,
    complete_back20=not bool(failure),final_parameters=current,checked_positions=len(records),
    curves_sha256=sha(OUT/'curves.npz'),body_wire_count=14,full_nominal_lengths_preserved=True,
    exact_initial_boundary_match=True,continuous_motion='NOT_TESTED',vertical_continuation='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_MERGED_BACK_DONE',report['status'],len(records),failure,flush=True)
