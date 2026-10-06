# -*- coding: utf-8 -*-
"""Read-only independent review of the received A3 placement; never adopt it."""
from pathlib import Path
import sys,json,hashlib,itertools,math,time
HERE=Path(__file__).resolve().parent
helper=(HERE/'check_J10_A2.py').read_text().split('body,body_bounds=')[0]
exec(compile(helper,str(HERE/'check_J10_A2.py'),'exec'),globals())
from mathutils.bvhtree import BVHTree
from interface_completion import axial
from mathutils import Matrix

OUT=HERE/'J10_A3_review';OUT.mkdir(exist_ok=True)
handoff=PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A3_J10.json'
A3=json.loads(handoff.read_text());start=time.time()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not A3['native_boards_replaced'] and not A3['mechanical_main_modified']
sources={str(handoff.relative_to(PROJECT)):sha(handoff)}
for path,digest in {**A3['native_source_manifest'],**A3['candidate']['hashes']}.items():
    assert sha(PROJECT/path)==digest,path
    sources[path]=digest
assert sha(PROJECT/A3['previous_addendum'])==A3['previous_addendum_sha256']
sources[A3['previous_addendum']]=A3['previous_addendum_sha256']

objects={o.name.removeprefix(PREFIX):o for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon'] and o.name!=PREFIX+'Power_Module'}
obstacles={n:Solid(o).m for n,o in objects.items()};fallbacks=[]
groups={n:o.get('group') for n,o in objects.items()}
JP=None
for c in cache['components']:
    ref=c['reference']
    if ref in ['J10','D30','F70','R50']:continue
    pieces=[]
    for i,s in enumerate(c['solids']):
        vv=np.asarray(s['vertices_mm'],float)
        if ref=='JP70':
            # Old pad2=(39.04,-44.5) -> new pad2=(35,-47.04), exact
            # native footprint rigid transform; never resize the connector.
            rot=np.array([[0,1,0],[-1,0,0],[0,0,1]])
            vv=(vv-np.array([36.5,-44.5,0]))@rot.T+np.array([35,-44.5,0])
        pieces.append(solid_from(vv@r.T+t,s['triangles'],ref+'/'+str(i),fallbacks))
    obstacles['Power/'+ref]=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
    if ref=='JP70':JP=obstacles['Power/'+ref]

def hits(m,ignore=()):
    rows=[];bb=m.bounding_box()
    for n,other in obstacles.items():
        if n in ignore:continue
        ob=other.bounding_box()
        if any(bb[i+3]<=ob[i]+1e-6 or ob[i+3]<=bb[i]+1e-6 for i in range(3)):continue
        v=(m^other).volume()
        if v>.001:rows.append(dict(object=n,intersection_mm3=v))
    return sorted(rows,key=lambda q:-q['intersection_mm3'])

back=[]
for row in A3['backside_candidates']:
    lo,hi=row['board_bounds_mm'];m,bb=box(lo,hi)
    original_hits=hits(m);first=None
    for dz in np.arange(.02,8.001,.02):
        hh=hits(m.translate([0,0,-float(dz)]))
        if hh:first=dict(extra_downward_travel_mm=float(dz),objects=hh);break
    back.append(dict(reference=row['reference'],world_bounds_mm=bb,actual_overlaps=original_hits,
        supplied_back_depth_mm=hi[2]-lo[2],basis=A3['backside_basis'][row['reference']],
        extra_downward_clearance_lower_bound_mm=None if first is None else max(0,first['extra_downward_travel_mm']-.02),first_downward_hit=first))
    obstacles['Power/'+row['reference']+'_BACK_CANDIDATE']=m

j=A3['J10'];body,body_bounds=box(*j['body_bounds_board_mm']);plug,plug_bounds=box(*j['moving_plug_bounds_board_mm'])
body_hits=hits(body);plug_hits=hits(plug)
withdraw,wb=box([30.9,25.1,0],[43.1,42.9,4.8])
lift,lb=box([30.9,25.1,0],[37.75,42.9,16.8])
path=[dict(phase='withdraw5.35',world_bounds_mm=wb,overlaps=hits(withdraw)),dict(phase='lift12',world_bounds_mm=lb,overlaps=hits(lift))]

# Exact source JP70 geometry is a KiCad library reference, not selected SKU.
# Its intentional PCB through-pin intersection is separately listed, not
# hidden behind a general waiver. Electrical finished-hole fit is not checked.
jp=dict(world_bounds_mm=list(JP.bounding_box()),all_overlaps=hits(JP,{'Power/JP70'}),
        external_overlaps=hits(JP,{'Power/JP70','Power/PCB'}),mating_cap_selected=False)
bb=JP.bounding_box();cc=(np.array(bb[:3])+bb[3:])/2
ops=[]
for d in [3.,5.,8.]:
    tool=axial(d/2,20,[cc[0],cc[1],bb[5]+.1+10],[0,0,1])
    ops.append(dict(target='JP70',diameter_allocation_mm=d,length_mm=20,
        start_above_pin_top_mm=.1,overlaps=hits(tool,{'Power/JP70'})))
tp_native=A3['candidate']['changes']['TP71']['after']['xy_mm']
tp=r@np.array([tp_native[0],-tp_native[1],top])+t
for d in [1.,2.,3.]:
    tool=axial(d/2,25,(tp+np.array([0,0,12.55])).tolist(),[0,0,1])
    ops.append(dict(target='TP71',diameter_allocation_mm=d,length_mm=25,
        world_pad_centre_mm=tp.tolist(),start_above_pcb_mm=.05,overlaps=hits(tool)))

trees={};names=list(obstacles)
for n,m in obstacles.items():
    mesh=m.to_mesh64();trees[n]=BVHTree.FromPolygons([Vector(v) for v in mesh.vert_properties[:,:3]],mesh.tri_verts.tolist(),all_triangles=True)
boxes=np.array([obstacles[n].bounding_box() for n in names]);los=boxes[:,:3];his=boxes[:,3:]
def wire_clear(points,radius):
    for a,b in zip(points,points[1:]):
        for alpha in np.linspace(0,1,max(2,int(np.linalg.norm(b-a)/.2)+2)):
            p=a+alpha*(b-a);rr=radius+.1
            ids=np.where(np.all(p>=los-rr,axis=1)&np.all(p<=his+rr,axis=1))[0]
            for i in ids:
                n=names[i];q,normal,_,d=trees[n].find_nearest(Vector(p))
                if d<rr or (Vector(p)-q).dot(normal)<-.0001:
                    return dict(status='FAIL',first_point_mm=p.tolist(),blockers=[n])
    return dict(status='PASS')

def bend(y,z,theta,R):
    e=np.array([plug_bounds[0][0],y,top+t[2]+z]);axis=np.array([-1.,0,0])
    direction=np.array([0,math.cos(math.radians(theta)),math.sin(math.radians(theta))])
    start=e+axis*5
    return np.array([e,*[start+R*(math.sin(a)*axis+(1-math.cos(a))*direction) for a in np.linspace(0,math.pi/2,91)]])

wire_results=[]
for model,od,R in [('Alpha5853',1.0922,10.922),('Alpha6711_NOT_SELECTED',1.016,5.08)]:
    for z in [1.2,1.8,2.4,3.0,3.6]:
        for angle in [30,45,60,75,90,105,120,135,150]:
            curves=[];checks=[]
            for i in range(8):
                y=float((r@np.array([0,-27-2*i,0])+t)[1]);curve=bend(y,z,angle,R)
                curves.append(curve);checks.append(dict(pin=i+1,**wire_clear(curve,od/2+.3)))
            # Point-to-segment lower bound subtracts max sample chord/2;
            # conservative and explicitly finite, never compares endpoints
            # alone or mislabels single-wire checks as eight-wire packing.
            gaps=[]
            if all(v['status']=='PASS' for v in checks):
                for i,a in enumerate(curves):
                    for k,b in enumerate(curves[i+1:],i+1):
                        # Resample the5mm straight segment as well as the arc.
                        aa=np.concatenate([np.linspace(p,q,max(2,int(np.linalg.norm(q-p)/.1)+2))[:-1] for p,q in zip(a,a[1:])]+[a[-1:]])
                        v=np.diff(b,axis=0);w=aa[:,None,:]-b[:-1][None,:,:]
                        tt=np.clip(np.sum(w*v[None,:,:],axis=2)/np.maximum(np.sum(v*v,axis=1),1e-12),0,1)
                        dist=float(np.min(np.linalg.norm(w-tt[:,:,None]*v[None,:,:],axis=2)))
                        lower=dist-.051-od
                        gaps.append(dict(a=i+1,b=k+1,surface_clearance_lower_bound_mm=lower))
            wire_results.append(dict(wire=model,OD_max_mm=od,radius_mm=R,terminal_straight_allocation_mm=5,
                assumed_exit_z_above_pcb_mm=z,bend_angle_from_Y_deg=angle,pins=checks,
                wire_to_wire=gaps,status='PASS' if gaps and min(g['surface_clearance_lower_bound_mm'] for g in gaps)>=.3 else 'BLOCKED'))
        print('A3_WIRE',model,z,sum(x['status']=='PASS' for x in wire_results if x['wire']==model and x['assumed_exit_z_above_pcb_mm']==z),flush=True)

out=dict(revision=P['revision'],status='BLOCKED',scope='A3 independent mechanical review; complete PCB/harness not accepted',
    source_blend_sha256=source_hash,sources=sources,backside=back,body_overlaps=body_hits,plug_overlaps=plug_hits,
    continuous_swept_boxes=path,JP70=jp,straight_operating_allocations=ops,
    operations_scope='Unselected cylindrical tool corridors only, approach ends before contact; no selected jumper cap, grasp, latch release or electronics probe qualification.',
    local_eight_wire_bends=wire_results,actual_terminal_exit_height_mm=None,
    formal_PH_hole_issue=A3['formal_board_PH_hole_blocker'],head_group_map=groups,
    numerical_fallbacks=fallbacks,main_unchanged=sha(source)==source_hash,
    elapsed_s=time.time()-start,manufacturing_release=False,
    limitations=['A3 and all16 formal PCB project sources are immutable hash inputs.',
        'Moving PHR housing/straight tool envelopes are not a complete cable-attached service path.',
        'Quarter-bend wires are static local trials only. Exit heights are ASSUMED, not selected to certify fit.',
        'Six prior H01-H03 paths and IMU/other harnesses are not included in this local J10 check.',
        'R50 package and operating tools use explicit allocations; exact purchased interfaces remain unknown.',
        'Native PCB/contract sources, main geometry, animation and print exports were not modified.'])
(OUT/'review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('A3_COMPLETE',[(q['reference'],q['extra_downward_clearance_lower_bound_mm']) for q in back],flush=True)
