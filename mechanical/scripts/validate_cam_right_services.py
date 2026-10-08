"""Current CAM service geometry. Plug bodies are illustrative allocations only.

Continuous translation helper retained from the independently reviewed candidate.
"""
from common import *
from validate import rigidtr
import hashlib,time
VOLUME_TOL=1e-7

def intersects_bb(a, b):
    return not (np.any(a[3:] < b[:3]) or np.any(a[:3] > b[3:]))

def sweep_hits(m, delta, targets):
    """Continuous pure-translation sweep, tested as exact surface prisms."""
    delta = np.asarray(delta, dtype=float)
    data = m.to_mesh()
    triangles = np.asarray(data.vert_properties)[:, :3][np.asarray(data.tri_verts)]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    forward = normals @ delta > 1e-12
    triangles = triangles[forward]
    lo = np.minimum(triangles.min(axis=1), triangles.min(axis=1) + delta)
    hi = np.maximum(triangles.max(axis=1), triangles.max(axis=1) + delta)
    start_bb = np.asarray(m.bounding_box())
    swept_bb = np.r_[np.minimum(start_bb[:3], start_bb[:3] + delta),
                     np.maximum(start_bb[3:], start_bb[3:] + delta)]
    result = []
    pieces_checked = 0
    for name, target in targets.items():
        bb = np.asarray(target.bounding_box())
        if not intersects_bb(swept_bb, bb):
            continue
        initial = max(0., float((m ^ target).volume())) if intersects_bb(start_bb, bb) else 0.
        if initial > VOLUME_TOL:
            result.append(dict(object=name, kind='initial_volume', intersection_mm3=initial))
            continue
        candidates = np.flatnonzero(np.all(hi >= bb[:3], axis=1) & np.all(lo <= bb[3:], axis=1))
        for i in candidates:
            pts = np.concatenate([triangles[i], triangles[i] + delta])
            prism = manifold.Manifold.hull_points(pts)
            pieces_checked += 1
            volume = max(0., float((prism ^ target).volume()))
            if volume > VOLUME_TOL:
                result.append(dict(object=name, kind='swept_surface_prism',
                                   triangle=int(i), intersection_mm3=volume))
                break
    return dict(status='PASS' if not result else 'BLOCKED', hits=result,
                forward_triangles=len(triangles), tested_prism_pairs=pieces_checked)

def hits(m,targets,exclude=(),margin=0.,tol=1e-5):
    bb=np.asarray(m.bounding_box());result=[]
    for name,target in targets.items():
        if name in exclude:continue
        b=np.asarray(target.bounding_box())
        if np.any(bb[3:]<b[:3]-margin) or np.any(bb[:3]>b[3:]+margin):continue
        volume=max(0.,float((m^target).volume()))
        gap=float(m.min_gap(target,margin)) if margin and volume<=tol else 0.
        if volume>tol or (margin and gap<margin-1e-7):
            result.append(dict(object=name,intersection_mm3=volume,gap_mm=gap))
    return result

