"""Bounded translation-and-rotation search for the common PH allocation.

The old search allowed translations only. This diagnostic adds 24 proper
box orientations, without altering parts or omitting the fourteen body wires.
It does not include the four attached CAM leads or real connector metrology.
"""
from pathlib import Path
ROT_SCRIPT=Path(__file__).resolve();ROT_HELPER=ROT_SCRIPT.parent/'screen_CAM_bridge_wire_stock.py'
text=ROT_HELPER.read_text().split('\nstages=',1)[0]
writer="np.savez_compressed(STOCK_OUT/'full_wires.npz',**{'pin'+str(k):v for k,v in wire.items()})"
assert text.count(writer)==1;text=text.replace(writer,'# Read-only geometry initialization.')
__file__=str(ROT_HELPER);exec(compile(text,str(ROT_HELPER),'exec'),globals());__file__=str(ROT_SCRIPT)
import heapq
from itertools import permutations,product
ROT_OUT=STOCK_OUT/'PH_rotated_entry';ROT_OUT.mkdir(exist_ok=True)
bounds=np.asarray(housing.bounding_box());center=(bounds[:3]+bounds[3:])/2;size=bounds[3:]-bounds[:3]
pad=.3;box=manifold.Manifold.cube((size+2*pad).tolist(),center=True)
radius=float(np.linalg.norm((size+2*pad)/2));queries=0
rotations=[np.eye(3,dtype=int)]
for perm in permutations(range(3)):
    for signs in product([-1,1],repeat=3):
        r=np.eye(3,dtype=int)[:,perm]@np.diag(signs)
        if round(np.linalg.det(r))==1 and not any(np.array_equal(r,q) for q in rotations):rotations.append(r)
assert len(rotations)==24
shapes=[box.transform(np.column_stack([r,center])) for r in rotations]
rotlinks={}
for i,r in enumerate(rotations):
    rotlinks[i]=[]
    for ax in range(3):
        for sign in [-1,1]:
            axis='XYZ'[ax];dq=np.asarray(Matrix.Rotation(sign*math.pi/2,3,axis))
            wanted=np.rint(dq@r).astype(int)
            k=next(j for j,t in enumerate(rotations) if np.array_equal(t,wanted))
            rotlinks[i].append((k,axis,sign))
def near(m):
    b=np.asarray(m.bounding_box())
    return [(n,s) for n,(s,lo,hi,_) in target_data.items() if not(np.any(b[:3]>hi) or np.any(b[3:]<lo))]
def collision(m,allow_native=False):
    global queries
    queries+=1
    for n,s in near(m):
        overlap=m^s
        if allow_native and n=='MCU_Carrier':overlap-=native
        v=max(0.,float(overlap.volume()))
        if v>1e-5:return dict(obstacle=n,padded_intersection_mm3=v)
    return None
native=manifold.Manifold.batch_hull([shapes[0],shapes[0].translate([0,0,8])])^phys['MCU_Carrier']
initial=collision(manifold.Manifold.batch_hull([shapes[0],shapes[0].translate([0,0,8])]),True)
cache={};rotation_certificates={}
def edge(a,b,rotation_info=None):
    key=tuple(sorted((a,b)))
    if key in cache:return cache[key]
    if rotation_info is None:
        out=collision(manifold.Manifold.batch_hull([shapes[a[3]].translate(list(a[:3])),shapes[b[3]].translate(list(b[:3]))]))
    else:
        axis,sign=rotation_info;R=rotations[a[3]];offset=np.asarray(a[:3])+center
        # For every subinterval, a midpoint cuboid enlarged isotropically by
        # the maximum corner travel covers the entire rotated cuboid.
        # Replacing isotropic enlargement by extra local half-extents is a
        # conservative Minkowski-box superset, avoiding faceted sphere gaps.
        pending=[(0.,math.pi/2)];out=None;covered=0
        while pending:
            lo,hi=pending.pop();mid=(lo+hi)/2;err=radius*(hi-lo)/2
            r=np.asarray(Matrix.Rotation(sign*mid,3,axis))@R
            shape=manifold.Manifold.cube((size+2*pad+2*err).tolist(),center=True).transform(np.column_stack([r,offset]))
            hit=collision(shape)
            if not hit:covered+=1;continue
            # A midpoint nominal intersection is a real padded-box failure;
            # otherwise subdivide the conservative angular covering bound.
            actual=box.transform(np.column_stack([r,offset]));hit2=collision(actual)
            if hit2:out=hit2;break
            if hi-lo<math.radians(.5):out=dict(obstacle='angular_bound_unresolved',interval_degrees=[math.degrees(lo),math.degrees(hi)]);break
            pending.extend([(lo,mid),(mid,hi)])
        if out is None:rotation_certificates[str(key)]=covered
    cache[key]=out;return out
