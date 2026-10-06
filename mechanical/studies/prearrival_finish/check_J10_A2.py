"""Read-only A2 side-entry envelope screen; never adopt the failed PCB candidate."""
from pathlib import Path
import sys, json, hashlib, itertools
HERE=Path(__file__).resolve().parent
M=HERE.parents[1]
sys.path.insert(0,str(M/'scripts'))
from common import *
from validate import Solid
from native_electronics import board_transform, source_mesh, solid_from

load_collections();assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
handoff_path=PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A2.json'
h=json.loads(handoff_path.read_text());j=h['J10_side_entry']
assert j['status']=='FAIL' and not h['native_boards_replaced']
cache=source_mesh(P['native_electronics']['boards']['power']['mesh'])
r,t=board_transform('power',cache)
pcb=next(c for c in cache['components'] if c['reference']=='PCB')
top=pcb['bounds_xyz_mm'][2][1]
assert np.max(np.abs(r-np.eye(3)))<1e-8, 'Re-derive rotated envelope transform explicitly'
def box(lo,hi):
    points=np.array([r@np.array([x,-y,z+top])+t for x,y,z in itertools.product(*zip(lo,hi))])
    a,b=points.min(0),points.max(0)
    return manifold.Manifold.cube((b-a).tolist()).translate(a.tolist()),[a.tolist(),b.tolist()]
body,body_bounds=box([38.25,25.05,0],[45.85,42.95,4.8])
mated,mated_bounds=box(j['mated_bounds_board_xyz_mm']['minimum'],j['mated_bounds_board_xyz_mm']['maximum'])
exit_axis=r@np.array([-1.,0,0])
obstacles={o.name.removeprefix(PREFIX):Solid(o).m for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon'] and o.name!=PREFIX+'Power_Module'}
fallbacks=[]
for c in cache['components']:
    if c['reference']=='J10':continue
    pieces=[]
    for i,s in enumerate(c['solids']):
        v=np.asarray(s['vertices_mm'])@r.T+t
        pieces.append(solid_from(v,s['triangles'],c['reference']+'/'+str(i),fallbacks))
    obstacles['Power/'+c['reference']]=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
def hits(m):
    rows=[];bb=m.bounding_box()
    for name,other in obstacles.items():
        ob=other.bounding_box()
        if any(bb[i+3]<=ob[i]+1e-6 or ob[i+3]<=bb[i]+1e-6 for i in range(3)):continue
        volume=(m^other).volume()
        if volume>.001:rows.append(dict(object=name,intersection_mm3=volume))
    return sorted(rows,key=lambda a:-a['intersection_mm3'])
paths=[]
for offset in np.linspace(0,j['unplug_straight_allocation_mm'],49):
    collisions=hits(mated.translate((exit_axis*offset).tolist()))
    if collisions:paths.append(dict(offset_mm=float(offset),overlaps=collisions))
wire_zone,wire_bounds=box([31.25,25.05,0],[36.25,42.95,4.8])
out=dict(revision=P['revision'],source_blend_sha256=source_hash,handoff=str(handoff_path.relative_to(PROJECT)),
         handoff_sha256=hashlib.sha256(handoff_path.read_bytes()).hexdigest(),
         status='BLOCKED',scope='Conservative vendor-envelope screen, not detailed connector contact or actual cable-fit certification',
         body_world_bounds_mm=body_bounds,mated_world_bounds_mm=mated_bounds,wire_exit_world_axis=exit_axis.tolist(),
         native_coordinate_conversion='KiCad +Y down -> source cache -Y; envelope Z0 added to actual PCB top, then unchanged board rigid transform',
         body_overlaps=hits(body),mated_overlaps=hits(mated),unplug_distance_allocation_mm=12.,
         unplug_samples=49,unplug_blocked_samples=paths,
         provisional_exit_corridor=dict(length_mm=5,world_bounds_mm=wire_bounds,overlaps=hits(wire_zone),
             evidence='ASSUMED full exit-face corridor, not eight real wire exit positions'),
         numerical_proxy_fallbacks=fallbacks,
         limits=['AABB overlap identifies space to reserve or inspect, not proof detailed parts touch.',
                 'Whole mated AABB swept conservatively; stationary socket region included, so false-positive rejection is possible.',
                 'No selected finished harness diameter/terminal exits. New Alpha5853 sample needs10.922mm conservative bend reference and5mm assumed straight exit, so old R6 paths are not approved.',
                 'No board/hole/footprint/frame edits; electrical C1 remains FAIL and outside the main model.'],
         main_modified=False,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash)
(HERE/'J10_A2_envelope_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('J10_A2_SCREEN',out['body_overlaps'],out['mated_overlaps'],'blocked_samples',len(paths),flush=True)
