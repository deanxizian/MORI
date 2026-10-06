"""Read-only clearance graph for a yaw-following route entering the head.

Use the union of actual source solids in the yaw frame over the existing finite
pose grid. No assumed wiring holes, moved hardware or nearest-normal inside
classification. Positive paths are only grid corridors, not bend-safe cables.
"""
from pathlib import Path
import sys,json,hashlib,time,heapq,collections,math
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from mathutils.bvhtree import BVHTree
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);before=hashlib.sha256(source.read_bytes()).hexdigest()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
started=time.time();lo=np.array([10.,-32.,156.]);hi=np.array([48.,32.,206.]);margin=4.
solids=[];sources=[]
for name,s in ss.items():
    if s.group=='pitch':poses=[(0,p) for p in range(-20,26,5)]
    elif s.group=='yaw':poses=[(0,0)]
    else:poses=[(y,0) for y in range(-60,61,10)]
    for y,p in poses:
        if s.group=='pitch':m=s.m.transform(np.asarray(rigidtr(0,p))[:3,:])
        elif s.group=='yaw':m=s.m
        else:m=s.m.transform(np.linalg.inv(np.asarray(rigidtr(y,0)))[:3,:])
        bb=np.asarray(m.bounding_box())
        if np.any(bb[:3]>hi+margin) or np.any(bb[3:]<lo-margin):continue
        solids.append(m);sources.append(dict(object=name,group=s.group,yaw_deg=y,pitch_deg=p))
print('ENTRY_UNION_INPUT',len(solids),'instances',len(set(s['object'] for s in sources)),'parts',flush=True)
m=manifold.Manifold.batch_boolean(solids,manifold.OpType.Add)
assert m.status()==manifold.Error.NoError
mesh=m.to_mesh64();vertices=np.asarray(mesh.vert_properties[:,:3]);triangles=np.asarray(mesh.tri_verts)
tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True)
np.savez_compressed(HERE/'head_entry_obstacle_union.npz',vertices_mm=vertices,triangles=triangles)
print('ENTRY_UNION_READY',len(vertices),len(triangles),time.time()-started,flush=True)
direction=Vector((.932173,.271419,.241973)).normalized()

def inside(point):
    origin=Vector(point);count=0
    for _ in range(80):
        loc,normal,index,distance=tree.ray_cast(origin,direction)
        if loc is None:return bool(count%2)
        count+=1;origin=loc+direction*1e-5
    return None

axes=[np.arange(a,b+.01,1.) for a,b in zip(lo,hi)]
grid=np.stack(np.meshgrid(*axes,indexing='ij'),axis=-1);shape=grid.shape[:3]
clearance=np.zeros(shape,dtype=np.float32);unresolved=0
for i in range(shape[0]):
    for j in range(shape[1]):
        for k in range(shape[2]):
            point=grid[i,j,k];distance=tree.find_nearest(Vector(point))[3]
            if distance<.1:continue
            hit=inside(point)
            if hit is None:unresolved+=1;continue
            clearance[i,j,k]=-distance if hit else distance
    if i%5==0:print('ENTRY_CLEARANCE_SLICE',i+1,shape[0],time.time()-started,flush=True)

# A widest-path graph avoids guessing a few Bézier shapes. Its positive edge
# capacity subtracts half the full edge length, so the entire straight edge is
# covered by the endpoint distances. The final cable must additionally bend.
deltas=[(a,b,c) for a,b,c in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
flat=clearance.ravel();strides=np.array([shape[1]*shape[2],shape[2],1]);best=np.full(len(flat),-np.inf)
previous=np.full(len(flat),-1,dtype=np.int32);heap=[]
start_mask=(grid[:,:,:,0]>=40)&(abs(grid[:,:,:,1])<=10)&(grid[:,:,:,2]<=159)
starts=np.flatnonzero(start_mask.ravel()&(flat>.5))
for n in starts:best[n]=float(flat[n]);heapq.heappush(heap,(-best[n],int(n)))
targets=(grid[:,:,:,0]>=16)&(grid[:,:,:,0]<=30)&(abs(grid[:,:,:,1])>=23)&(grid[:,:,:,2]>=199)
target_ids=set(np.flatnonzero(targets.ravel()&(flat>.5)).tolist());end=None
while heap:
    neg,n=heapq.heappop(heap);score=-neg
    if score<best[n]-1e-9:continue
    if n in target_ids:end=n;break
    index=np.array(np.unravel_index(n,shape))
    for delta in deltas:
        near=index+delta
        if np.any(near<0) or np.any(near>=shape):continue
        q=int(np.dot(near,strides));capacity=min(float(flat[n]),float(flat[q]))-.5
        value=min(score,capacity)
        if value>best[q] and value>0:
            best[q]=value;previous[q]=n;heapq.heappush(heap,(-value,q))
path=[]
if end is not None:
    n=end
    while n>=0:path.append(grid.reshape(-1,3)[n].tolist());n=int(previous[n])
    path.reverse()
np.savez_compressed(HERE/'head_entry_clearance.npz',grid_mm=grid,clearance_mm=clearance)
out=dict(status='PASS' if path else 'BLOCKED',scope='Finite 1mm clearance graph in yaw coordinates; not a complete routed harness',
         source_blend_sha256=before,source_instances=sources,union_vertices=len(vertices),union_triangles=len(triangles),
         examined_box_min_mm=lo.tolist(),examined_box_max_mm=hi.tolist(),grid_spacing_mm=1.,node_count=int(flat.size),
         yaw_samples=list(range(-60,61,10)),pitch_samples=list(range(-20,26,5)),unresolved_inside_nodes=unresolved,
         start_node_count=int(len(starts)),target_node_count=len(target_ids),path_mm=path,
         certified_graph_path_clearance_mm=float(best[end]) if end is not None else None,
         implied_round_allocation_diameter_after_point3_gap_mm=max(0.,2*(float(best[end])-.3)) if end is not None else None,
         minimum_bend='NOT_TESTED',actual_connector_endpoints='NOT_TESTED',installation='NOT_TESTED',
         actual_wire_count='NOT_TESTED',actual_harness='NOT_TESTED',main_geometry_changed=False,elapsed_s=time.time()-started,
         limits=['Physical obstacles are swept over finite poses, not continuous motion.',
                 'This positive-side local region is not an exhaustive search of all robot space.',
                 'Grid path corners are not bend-qualified and cannot be used as wires.',
                 'Diameter from clearance does not establish capacity for 11 functional conductors.',
                 'No fixed points, supports, real cable construction or installation paths are defined.'])
(HERE/'head_entry_space.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('ENTRY_SPACE_COMPLETE',out['status'],out['certified_graph_path_clearance_mm'],len(path),time.time()-started,flush=True)
