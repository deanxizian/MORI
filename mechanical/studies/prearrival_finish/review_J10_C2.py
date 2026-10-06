# -*- coding: utf-8 -*-
"""Independent C2 nominal-space review. Candidate-only; main geometry read-only."""
from pathlib import Path
import sys,json,hashlib,itertools,math
HERE=Path(__file__).resolve().parent
helper=(HERE/'check_J10_A2.py').read_text().split('body,body_bounds=')[0]
exec(compile(helper,str(HERE/'check_J10_A2.py'),'exec'),globals())
from mathutils.bvhtree import BVHTree
from interface_completion import axial
HARD=PROJECT/'hardware/v1_2/prearrival_20261002/j10_refinement_C2'
record_path=HARD/'backside_screen.json'
record=json.loads(record_path.read_text())
assert record['source_hashes']['mechanical/mori_v1_2.blend']==source_hash
OUT=HERE/'J10_C2_review';OUT.mkdir(exist_ok=True)
shape_objects={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon'] and o.name!=PREFIX+'Power_Module'}
obstacles={n:s.m for n,s in shape_objects.items()}
fallbacks=[]
for c in cache['components']:
    if c['reference'] in ['J10','D30','F70']:continue
    pieces=[solid_from(np.asarray(s['vertices_mm'])@r.T+t,s['triangles'],c['reference']+'/'+str(i),fallbacks) for i,s in enumerate(c['solids'])]
    obstacles['Power/'+c['reference']]=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
def hits(m):
    rows=[];bb=m.bounding_box()
    for n,other in obstacles.items():
        ob=other.bounding_box()
        if any(bb[i+3]<=ob[i]+1e-6 or ob[i+3]<=bb[i]+1e-6 for i in range(3)):continue
        v=(m^other).volume()
        if v>.001:rows.append(dict(object=n,intersection_mm3=v))
    return sorted(rows,key=lambda a:-a['intersection_mm3'])

back=[]
for row in record['backside_envelopes']:
    name=row['reference'];lo,hi=row['board_bounds_mm'];m,bb=box(lo,hi)
    collisions=hits(m)
    # Find the first collision when moving the entire envelope downwards.
    # This is an extra-thickness capacity probe, not a manufacturing tolerance.
    first=None
    for dz in np.arange(.02,8.001,.02):
        hh=hits(m.translate([0,0,-float(dz)]))
        if hh:first=dict(extra_downward_travel_mm=float(dz),objects=hh);break
    back.append(dict(reference=name,native_bounds_mm=[lo,hi],world_bounds_mm=bb,
        supplied_back_depth_mm=float(hi[2]-lo[2]),actual_overlaps=collisions,
        downward_capacity_probe=first,
        minimum_remaining_gap_lower_bound_mm=None if first is None else max(0,first['extra_downward_travel_mm']-.02),
        gap_scope='Downward translation of the whole conservative envelope on a0.02mm finite grid; not general Euclidean clearance or load/thermal approval'))
    obstacles['Power/'+name+'_BACK_CANDIDATE']=m

body,body_bounds=box([38.25,25.05,0],[45.85,42.95,4.8])
plug_m,plug_bounds=box([36.25,25.1,0],[43.10,42.9,4.8])
path=[]
# Continuous swept boxes are exact for translating this axis-aligned envelope.
withdraw,withdraw_bounds=box([36.25-5.35,25.1,0],[43.10,42.9,4.8])
lift,lift_bounds=box([36.25-5.35,25.1,0],[43.10-5.35,42.9,16.8])
path.append(dict(phase='withdraw5.35',bounds_mm=withdraw_bounds,overlaps=hits(withdraw)))
path.append(dict(phase='lift12',bounds_mm=lift_bounds,overlaps=hits(lift)))

# Analytic one-quarter bends for individual wire lanes, retaining the new
#10.922mm centreline radius and5mm unbent terminal allocation. Crimp Z is not
# documented: probe candidate heights, retain them as ASSUMED, never snap a
# terminal to whichever height clears and call it actual hardware.
wire_od=1.0922;wire_R=10.922;straight=5.;clear=.3
trees={}
for n,m in obstacles.items():
    data=m.to_mesh64();trees[n]=BVHTree.FromPolygons([Vector(v) for v in data.vert_properties[:,:3]],data.tri_verts.tolist(),all_triangles=True)
def wire_clear(points, radius):
    near=[];step=.2;extra=step/2
    for a,b in zip(points,points[1:]):
        for alpha in np.linspace(0,1,max(2,int(np.linalg.norm(b-a)/step)+2)):
            p=a+alpha*(b-a)
            for n,m in obstacles.items():
                bb=m.bounding_box()
                if any(p[i]<bb[i]-radius-extra or p[i]>bb[i+3]+radius+extra for i in range(3)):continue
                q,normal,_,d=trees[n].find_nearest(Vector(p))
                if d<radius+extra or (Vector(p)-q).dot(normal)<-.0001:
                    return dict(status='FAIL',first_point_mm=p.tolist(),blockers=[n])
    return dict(status='PASS')

def bend_points(y,z,theta_deg):
    e=np.array([plug_bounds[0][0],y,top+t[2]+z])
    axis=np.array([-1.,0,0]); direction=np.array([0,math.cos(math.radians(theta_deg)),math.sin(math.radians(theta_deg))])
    start=e+axis*straight
    bend=[start+wire_R*(math.sin(a)*axis+(1-math.cos(a))*direction) for a in np.linspace(0,math.pi/2,91)]
    return np.array([e,*bend])
local_bends=[]
for z in [1.2,2.4,3.6]:
    for angle in [30,45,60,75,90,105,120,135,150]:
        rs=[]
        for i in range(8):
            native_y=27+2*i
            y=float((r@np.array([0,-native_y,0])+t)[1])
            curve=bend_points(y,z,angle)
            rs.append(dict(pin=i+1,**wire_clear(curve,wire_od/2+clear)))
        local_bends.append(dict(assumed_wire_height_above_pcb_mm=z,bend_direction_angle_from_robot_Y_deg=angle,
            pins=rs,status='PASS' if all(p['status']=='PASS' for p in rs) else 'FAIL'))
        print('C2_BEND',z,angle,sum(p['status']=='PASS' for p in rs),flush=True)

# Check declared gripping allowances, not an invented anthropometric standard.
#8mm and10mm cylinders approach the exposed plug end along X; physical hand
#access, grip force and connector latch service remain unqualified.
grip=[]
center=np.mean(plug_bounds,axis=0)
for d in [8,10]:
    tool=axial(d/2,20,[plug_bounds[0][0]-10,center[1],center[2]],[1,0,0])
    grip.append(dict(diameter_allocation_mm=d,length_mm=20,overlaps=hits(tool),
                     evidence='ASSUMED straight gripping-tool corridor, not a selected tool or human finger model'))
out=dict(revision=P['revision'],status='BLOCKED',scope='Independent C2 local nominal geometry only; no adoption',
    source_blend_sha256=source_hash,hardware_study=str(record_path.relative_to(PROJECT)),
    hardware_study_sha256=hashlib.sha256(record_path.read_bytes()).hexdigest(),
    backside=back,body_overlaps=hits(body),plug_overlaps=hits(plug_m),continuous_swept_boxes=path,
    candidate_bends=local_bends,grip_corridors=grip,
    wiring=dict(wire_outer_diameter_max_mm=wire_od,wire_bend_radius_mm=wire_R,terminal_straight_allocation_mm=straight,
        actual_crimp_exit_height_mm=None,complete_route=False,plug_with_attached_harness_path=False),
    numerical_fallbacks=fallbacks,main_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,
    limits=['D30/F70 package envelopes include the supplied0.15mm assumed installation allowance.',
        'Local backside geometric allowance is a candidate limit, not approval to change historical contract or adopted PCB.',
        'C2 remains an unrouted/unqualified hardware candidate until owner handoff; PCB must remain readonly here.',
        'PHR width/length received; exact seating Z, contact release, latch operation, terminal exit and tolerances not qualified.',
        'Quarter bends are only local nominal lane screening; no finished bundle/fanout, other harness or service slack design.',
        'Plug withdrawal/lift of the housing alone is not a harness removal qualification.'])
(OUT/'review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('C2_REVIEW_COMPLETE',[(r['reference'],r['minimum_remaining_gap_lower_bound_mm']) for r in back],flush=True)
