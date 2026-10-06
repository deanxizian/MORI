"""Find bounded-clearance grid corridors; do not call grid corners wire bends."""
from pathlib import Path
import sys,json,hashlib,math,time,heapq,itertools
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
space=json.loads((HERE/'head_entry_space.json').read_text())
data=np.load(HERE/'head_entry_clearance.npz');grid=data['grid_mm'];clear=data['clearance_mm'];shape=clear.shape
mesh=np.load(HERE/'head_entry_obstacle_union.npz')
tree=BVHTree.FromPolygons(mesh['vertices_mm'],mesh['triangles'],all_triangles=True)
pts=grid.reshape(-1,3);flat=clear.ravel();strides=np.array([shape[1]*shape[2],shape[2],1])
deltas=[np.array(q) for q in itertools.product([-1,0,1],repeat=3) if any(q)]
lengths=[float(np.linalg.norm(q)) for q in deltas]
started=time.time();cases=[]
seed=json.loads((HERE/'split_planar_loops_refined.json').read_text())
planning=[(g['id'],g['diameter_mm']) for g in seed['groups']]
for group,diameter in planning:
    radius=diameter/2;required=radius+.3
    valid=flat>=required
    start_mask=(pts[:,0]>=40)&(abs(pts[:,1])<=10)&(pts[:,2]<=159)&valid
    target_mask=(pts[:,0]>=16)&(pts[:,0]<=30)&(abs(pts[:,1])>=23)&(pts[:,2]>=199)&valid
    target_ids=set(np.flatnonzero(target_mask).tolist());starts=np.flatnonzero(start_mask)
    dx=np.maximum(np.maximum(16-pts[:,0],pts[:,0]-30),0)
    dy=np.maximum(23-abs(pts[:,1]),0);dz=np.maximum(199-pts[:,2],0)
    heuristic=np.sqrt(dx*dx+dy*dy+dz*dz)
    cost=np.full(len(flat),np.inf);previous=np.full(len(flat),-1,dtype=np.int32);heap=[];edge_cache={}
    for n in starts:cost[n]=0;heapq.heappush(heap,(float(heuristic[n]),0.,int(n)))
    end=None;expanded=0
    while heap:
        _,distance,n=heapq.heappop(heap)
        if distance>cost[n]+1e-8:continue
        if n in target_ids:end=n;break
        expanded+=1;index=np.array(np.unravel_index(n,shape))
        for delta,ln in zip(deltas,lengths):
            other=index+delta
            if np.any(other<0) or np.any(other>=shape):continue
            q=int(np.dot(other,strides))
            if not valid[q] or distance+ln>=cost[q]-1e-8:continue
            # Initial bound is exact for all points on this straight edge.
            bound=min(float(flat[n]),float(flat[q]))-ln/2
            if bound<required:
                key=(min(n,q),max(n,q))
                if key not in edge_cache:
                    samples=np.linspace(pts[n],pts[q],17)
                    edge_cache[key]=min(tree.find_nearest(Vector(p))[3] for p in samples)-ln/32-1e-5
                bound=edge_cache[key]
            if bound<required:continue
            cost[q]=distance+ln;previous[q]=n
            heapq.heappush(heap,(float(cost[q]+heuristic[q]),float(cost[q]),q))
    path=[];bound=None
    if end is not None:
        n=end
        while n>=0:path.append(pts[n].tolist());n=int(previous[n])
        path.reverse();bound=1e9
        for a,b in zip(np.asarray(path),np.asarray(path)[1:]):
            ln=np.linalg.norm(b-a);samples=np.linspace(a,b,33)
            bound=min(bound,min(tree.find_nearest(Vector(p))[3] for p in samples)-ln/64-1e-5)
    row=dict(id=group,planning_diameter_mm=diameter,status='PASS' if path else 'BLOCKED',path_mm=path,
             expanded_nodes=expanded,checked_near_boundary_edges=len(edge_cache),
             polyline_length_mm=float(cost[end]) if end is not None else None,
             source_surface_clearance_lower_bound_mm=bound,
             polyline_surface_gap_lower_bound_mm=bound-radius if bound is not None else None,
             minimum_bend='NOT_TESTED',mutual_group_clearance='NOT_TESTED',staging_endpoints_not_connectors=True)
    cases.append(row);print('ENTRY_SHORTEST',group,row['status'],len(path),expanded,time.time()-started,flush=True)
out=dict(status='PASS' if all(c['status']=='PASS' for c in cases) else 'BLOCKED',
         scope='Independent grid-corridor feasibility for the three planning diameters only',
         source_blend_sha256=space['source_blend_sha256'],source_space_sha256=hashlib.sha256((HERE/'head_entry_space.json').read_bytes()).hexdigest(),
         source_clearance_sha256=hashlib.sha256((HERE/'head_entry_clearance.npz').read_bytes()).hexdigest(),
         source_obstacle_mesh_sha256=hashlib.sha256((HERE/'head_entry_obstacle_union.npz').read_bytes()).hexdigest(),
         groups=cases,main_geometry_changed=False,all_three_installed_together='NOT_TESTED',
         minimum_bend='NOT_TESTED',actual_anchors='NOT_TESTED',complete_wire_paths='NOT_TESTED',elapsed_s=time.time()-started,
         limits=['Each independent path is a 1mm graph corridor with sharp corners, not a printable or installed cable route.',
                 'The paths may overlap each other and do not establish simultaneous capacity for 11 wires.',
                 'The source union is a finite 13-yaw/10-pitch sweep in yaw coordinates.',
                 'Body-loop and connector approaches, exterior concealment, support and installation remain untested.',
                 'A failed graph resolution would not prove every continuous route is impossible.'])
(HERE/'head_entry_shortest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('ENTRY_SHORTEST_COMPLETE',out['status'],time.time()-started,flush=True)
