"""Find nominal bare-plug access after CAM-first assembly, without changing CAD.

All other connector allocations are retained at their final poses. Only the
named H01/H02/H04 conductors are deferred. A successful bare-plug approach is
not an attached-cable, hand/tool or actual connector mating qualification.
"""
from pathlib import Path
GRID_SCRIPT=Path(__file__).resolve()
GRID_HELPER=GRID_SCRIPT.parent/'screen_CAM_later_body_connections.py'
prefix=GRID_HELPER.read_text().split('\nstarted=time.time();rows=',1)[0]
__file__=str(GRID_HELPER)
exec(compile(prefix,str(GRID_HELPER),'exec'),globals())
__file__=str(GRID_SCRIPT)
import heapq
from collections import Counter

GRID_OUT=LATER_OUT/'grid_approach'
GRID_OUT.mkdir(exist_ok=True)
base=physical_targets(shellpose(15,0,14))
other_ports={p for h in deferred for p in pairings[h]}
for port in other_ports:
    base['Plug_'+port]=object_data(plug[port].m)
top=max(float(d[2][2]) for d in base.values())+6.

def collision_sweep(port,shape,targets,native_domain=None):
    """Boolean physical overlap and bounded CAM curve clearance, incl. containment."""
    bb=np.asarray(shape.bounding_box())
    for name,(solid,lo,hi,_) in targets.items():
        if np.any(bb[:3]>hi) or np.any(bb[3:]<lo):
            continue
        hit=shape^solid
        if native_domain is not None and name==native_names[port.split('_')[0]]:
            hit-=native_domain
        volume=max(0.,float(hit.volume()))
        if volume>1e-5:
            return dict(obstacle=name,kind='solid_overlap',volume_mm3=volume)
    raw=shape.to_mesh64()
    vertices=np.asarray(raw.vert_properties[:,:3]);faces=np.asarray(raw.tri_verts)
    triangles=vertices[faces]
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    norms=np.linalg.norm(normals,axis=1);valid=norms>1e-12
    normals=normals[valid]/norms[valid,None]
    offsets=np.sum(normals*triangles[valid,0],axis=1)
    assert np.max(vertices@normals.T-offsets)<=2e-5, 'Swept bound must be convex'
    tree=BVHTree.FromPolygons(vertices,faces.tolist(),all_triangles=True)
    for pin,data in cam_data.items():
        margin=OD/2+.3+data['max_step']/2+data['chord']+1e-4
        points=data['points']
        ids=np.where(np.all(points>=bb[:3]-margin,axis=1)&np.all(points<=bb[3:]+margin,axis=1))[0]
        if not len(ids):
            continue
        inside=np.all(points[ids]@normals.T<=offsets+1e-7,axis=1)
        if np.any(inside):
            return dict(obstacle='CAM_wire_'+str(pin),kind='wire_center_inside_swept_bound',point_mm=points[ids[np.flatnonzero(inside)[0]]].tolist())
        for i in ids:
            distance=float(tree.find_nearest(Vector(points[i]))[3])
            if distance<margin:
                return dict(obstacle='CAM_wire_'+str(pin),kind='clearance_bound',distance_mm=distance,required_mm=margin,point_mm=points[i].tolist())
    return None

