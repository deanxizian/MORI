"""Explore a finite family of exterior-neck clearance probes, not real harnesses.

Only the lower body-to-throat passage is assessed. Neither staging endpoint is
a connector/anchor. No bending-life, selected bundle or attached service loop
claim is made. No source object or source blend is saved.
"""
from pathlib import Path
import sys,json,hashlib,math,itertools,time,collections,csv
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from interface_completion import axial
from numpy.polynomial import polynomial as poly
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);before=hashlib.sha256(source.read_bytes()).hexdigest()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
obstacles={n:s for n,s in ss.items() if s.hi[2]>140 and s.lo[2]<177 and s.lo[0]<10 and s.hi[0]>-10}
trees={n:s.bvh() for n,s in obstacles.items()}
src=HERE.parent/'harness_A2/imu_individual_routes.py'
code=src.read_text();sample_t=np.linspace(0,1,65)
exec(compile(code[code.index('def bezier'):code.index('def check_points')],str(src),'exec'),globals())
wire_path=PROJECT/'hardware/v1_2/prearrival_20261002/harness_detail.csv'
wire_rows={r['线束']:r for r in csv.DictReader(wire_path.open(encoding='utf-8-sig'))}
R=float(wire_rows['P_J18']['厂家弯曲10D保守mm'])
grid_t=np.linspace(0,1,301);gap=.3;reasons=collections.Counter();tried=0;valid=[];start=time.time()

def screen(points,radius):
    # Source cubic chord length is bounded below; nearest-surface distances
    # subtract half that spacing plus circular/chord numerical allowance.
    chord=float(np.max(np.linalg.norm(np.diff(points,axis=0),axis=1)))
    clear=radius+gap+chord/2+.001
    for name,s in obstacles.items():
        mask=np.all(points>=s.lo-clear,axis=1)&np.all(points<=s.hi+clear,axis=1)
        for p in points[mask]:
            if trees[name].find_nearest(Vector(p))[3]<clear:return name
        if np.all(points>=s.lo) and np.all(points<=s.hi):
            probe=manifold.Manifold.sphere(.01,16).translate(points[0].tolist())
            if (probe^s.m).volume()>probe.volume()*.5:return name
    return None

# Endpoints are named study staging planes, deliberately not portrayed as
# port exits, clips, anchors or a mechanically adopted bundle placement.
for diameter in [6.,5.,4.,3.]:
    picked=[]
    for sy,ey,sz,ez,up,down in itertools.product([-43.,-41.,-39.],[-32.,-30.,-28.],
                                               [140.,143.],[172.,174.],[10.,16.,22.,28.],[8.,14.,20.,26.]):
        tried+=1;a=np.array([0.,sy,sz]);b=np.array([0.,ey,ez])
        # Both ends approach in a plane containing the yaw axis. End tangent
        # may lean inwards; no actual connector axis is being asserted.
        tangent=np.array([0.,.6,.8])
        c=np.array([a,a+[0,0,up],b-tangent*down,b])
        if radius_at_samples(c)<R:reasons['bend_radius']+=1;continue
        rr,roots=extrema_radius(c)
        if rr<R:reasons['bend_radius_extrema']+=1;continue
        pts=bezier(c,grid_t)
        if np.min(np.diff(pts[:,2]))<-.001:reasons['not_monotone_up']+=1;continue
        why=screen(pts,diameter/2)
        if why:reasons[why]+=1;continue
        picked.append(dict(probe_diameter_mm=diameter,curve_mm=pts.tolist(),cubic_controls_mm=c.tolist(),
            minimum_curvature_radius_mm=rr,required_screen_radius_mm=R,
            geometric_length_mm=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()),
            maximum_chord_mm=float(np.max(np.linalg.norm(np.diff(pts,axis=0),axis=1))),
            staging_start_mm=a.tolist(),staging_end_mm=b.tolist()))
    if picked:
        best=min(picked,key=lambda x:x['geometric_length_mm']);valid.append(best)
    print('OUTER_PROBE_POOL',diameter,len(picked),'seconds',time.time()-start,flush=True)

# Validate each selected planning probe as a closed conservative capsule sweep.
checks=[]
for i,row in enumerate(valid):
    pts=np.array(row['curve_mm']);radius=row['probe_diameter_mm']/2+gap+.02
    pieces=[]
    for a,b in zip(pts,pts[1:]):
        dd=b-a;ln=np.linalg.norm(dd)
        pieces.append(axial(radius,ln,(a+b)/2,dd/ln,segments=64))
    pieces += [manifold.Manifold.sphere(radius,32).translate(p.tolist()) for p in pts[1:-1]]
    m=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add);hits=[]
    bb=np.asarray(m.bounding_box());
    for name,s in ss.items():
        if np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
        v=max(0.,(m^s.m).volume())
        if v>.001:hits.append(dict(object=name,volume_mm3=v))
    motion=[]
    for yaw in range(-60,61,10):
        for pitch in range(-20,26,5):
            for name,s in ss.items():
                if s.group not in ['yaw','pitch']:continue
                other=s.m.transform(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))[:3,:]);ob=np.asarray(other.bounding_box())
                if np.any(bb[:3]>ob[3:]) or np.any(bb[3:]<ob[:3]):continue
                v=max(0.,(m^other).volume())
                if v>.001:motion.append(dict(object=name,yaw_deg=yaw,pitch_deg=pitch,volume_mm3=v))
    checks.append(dict(diameter_mm=row['probe_diameter_mm'],static_status='FAIL' if hits else 'PASS',
        motion_status='FAIL' if motion else 'PASS',static_hits=hits,motion_hits=motion,head_poses=130,
        meaning='Fixed-in-body probe only. No moving cable, connector, anchor or actual bundle attached.'))
    print('OUTER_PROBE_SOLID',row['probe_diameter_mm'],len(hits),len(motion),flush=True)
out=dict(revision=P['revision'],source_blend_sha256=before,status='PASS' if valid and all(x['static_status']=='PASS' for x in checks) else 'BLOCKED',
    scope='Finite lower-neck staging-to-staging round planning probes only',
    curve_radius_basis=dict(source=str(wire_path.relative_to(PROJECT)),sha256=hashlib.sha256(wire_path.read_bytes()).hexdigest(),
        field='P_J18 static wire sample bend requirement',radius_mm=R,not_dynamic_qualification=True),
    planning_diameters_mm=[6,5,4,3],diameters_are_selected_bundles=False,project_gap_per_side_mm=gap,
    search_cases=tried,reject_reasons=dict(reasons),selected=valid,solid_checks=checks,elapsed_s=time.time()-start,
    main_geometry_changed=False,actual_harness_route='NOT_TESTED',anchors='NOT_TESTED',service_loops='NOT_TESTED',
    limits=['Finite family only; absence of a passing candidate does not prove no route exists.',
        'The source wire sample does not set actual bundle diameter or dynamic bend life.',
        'A fixed body probe tests lower-throat occupancy, not the motion of an attached head harness.',
        'Staging endpoints are unanchored study coordinates. Connector approaches and outer-shell coverage not qualified.',
        'No current fourteen-wire candidate overlap screen below140mm; that remaining connection is outside this passage-only scope.'])
(HERE/'outer_neck_probes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('OUTER_NECK_PROBES',out['status'],'candidates',len(valid),'seconds',out['elapsed_s'],flush=True)
