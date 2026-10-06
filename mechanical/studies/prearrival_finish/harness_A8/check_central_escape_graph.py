"""Widest finite graph exit through zero-pose or named finite-pose obstacles.

Spherical wire clearance only; no bending, retention or motion qualification.
All accepted edges use a nearest-surface bound covering the complete segment.
"""
from pathlib import Path
import json,math,hashlib,heapq,time,collections,sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
mode='body' if '--lower' in sys.argv else 'yaw' if '--upper' in sys.argv else 'zero'
mesh_path=HERE/('central_occupied_zero.npz' if mode=='zero' else f'central_{mode}_obstacle_union.npz');mesh=np.load(mesh_path)
tree=BVHTree.FromPolygons(mesh['vertices_mm'],mesh['triangles'],all_triangles=True)
source=json.loads((HERE/('central_void_check.json' if mode=='zero' else 'central_route_unions.json')).read_text())
if mode!='zero':assert next(x['sha256'] for x in source['frames'] if x['frame']==mode)==hashlib.sha256(mesh_path.read_bytes()).hexdigest()
zmin,zmax=(134.,160.) if mode=='body' else (180.,205.) if mode=='yaw' else (134.,206.)
root_z=150. if mode=='body' else 182. if mode=='yaw' else 166.
rs=np.arange(0,36.01,.4);zs=np.arange(zmin,zmax+.01,.5);angles=np.arange(0,360,5)
shape=(len(rs),len(angles),len(zs));strides=np.array([shape[1]*shape[2],shape[2],1])
def key(index):return int(np.dot(index,strides))
def idx(k):return np.array(np.unravel_index(k,shape))
def point(index):
    ir,ia,iz=index;a=math.radians(float(angles[ia]));r=float(rs[ir])
    return np.array([r*math.cos(a),r*math.sin(a),float(zs[iz])])
positions={};distances={}
def position(k):
    if k not in positions:positions[k]=point(idx(k))
    return positions[k]
def dist(k):
    if k not in distances:distances[k]=tree.find_nearest(Vector(position(k)))[3]
    return distances[k]
start_index=np.array([17,0,int((root_z-zmin)/.5)]);root=key(start_index)
best={root:dist(root)};parents={};edge_bounds={};queue=[(-best[root],root)]
started=time.time();expanded=0;end=None;witness=None
required=.6604/2+.3
while queue:
    neg,k=heapq.heappop(queue);score=-neg
    if score<best[k]-1e-9:continue
    index=idx(k);r=rs[index[0]];z=zs[index[2]]
    reached=(r>=30 or z<=136) if mode=='body' else (r>=30 or z>=204) if mode=='yaw' else (r>=30 or z<=136 or z>=204)
    if reached:
        end=k;break
    expanded+=1
    if expanded%5000==0:print('A8_CENTRAL_GRAPH',expanded,len(queue),score,round(time.time()-started,1),flush=True)
    if score<required and witness is None:witness={'expanded_nodes_before_threshold_loss':expanded,'best_remaining_clearance_bound_mm':score}
    for axis,delta in [(0,-1),(0,1),(1,-1),(1,1),(2,-1),(2,1)]:
        other=index.copy();other[axis]+=delta
        if axis==1:other[axis]%=shape[axis]
        elif other[axis]<0 or other[axis]>=shape[axis]:continue
        near=key(other);dnear=dist(near)
        if dnear<=0 or min(score,dnear)<=best.get(near,0)+1e-9:continue
        a,b=position(k),position(near);ln=float(np.linalg.norm(b-a))
        if ln<1e-9:continue
        capacity=min(dist(k),dnear)-ln/2
        if capacity<min(score,required):
            samples=np.linspace(a,b,17)
            capacity=min(tree.find_nearest(Vector(p))[3] for p in samples)-ln/32-1e-5
        value=min(score,capacity)
        if value>best.get(near,0)+1e-9 and value>0:
            best[near]=value;parents[near]=k;edge_bounds[near]=capacity
            heapq.heappush(queue,(-value,near))
path=[]
if end is not None:
    k=end
    while True:
        path.append(position(k).tolist())
        if k==root:break
        k=parents[k]
    path.reverse()
reachable_keys=[k for k,v in best.items() if v>=required]
reachable_points=np.asarray([position(k) for k in reachable_keys])
reachable_summary=None
if len(reachable_points):
    radial=np.linalg.norm(reachable_points[:,:2],axis=1)
    reachable_summary=dict(node_count=len(reachable_points),
        radial_range_mm=[float(radial.min()),float(radial.max())],
        z_range_mm=[float(reachable_points[:,2].min()),float(reachable_points[:,2].max())])
cloud_path=HERE/f'central_{mode}_reachable_nodes.npz'
np.savez_compressed(cloud_path,points_mm=reachable_points,clearance_lower_bounds_mm=np.array([best[k] for k in reachable_keys]))
out=dict(status='PASS' if end is not None and best[end]>=required else 'BLOCKED',
    scope='Finite cylindrical graph; zero-pose or named finite-pose union, not an exhaustive free-space or full wire route proof',
    coordinate_frame=mode,
    source_blend_sha256=source['source_blend_sha256'],source_mesh_sha256=hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
    steps={'radial_mm':.4,'angle_deg':5,'z_mm':.5},root_mm=position(root).tolist(),
    target=('radius>=30 mm OR Z<=136 mm' if mode=='body' else 'radius>=30 mm OR Z>=204 mm' if mode=='yaw' else 'radius>=30 mm OR Z<=136 mm OR Z>=204 mm'),wire_od_max_mm=.6604,project_gap_mm=.3,
    required_centreline_clearance_mm=required,widest_grid_path_clearance_bound_mm=best[end] if end is not None else None,
    path_mm=path,expanded_nodes=expanded,queried_nodes=len(distances),threshold_witness=witness,
    reachable_with_wire_radius_and_project_gap=reachable_summary,
    reachable_nodes_file=cloud_path.name,reachable_nodes_sha256=hashlib.sha256(cloud_path.read_bytes()).hexdigest(),
    main_geometry_changed=False,elapsed_s=time.time()-started,minimum_bend='NOT_TESTED',
    finite_pose_obstacles_included=mode!='zero',continuous_motion='NOT_TESTED',
    limits=['Clearance lower bounds cover the edges in this graph, but do not upper-bound every possible continuous path.',
        'The search begins in a previously checked exterior point. Positive edge bounds prevent entering a solid without crossing its surface.',
        'Corners in a graph route are not cable bends or an installable harness.'])
(HERE/('central_escape_graph.json' if mode=='zero' else f'central_{mode}_escape_graph.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('A8_CENTRAL_GRAPH_COMPLETE',out['status'],out['widest_grid_path_clearance_bound_mm'],expanded,round(time.time()-started,1),flush=True)