rows=[]
overall_started=time.time()
for group in sorted(deferred):
    for port in pairings[group]:
        targets={n:d for n,d in base.items() if n!='Plug_'+port}
        m=plug[port].m
        axis=np.asarray(port_pins[port]['axis'])
        origin=axis*8
        domain=m^phys[native_names[port.split('_')[0]]]
        hull=manifold.Manifold.batch_hull([m,m.translate(origin.tolist())])
        initial=collision_sweep(port,hull,targets,domain)
        center=(np.asarray(m.bounding_box())[:3]+np.asarray(m.bounding_box())[3:])/2
        halfz=(np.asarray(m.bounding_box())[5]-np.asarray(m.bounding_box())[2])/2
        goal_z=top+halfz-center[2]
        # For the downward-facing IMU connector prefer the independently clear
        # right-side exterior, with all other mating allocations now retained.
        goal_x=max(d[2][0] for d in targets.values())+10-center[0]
        side_goal=axis[2]<0
        started=time.time();cache={};blocked=Counter();path=None
        start=(0,0,0);parents={start:None};cost={start:0.};closed=set()
        def shift(n):
            return origin+np.array(n,dtype=float)*2.
        def heuristic(n):
            q=shift(n)
            return max(0.,goal_x-q[0]) if side_goal else max(0.,goal_z-q[2])
        def edge(a,b):
            key=tuple(sorted((a,b)))
            if key not in cache:
                swept=manifold.Manifold.batch_hull([m.translate(shift(a).tolist()),m.translate(shift(b).tolist())])
                cache[key]=collision_sweep(port,swept,targets)
            return cache[key]
        frontier=[(1.4*heuristic(start),0.,start)];expanded=0
        if not initial:
            while frontier and expanded<10000 and time.time()-started<45:
                _,g,n=heapq.heappop(frontier)
                if n in closed:
                    continue
                closed.add(n);expanded+=1
                if heuristic(n)<1e-7:
                    path=[];q=n
                    while q is not None:
                        path.append(q);q=parents[q]
                    path.reverse();break
                directions=[(2,1),(0,1),(0,-1),(1,-1),(1,1),(2,-1)]
                if side_goal:
                    directions=[(0,1),(2,-1),(1,-1),(1,1),(2,1),(0,-1)]
                for dim,sign in directions:
                    q=list(n);q[dim]+=sign;q=tuple(q);s=shift(q)
                    if abs(s[0])>130 or abs(s[1])>100 or s[2]<-35 or s[2]>130:
                        continue
                    if q in closed or g+2>=cost.get(q,math.inf):
                        continue
                    hit=edge(n,q)
                    if hit:
                        blocked[hit['obstacle']]+=1;continue
                    cost[q]=g+2;parents[q]=n
                    heapq.heappush(frontier,(g+2+1.4*heuristic(q),g+2,q))
                if expanded%1000==0:
                    print('LATER_GRID_PROGRESS',port,expanded,len(frontier),round(time.time()-started,1),flush=True)
        # Greedy shortcut segments are checked over their entire convex sweep.
        short=[];certificates=[]
        if path:
            i=0;short=[path[0]]
            while i<len(path)-1:
                for j in range(len(path)-1,i,-1):
                    if edge(path[i],path[j]) is None:
                        certificates.append(dict(from_mm=shift(path[i]).tolist(),to_mm=shift(path[j]).tolist(),status='PASS'))
                        short.append(path[j]);i=j;break
                else:
                    raise RuntimeError('Original certified grid edge disappeared')
        row=dict(harness=group,port=port,status='PASS' if path else 'BLOCKED',initial_axial_failure=initial,
            initial_axial_mm=8.,initial_axis=axis.tolist(),expanded_nodes=expanded,frontier_nodes=len(frontier),
            grid_step_mm=2.,path_translations_mm=[np.zeros(3).tolist()]+[shift(n).tolist() for n in short] if path else None,
            continuous_segment_certificates=certificates,goal='right of body bounds' if side_goal else 'above all rigid stage components',
            top_rigid_exterior_plane_mm=top,blocked_edges_by_object=dict(blocked),
            stop='exterior_reached' if path else ('initial_withdrawal_blocked' if initial else ('bounded_search_stopped' if frontier else 'bounded_grid_exhausted')),
            elapsed_s=time.time()-started,node_budget=10000,time_budget_s=45)
        rows.append(row)
        print('LATER_GRID_RESULT',port,row['status'],expanded,len(short),round(row['elapsed_s'],2),flush=True)
        (GRID_OUT/'partial.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')

report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Bare connector approach with all other final mating allocations present and H01/H02/H04 conductors deferred',
    script_sha256=sha(GRID_SCRIPT),helper_sha256=sha(GRID_HELPER),protected_sources=protected,
    source_split_report_sha256=sha(membership_path),full_CAM_arrays_sha256=sha(STOCK_OUT/'full_wires.npz'),
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],source_objects=209,present_source_objects=122,
    deferred_harness_conductors=sorted(deferred),H03_conductors_retained=True,
    other_plugs_in_final_pose=True,rows=rows,physical_solids_check='Nominal closed-solid overlap threshold 1e-5 cubic mm; no physical-solid clearance guarantee',
    CAM_curve_check='Convex containment plus surface distance, including sample-halfstep/chord/0.3 mm allowances',
    initial_native_exception='Only original own-board final mating volume in the first axial segment',
    attached_deferred_wires='NOT_TESTED',tools_and_hands='NOT_TESTED',actual_plug_geometry='ASSUMED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,no_universal_impossibility_claim=True,
    elapsed_s=time.time()-overall_started)
(GRID_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/n)==h for n,h in protected.items())
print('LATER_GRID_DONE',report['status'],round(report['elapsed_s'],2),flush=True)