started=time.time();expanded=0;path=None;blocked={};stop='initial_withdrawal_blocked'
start=(0,0,8,0);goal=np.array([-18,44,60]);parents={start:None};edge_types={};cost={start:0.}
def heuristic(n):return float(np.linalg.norm(np.asarray(n[:3])-goal))
heap=[(1.6*heuristic(start),0.,start)];closed=set()
if not initial:
    while heap and expanded<12000 and time.time()-started<150:
        _,g,n=heapq.heappop(heap)
        if n in closed:continue
        closed.add(n);expanded+=1
        if tuple(n[:3])==tuple(goal):
            path=[];q=n
            while q is not None:path.append(list(q));q=parents[q]
            path.reverse();stop='goal_reached';break
        neighbors=[]
        for axis in range(3):
            for sign in [-1,1]:
                q=list(n);q[axis]+=2
                if sign<0:q[axis]-=4
                if -48<=q[0]<=48 and -24<=q[1]<=64 and 8<=q[2]<=80:neighbors.append((tuple(q),2.,None))
        neighbors += [(tuple(n[:3])+(j,),radius*math.pi/2,(axis,sign)) for j,axis,sign in rotlinks[n[3]]]
        for q,delta,info in neighbors:
            if q in closed or g+delta>=cost.get(q,math.inf):continue
            hit=edge(n,q,info)
            if hit:blocked[hit['obstacle']]=blocked.get(hit['obstacle'],0)+1;continue
            cost[q]=g+delta;parents[q]=n;edge_types[q]=info;heapq.heappush(heap,(g+delta+1.6*heuristic(q),g+delta,q))
        if expanded%250==0:print('PH_ROTATED_SEARCH',expanded,len(heap),round(time.time()-started,1),flush=True)
    if not path:stop='bounded_search_stopped' if heap else 'bounded_grid_exhausted'
report=dict(status='PASS' if path else 'BLOCKED',scope='Rigid PH housing allocation only; 24 proper rotations and translation, before yaw/pitch installation',
    script_sha256=sha(ROT_SCRIPT),helper_sha256=sha(ROT_HELPER),source_main_sha256=source_hash,protected_sources=protected,
    source_split_report_sha256=sha(membership_path),substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_objects=209,present_source_objects=len(core|upper|bridge),mating_allocations=len(plug),fixed_wire_solids=len(fixed),
    housing_dimensions_mm=size.tolist(),housing_evidence='ASSUMED existing PH mated allocation; complete real mating geometry unconfirmed',clearance_padding_mm=pad,
    straight_withdrawal=dict(status='BLOCKED' if initial else 'PASS',failure=initial,distance_mm=8),
    native_mating_overlap_exception='Only the initial axial withdrawal; no source-volume exception during subsequent translations or rotations',
    rotation_matrices=[r.tolist() for r in rotations],path_states=path,goal_translation_mm=goal.tolist(),grid_step_mm=2.,expanded_nodes=expanded,
    frontier_nodes=len(heap),stop=stop,blocking_edges_by_object=blocked,collision_queries=queries,
    rotation_edge_bound='Midpoint box expanded by radius times half angular interval; exact Minkowski-box superset of the travel-ball bound',
    certified_rotation_edges=len(rotation_certificates),node_budget=12000,time_budget_s=150,elapsed_s=time.time()-started,
    attached_four_wire_supply='NOT_TESTED',actual_mating='NOT_TESTED',hand_access='NOT_TESTED',main_applied=False,
    whole_harness='BLOCKED',manufacturing_release=False,no_universal_impossibility_claim=True)
(ROT_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/n)==h for n,h in protected.items())
print('PH_ROTATED_DONE',report['status'],stop,expanded,round(time.time()-started,2),flush=True)
