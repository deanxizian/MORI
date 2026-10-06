"""Read-only current-source checks of the two passing yaw-loop allocations.

These are unselected circular envelopes with unanchored staging endpoints.
Source meshes, the prior fourteen-wire candidate and 130 poses are screened.
No main objects, holes, cable selections or physical qualifications are made.
"""
from pathlib import Path
BASE=Path(__file__).resolve().with_name('check_outer_neck_probes.py')
exec(compile(BASE.read_text().split('# Endpoints are named')[0],str(BASE),'exec'),globals())
from mathutils.bvhtree import BVHTree
seed_path=HERE/'split_planar_loops_refined.json'
seed=json.loads(seed_path.read_text())
assert seed['source_blend_sha256']==before
trees={n:s.bvh() for n,s in ss.items()}
fixed_path=HERE.parent/'harness_A2/assembly_safe_review/fourteen_wire_solids.json'
fixed_json=json.loads(fixed_path.read_text());fixed={}
for name,row in fixed_json.items():
    vv=np.asarray(row['vertices_mm']);lo=vv.min(axis=0);hi=vv.max(axis=0)
    fixed[name]=dict(lo=lo,hi=hi,vertices=vv,triangles=row['triangles'],tree=None)
del fixed_json

def sample_clear(points,radius,error,names):
    chord=float(np.linalg.norm(np.diff(points,axis=0),axis=1).max())
    clear=radius+.3+chord/2+error+1e-4
    for name in names:
        s=ss[name]
        mask=np.all(points>=s.lo-clear,axis=1)&np.all(points<=s.hi+clear,axis=1)
        for pt in points[mask]:
            dd=trees[name].find_nearest(Vector(pt))[3]
            if dd<clear:return dict(object=name,distance_mm=dd,required_with_sample_coverage_mm=clear,
                                   point_in_zero_object_frame_mm=pt.tolist(),meaning='clearance bound not met')
        # A connected curve with no boundary crossing and a point outside the
        # box is outside. Only wholly enclosed boxes need an inside probe.
        if np.all(points>=s.lo) and np.all(points<=s.hi):
            tiny=manifold.Manifold.sphere(.01,16).translate(points[0].tolist())
            if (tiny^s.m).volume()>tiny.volume()*.5:return dict(object=name,inside=True)
    return None

def fixed_clear(points,radius,error):
    clear=radius+.3+np.linalg.norm(np.diff(points,axis=0),axis=1).max()/2+error+1e-4
    for name,row in fixed.items():
        mask=np.all(points>=row['lo']-clear,axis=1)&np.all(points<=row['hi']+clear,axis=1)
        if not mask.any():continue
        if row['tree'] is None:row['tree']=BVHTree.FromPolygons(row['vertices'],row['triangles'],all_triangles=True)
        for pt in points[mask]:
            dd=row['tree'].find_nearest(Vector(pt))[3]
            if dd<clear:return dict(object=name,distance_mm=dd,required_with_sample_coverage_mm=float(clear))
        # This branch is unlikely for thin fixed wires but must not be silently
        # assumed exterior if a future candidate lies wholly inside the box.
        if np.all(points>=row['lo']) and np.all(points<=row['hi']):
            m=manifold.Manifold(manifold.Mesh64(vert_properties=row['vertices'],tri_verts=np.asarray(row['triangles'],dtype=np.uint64)))
            tiny=manifold.Manifold.sphere(.01,16).translate(points[0].tolist())
            if (tiny^m).volume()>tiny.volume()*.5:return dict(object=name,inside=True)
    return None

groups=[]
for group in seed['groups']:
    if group['status']!='PASS':continue
    radius=group['diameter_mm']/2;hits=[];fixed_hits=[]
    for pose in group['selected']['poses']:
        pts=np.asarray(pose['curve_mm']);yaw=pose['yaw_deg'];err=pose['second_derivative_chord_error_bound_mm']
        fh=fixed_clear(pts,radius,err)
        if fh:fixed_hits.append(dict(yaw_deg=yaw,**fh))
        for pitch in range(-20,26,5):
            for name,s in ss.items():
                if s.group in ['yaw','pitch']:
                    inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                    local=pts@inv[:3,:3].T+inv[:3,3]
                else:local=pts
                hit=sample_clear(local,radius,err,[name])
                if hit:hits.append(dict(yaw_deg=yaw,pitch_deg=pitch,**hit))
    result=dict(id=group['id'],status='PASS' if not hits and not fixed_hits else 'FAIL',
                source_poses=130,current_part_count=len(ss),current_source_hits=hits,
                previous_fourteen_wire_hits=fixed_hits,certified_project_surface_gap_mm=.3,
                anchor_and_connector_approaches='NOT_TESTED')
    groups.append(result)
    print('LOOP_SOURCE_GROUP',group['id'],result['status'],len(hits),len(fixed_hits),time.time()-start,flush=True)

pairs=[]
passing=[g for g in seed['groups'] if g['status']=='PASS']
for ga,gb in itertools.combinations(passing,2):
    # Parallel planes give a global point-to-point separation bound independent
    # of horizontal shape. This also holds between the 13 yaw sample poses.
    center_bound=abs(ga['plane_z_mm']-gb['plane_z_mm'])
    surface_bound=center_bound-(ga['diameter_mm']+gb['diameter_mm'])/2
    pairs.append(dict(a=ga['id'],b=gb['id'],status='PASS' if surface_bound>=.3 else 'BLOCKED',
                      method='parallel-plane global distance bound',surface_gap_lower_bound_mm=surface_bound))
out=dict(status='PASS' if groups and all(g['status']=='PASS' for g in groups) and all(p['status']=='PASS' for p in pairs) else 'FAIL',
         scope='Two finite planning loops only; UART, neck rise and installed harness are not qualified',
         source_blend_sha256=before,source_loops_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),
         source_fixed_wires_sha256=hashlib.sha256(fixed_path.read_bytes()).hexdigest(),groups=groups,inter_group=pairs,
         classification='PLACEHOLDER / ASSUMED planning allocations',actual_harness='NOT_TESTED',
         main_geometry_changed=False,individual_wire_lengths='NOT_TESTED',elapsed_s=time.time()-start,
         limits=['Clearance uses original triangles/proxies plus bounded curve-to-chord and sample spacing allowances.',
                 '13 yaw × 10 pitch poses are finite nominal source geometry checks, not continuous-motion certification.',
                 'Endpoints are study coordinates with no real retention or terminal approaches.',
                 'Constant group-centreline length does not establish all individual wire lengths or dynamic lifetime.',
                 'There is no third passing UART route in this report.'])
(HERE/'loop_source_solids.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('LOOP_SOURCE_COMPLETE',out['status'],time.time()-start,flush=True)
