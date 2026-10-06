"""Current rigid geometry + unchanged native ports; no holes or board edits.

Explore a broad rear-side route for the IMU instead of adopting the failed
feedthrough. Cable envelopes remain requirements, not purchased-wire data.
"""
from pathlib import Path
import hashlib,json,time
REVIEW=Path(__file__).resolve().parent
PREVIOUS=REVIEW.parent/'prearrival_closure'
helper=(PREVIOUS/'harness_routes.py').read_text().split('specs=')[0]
exec(compile(helper,str(PREVIOUS/'harness_routes.py'),'exec'),globals())
source=Path(bpy.data.filepath);source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
# Original native connector datums are unchanged except the received rear J3.
hand=json.loads((PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json').read_text())
p=plug['rear_J3'];cc=(p.lo+p.hi)/2;bb=hand['rear_J3']['nominal_screen']['plug_world_bounds_mm'];tt=(np.array(bb[:3])+bb[3:])/2
tr=Matrix.Translation(Vector(tt))@Matrix.Rotation(math.pi,4,'X')@Matrix.Translation(-Vector(cc))
p.o.matrix_world=tr@p.o.matrix_world;bpy.context.view_layer.update();plug['rear_J3']=Solid(p.o)
obstacles=dict(ss);obstacles.update({'Plug_'+k:v for k,v in plug.items()})
trees={n:BVHTree.FromPolygons([Vector(v) for v in s.v],s.f.tolist(),all_triangles=True) for n,s in obstacles.items()}
obs=list(obstacles);los=np.array([obstacles[n].lo for n in obs]);his=np.array([obstacles[n].hi for n in obs])
prior=json.loads((PREVIOUS/'harness_routes.json').read_text())
received=json.loads((PREVIOUS/'p5r7_receipt/route_replay.json').read_text())
overrides={r['id']:r for r in received['rows'] if r.get('route_changed')}
rows=[]
for row in prior['static_routes']:
    if row['status']!='PASS':continue
    row=json.loads(json.dumps(row));row.update(overrides.get(row['id'],{}))
    points=np.array(row['curve_mm']);r=row['bundle_diameter_allocation_mm']/2
    hs=solid_hits(points,r);row.update(solid_hits=hs,status='PASS' if not hs else 'FAIL')
    rows.append(row);print('CURRENT_STATIC',row['id'],row['status'],flush=True)

def distinct(points):
    out=[]
    for p in points:
        if not out or np.linalg.norm(p-out[-1])>.001:out.append(np.array(p,dtype=float))
    # Remove straight-through intermediate points before radius trimming.
    # Otherwise two right-angle trims on an artificial short middle segment
    # can reject a physically continuous straight run.
    i=1
    while i<len(out)-1:
        u=out[i]-out[i-1];v=out[i+1]-out[i]
        if np.dot(u,v)/(np.linalg.norm(u)*np.linalg.norm(v))>.999999:
            out.pop(i)
        else:i+=1
    return out

def imu_controls(a,b,aa,ab):
    # Route down behind the existing deck, then travel inward below it.
    # Keep the end segment aligned with each actual connector exit normal.
    # A single broad lower elbow avoids artificially short alternating bends.
    for yback,zup,zdown in itertools.product([-67,-68,-66,-69],[142,144,146,148],[84,86,88]):
        yield distinct([a,[a[0],a[1],zup],[b[0],a[1],zup],
            [b[0],yback,zup],[b[0],yback,zdown],[b[0],b[1],zdown],b])
    for dx,yback,zup,zdown in itertools.product([0,8,-8,16,-16],[-67,-68,-66,-69],[142,144,146,148],[84,86,88]):
        yield distinct([a,[a[0],a[1],zup],[dx,a[1],zup],[dx,yback,zup],
            [dx,yback,zdown],[b[0],b[1],zdown],b])
    for dx,yback,zup,zdown,yfront in itertools.product([0,8,-8,16,-16,b[0]],[-67,-68,-66,-69],[140,138,142,144,146],[86,84,88,90],[-57,-54,-60]):
        yield distinct([a,[a[0],a[1],zup],[dx,a[1],zup],[dx,yback,zup],
            [dx,yback,zdown],[dx,yfront,zdown],[b[0],yfront,zdown],
            [b[0],b[1],zdown],b])

attempts=[]
for hid,rad,R,shift in [('H04',2.5,8,0),('H04_splitA',1.4,6,-4),('H04_splitB',1.4,6,4)]:
    if hid!='H04' and any(r['id']=='H04' and r['status']=='PASS' for r in rows):break
    ea,a,aa=endpoint('motion_J4',rad);eb,b,ab=endpoint('imu_J1',rad)
    ea+=np.array([shift,0,0]);a+=np.array([shift,0,0]);eb+=np.array([shift,0,0]);b+=np.array([shift,0,0])
    print('ENDPOINTS',hid,a.tolist(),b.tolist(),aa.tolist(),ab.tolist(),flush=True)
    counts=dict(tried=0,short_bends=0,collision=0);start=time.time();best=None;closest=None;best_free=-1
    for control in imu_controls(a,b,aa,ab):
        counts['tried']+=1;curve=rounded(control,R)
        if curve is None:
            counts['short_bends']+=1
            if counts['tried']==1:print('FIRST_CONTROLS',hid,[p.tolist() for p in control],flush=True)
            continue
        points=resample(curve,.6);nfree=0
        for p in points:
            if not free(p,rad+.3):break
            nfree+=1
        if nfree>best_free:
            best_free=nfree;closest=dict(controls_mm=[p.tolist() for p in control],first_blocked_point_mm=None if nfree==len(points) else points[nfree].tolist(),passed_samples=nfree,total_samples=len(points))
        if nfree!=len(points):counts['collision']+=1;continue
        hs=solid_hits(curve,rad)
        if hs:counts['collision']+=1;continue
        best=dict(id=hid,status='PASS',from_port='motion_J4',to_port='imu_J1',
                  curve_mm=[p.tolist() for p in curve],controls_mm=[p.tolist() for p in control],
                  exit_faces_mm=[ea.tolist(),eb.tolist()],solid_hits=[],
                  bundle_diameter_allocation_mm=rad*2,analytic_arc_radius_mm=R,
                  length_mm=sum(float(np.linalg.norm(q-p)) for p,q in zip(curve,curve[1:])),
                  curve_construction='Analytic tangent circular arcs',data_status='ASSUMED cable envelope; documented native ports')
        break
    result=best or dict(id=hid,status='BLOCKED',bundle_diameter_allocation_mm=rad*2,
         analytic_arc_radius_mm=R,closest_candidate=closest,reason='Finite same-solid corridor search did not satisfy bend/clearance. Not a proof of impossibility; no opening adopted.')
    result['search']=dict(**counts,elapsed_s=time.time()-start);rows.append(result);attempts.append(result)
    print('IMU_CURRENT',hid,result['status'],result['search'],flush=True)
    (REVIEW/'imu_route_search_progress.json').write_text(json.dumps(attempts,indent=2)+'\n')

# Segment-to-segment distances include wire-to-wire crowding, which earlier
# per-route checks omitted. No connected-harness overlap is silently waived.
def segment_distance(p,q,r,s):
    u=q-p;v=s-r;w=p-r;a=u@u;b=u@v;c=v@v;d=u@w;e=v@w
    def point_segment(x,y,z):
        v=z-y;vv=v@v;t=np.clip((x-y)@v/vv,0,1) if vv>1e-12 else 0
        return float(np.linalg.norm(x-y-t*v))
    distances=[point_segment(p,r,s),point_segment(q,r,s),point_segment(r,p,q),point_segment(s,p,q)]
    det=a*c-b*b
    if det>1e-12:
        t=(b*e-c*d)/det;z=(a*e-b*d)/det
        if 0<=t<=1 and 0<=z<=1:distances.append(float(np.linalg.norm(w+t*u-z*v)))
    return min(distances)
crowding=[]
passed=[r for r in rows if r['status']=='PASS']
for i,a in enumerate(passed):
    for b in passed[i+1:]:
        ap=resample(a['curve_mm'],1);bp=resample(b['curve_mm'],1)
        required=(a['bundle_diameter_allocation_mm']+b['bundle_diameter_allocation_mm'])/2
        nearest=1e9;where=None
        for p,q in zip(ap,ap[1:]):
            for r,s in zip(bp,bp[1:]):
                if np.any(np.maximum(p,q)+required<np.minimum(r,s)) or np.any(np.maximum(r,s)+required<np.minimum(p,q)):continue
                dist=segment_distance(p,q,r,s)
                if dist<nearest:nearest=dist;where=[((p+q)/2).tolist(),((r+s)/2).tolist()]
        if nearest<required+.3:crowding.append(dict(a=a['id'],b=b['id'],distance_mm=nearest,required_no_overlap_mm=required,locations_mm=where,status='FAIL' if nearest<required else 'BLOCKED'))
out=dict(revision=P['revision'],source_blend_sha256=source_hash,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,
    source_helper_sha256=hashlib.sha256((PREVIOUS/'harness_routes.py').read_bytes()).hexdigest(),
    routes=rows,wire_to_wire=crowding,status='BLOCKED',new_print_cuts=False,cut_lengths_released=False,
    limitations=['Static bodies and received mating-housing envelopes only; not complete harness qualification.',
       'Unknown insulation, terminal fanout, strain relief and moving-head loops remain explicit.',
       'Lengths are geometric centerlines without assembly/slack/termination allowance, not cutting instructions.'])
(REVIEW/'body_routes_current.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('BODY_ROUTES_DONE',len(rows),'wire_conflicts',len(crowding),flush=True)
