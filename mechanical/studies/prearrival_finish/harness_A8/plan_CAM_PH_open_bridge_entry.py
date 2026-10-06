"""Check a common PH housing before installing the yaw rotor/reaction shaft.

Uses the existing unmeasured mated-housing allocation and a conservative box
margin. Any path found is a rigid connector-space candidate only. It does not
prove mating tolerances, attached-wire motion, handling or supplier assembly.
"""
from pathlib import Path
PH_SCRIPT=Path(__file__).resolve();PH_HELPER=PH_SCRIPT.parent/'screen_CAM_bridge_wire_stock.py'
text=PH_HELPER.read_text().split('\nstages=',1)[0]
writer="np.savez_compressed(STOCK_OUT/'full_wires.npz',**{'pin'+str(k):v for k,v in wire.items()})"
assert text.count(writer)==1;text=text.replace(writer,'# Read-only import of existing definitions.')
__file__=str(PH_HELPER);exec(compile(text,str(PH_HELPER),'exec'),globals());__file__=str(PH_SCRIPT)
import heapq
PH_OUT=STOCK_OUT/'PH_open_bridge';PH_OUT.mkdir(exist_ok=True)
bounds=np.asarray(housing.bounding_box());center=(bounds[:3]+bounds[3:])/2;size=bounds[3:]-bounds[:3]
pad=.3;cube=manifold.Manifold.cube((size+2*pad).tolist(),center=True).translate(center.tolist())
native_domain=manifold.Manifold.batch_hull([cube,cube.translate([0.,0.,8.])])^phys['MCU_Carrier']
checks=0
def collision(shape):
    global checks
    checks+=1;bb=np.asarray(shape.bounding_box())
    for name,(m,lo,hi,_) in target_data.items():
        if np.any(bb[:3]>hi) or np.any(bb[3:]<lo):continue
        overlap=shape^m
        if name=='MCU_Carrier':overlap-=native_domain
        volume=max(0.,float(overlap.volume()))
        if volume>1e-5:return dict(obstacle=name,padded_intersection_mm3=volume)
    return None
def swept(a,b):
    return manifold.Manifold.batch_hull([cube.translate(list(a)),cube.translate(list(b))])
initial=collision(swept((0,0,0),(0,0,8)))
rows=[];path=None;started=time.time();expanded=0;stop='initial_withdrawal_blocked'
rows.append(dict(stage='straight_disengagement',translation_mm=[0.,0.,8.],status='BLOCKED' if initial else 'PASS',failure=initial))
if not initial:
    start=(0,0,8);goal=(-18,44,60);step=2
    def heuristic(n):return float(np.linalg.norm(np.asarray(n)-goal))
    heap=[(heuristic(start),0.,start)];cost={start:0.};parent={start:None};closed=set();blocked={};edge_cache={}
    while heap and expanded<6000 and time.time()-started<100:
        _,g,n=heapq.heappop(heap)
        if n in closed:continue
        closed.add(n);expanded+=1
        if n==goal:
            path=[];node=n
            while node is not None:path.append(list(node));node=parent[node]
            path.reverse();stop='goal_reached';break
        for axis in range(3):
            for sign in (-1,1):
                q=list(n);q[axis]+=sign*step;q=tuple(q)
                if not(-48<=q[0]<=48 and -24<=q[1]<=64 and 8<=q[2]<=80) or q in closed:continue
                if g+step>=cost.get(q,math.inf):continue
                key=tuple(sorted([n,q]))
                if key not in edge_cache:edge_cache[key]=collision(swept(n,q))
                hit=edge_cache[key]
                if hit:blocked[hit['obstacle']]=blocked.get(hit['obstacle'],0)+1;continue
                cost[q]=g+step;parent[q]=n;heapq.heappush(heap,(g+step+heuristic(q),g+step,q))
        if expanded%500==0:print('PH_OPEN_BRIDGE_SEARCH',expanded,len(heap),round(time.time()-started,1),flush=True)
    if not path:stop='bounded_search_stopped' if heap else 'bounded_grid_exhausted'
    rows.append(dict(stage='rigid_housing_to_open_neck',status='PASS' if path else 'BLOCKED',
        start_translation_mm=list(start),goal_translation_mm=list(goal),expanded_nodes=expanded,
        frontier_nodes=len(heap),stop=stop,blocking_edges_by_object=blocked))
report=dict(status='PASS' if path else 'BLOCKED',scope='Rigid common-PH allocation through the pre-yaw assembly; no attached-wire or physical-mating proof',
    script_sha256=sha(PH_SCRIPT),helper_sha256=sha(PH_HELPER),source_main_sha256=source_hash,
    source_split_report_sha256=sha(membership_path),protected_sources=protected,
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_objects=209,present_source_objects=len(core|upper|bridge),mating_allocations=len(plug),fixed_wire_solids=len(fixed),
    housing_bounds_mm=bounds.tolist(),housing_evidence='ASSUMED sourced PH mated allocation, not measured housing',
    clearance_box_padding_mm=pad,own_native_mating_domain_mm3=float(native_domain.volume()),
    own_native_mating_domain_scope='Only MCU_Carrier overlap with the original axial housing pull; not a mating-fit qualification',
    grid_step_mm=2.,rigid_edge_sweeps='Convex endpoint hull for linear fixed-orientation translation',
    node_budget=6000,time_budget_s=100,rows=rows,translation_path_mm=path,collision_queries=checks,
    wire_path_and_material='NOT_TESTED',hand_access='NOT_TESTED',actual_mating='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,no_universal_impossibility_claim=True,
    elapsed_s=time.time()-started)
(PH_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('PH_OPEN_BRIDGE_DONE',report['status'],stop,expanded,checks,round(time.time()-started,2),flush=True)