def run(ss):
    from cam_orientation import transform
    from microphone_geometry import microphone_paths
    started=time.time();q=P['cam_orientation'];tr=transform();moving=q['changed_existing_ids']
    baseline=json.loads((PROJECT/q['baseline']).read_text())
    previous=baseline['assets']['CAM_Mainboard'];ref=next(c for c in previous['component_reference_index'] if c['reference']=='USB_C')
    old=np.load(ROOT/'input_assets/M1_53_CAM_Mainboard_visual_before_right.npz')['vertices_mm'][slice(*ref['vertices'])]
    old_mouth=(old.min(0)+old.max(0))/2;old_mouth[2]=old[:,2].min()
    mouth=tr[:3,:3]@old_mouth+tr[:3,3];axis=tr[:3,:3]@np.array([0.,0.,-1.])
    assert np.allclose(axis,[1,0,0])
    ms={n:s.m for n,s in ss.items()};tools=ROOT/'input_assets/cam_right_tools';stage=json.loads((tools/'stage.json').read_text())
    fixed_names=(set(stage['fixed_objects'])&set(ss))-set(moving)-set(stage['deferred_screws'])
    fixed={n:ms[n] for n in fixed_names};board={n:ms[n] for n in moving}
    tool_names=fixed_names|set(moving)|set(P['camera_cam_completion']['cam_screws']['ids'])
    tool_rows=[]
    for row in P['interface_completion']['inserts']:
        if row.get('screw') not in P['camera_cam_completion']['cam_screws']['ids']:continue
        for kind in ['work_sweep','entry_sweep','arrival_sweep']:
            p=tools/(row['screw']+'_'+kind+'.npz');data=np.load(p)
            m=manifold.Manifold(manifold.Mesh64(data['vertices_mm'],data['triangles'].astype(np.uint64)))
            exclude=[row['screw']]+([row['id']] if kind=='arrival_sweep' else [])
            clash=hits(m,{n:ms[n] for n in tool_names},exclude,tol=1e-4)
            tool_rows.append(dict(screw=row['screw'],kind=kind,hits=clash,status='PASS' if not clash else 'FAIL'))
    seq=q['assembly'];forward=np.array([0,seq['forward_mm'],0]);lift=np.array([0,0,seq['lift_at_plug_insertion_mm']])
    board_rows=[]
    for n,m in board.items():
        for label,start,delta in [('seat_forward',m,forward),('entry',m.translate(forward.tolist()),np.array([0,0,seq['entry_above_mm']]))]:
            board_rows.append(dict(object=n,segment=label,**sweep_hits(start,delta,fixed)))
    allocation_rows=[]
    groups={g:{n:s.m for n,s in ss.items() if (s.group if s.group in ['pitch','yaw'] else 'body')==g} for g in ['body','yaw','pitch']}
    for width,thickness,length in [(10.,5.,12.),(10.,5.,16.),(11.2,6.7,17.5)]:
        plug=manifold.Manifold.cube([width,thickness,length],True).translate((old_mouth-[0,0,.5+length/2]).tolist()).transform(tr[:3,:])
        motion=[]
        for yaw in range(-60,61,10):
            for pitch in range(-20,26,5):
                matrices={'body':np.asarray(rigidtr(yaw,pitch)),'yaw':np.asarray(rigidtr(0,pitch)),'pitch':np.eye(4)}
                for group,targets in groups.items():
                    if group=='pitch' and (yaw!=0 or pitch!=0):continue
                    motion.extend(dict(yaw=yaw,pitch=pitch,group=group,**h) for h in hits(plug.transform(matrices[group][:3,:]),targets,margin=.3))
        raised={n:m.translate((forward+lift).tolist()) for n,m in board.items()}
        travel=[dict(segment='seat_forward',**sweep_hits(plug,forward,fixed)),
                dict(segment='lowering',**sweep_hits(plug.translate(forward.tolist()),lift,fixed)),
                dict(segment='plug_insertion',**sweep_hits(plug.translate((forward+lift).tolist()),seq['plug_approach_travel_mm']*axis,fixed|raised))]
        ok=not motion and all(row['status']=='PASS' for row in travel)
        allocation_rows.append(dict(body_size_mm=[width,thickness,length],status='PASS' if ok else 'FAIL',motion_hits=motion,continuous_segments=travel))
        print('CAM_RIGHT_PLUG',width,thickness,length,allocation_rows[-1]['status'],flush=True)
    # Full native motion already checks the installed microphones. Here verify
    # both nominal open-air routes against all native solids at the same poses.
    air=[]
    for row in microphone_paths(installed=True):
        points=row['probe_points'];pieces=[];radius=P['microphone_acoustics']['airway_probe_radius_mm']
        for a,b in zip(points,points[1:]):
            a,b=Vector(a),Vector(b);rot=(b-a).to_track_quat('Z','Y').to_matrix().to_4x4()
            mat=Matrix.Translation((a+b)/2)@rot
            pieces.append(manifold.Manifold.cylinder((b-a).length,radius,radius,24,True).transform(np.asarray(mat)[:3,:]))
        for p in points[1:-1]:pieces.append(manifold.Manifold.sphere(radius,20).translate(list(p)))
        probe=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add);clashes=[]
        for yaw in range(-60,61,10):
            for pitch in range(-20,26,5):
                matrices={'body':np.asarray(rigidtr(yaw,pitch)),'yaw':np.asarray(rigidtr(0,pitch)),'pitch':np.eye(4)}
                for group,targets in groups.items():
                    if group=='pitch' and (yaw!=0 or pitch!=0):continue
                    clashes.extend(dict(yaw=yaw,pitch=pitch,**h) for h in hits(probe.transform(matrices[group][:3,:]),targets,exclude=['Onboard_MIC_'+row['side']]))
        air.append(dict(channel=row['side'],port_mm=list(row['port']),points_mm=[list(p) for p in points],hits=clashes,status='PASS' if not clashes else 'FAIL'))
    # Each CAM-side entry is transformed using its retained local/photo basis;
    # source contact face, actual insertion depth and real flex shape remain unknown.
    basis=np.array(ss['CAM_Mainboard'].o['source_rotation']);entries={}
    for name,vector in P['waveshare_detail']['entry_correction']['outward_direction_uvw'].items():
        entries[name]={'outward_world':(basis@np.array(vector)).tolist(),'evidence':'PHOTO_DIRECTION_WITH_RIGID_BOARD_TRANSFORM','mating_dimensions':'BLOCKED'}
    ok=all(r['status']=='PASS' for r in tool_rows+board_rows+allocation_rows+air)
    result=dict(revision=P['revision'],status='PASS' if ok else 'FAIL',
        source_blend_sha256=hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),
        scope='130 discrete poses, 3 illustrative USB bodies, 12 existing tool sweeps, current CAM entry path and open-air probes only.',
        method='Actual triangle-solid intersections/min_gap; piecewise continuous translation tested with forward surface prisms preserving holes. No complete plug nose/contact/cable or hand qualification.',
        combined_poses=130,USB_nominal_mouth_mm=mouth.tolist(),USB_outward_world=axis.tolist(),
        connector_entries=entries,tools=tool_rows,board_path=board_rows,USB_body_allocations=allocation_rows,
        microphone_paths=air,fixed_assembly_parts=sorted(fixed_names),deferred_parts=sorted(set(ss)-fixed_names-set(moving)),
        sequence=seq,acoustic_RF_performance='NOT_TESTED',complete_harness='BLOCKED',manufacturing_release=False,
        elapsed_s=time.time()-started)
    save_json(ROOT/'reports/cam_right_service_validation.json',result)
    return result
