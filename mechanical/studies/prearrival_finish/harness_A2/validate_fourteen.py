# -*- coding: utf-8 -*-
"""Full static14-wire envelope check on untouched M1.47 assembly."""
from pathlib import Path
import json,hashlib,time,itertools,sys
FOURTEEN_DIR=Path(__file__).resolve().parent
SLOT_PATH='--deck-slot' in sys.argv
ASSEMBLY_REVIEW='--assembly-reviewed' in sys.argv
OUTPUT_DIR=FOURTEEN_DIR/'assembly_safe_review' if ASSEMBLY_REVIEW else FOURTEEN_DIR/'deck_slot_review' if SLOT_PATH else FOURTEEN_DIR
OUTPUT_DIR.mkdir(exist_ok=True)
helper=(FOURTEEN_DIR/'validate_candidate.py').read_text().split('wire_solids={}')[0]
exec(compile(helper,str(FOURTEEN_DIR/'validate_candidate.py'),'exec'),globals())
if SLOT_PATH:
    sys.path.insert(0,str(FOURTEEN_DIR))
    from deck_slot_candidate import apply_to_study
    slot_candidate=apply_to_study(globals())
imu_source=FOURTEEN_DIR/('imu_refined_assembly_joint.json' if ASSEMBLY_REVIEW else 'imu_slot_assembly_joint.json' if SLOT_PATH else 'imu_wide_joint.json')
if '--joint' in sys.argv:
    assert ASSEMBLY_REVIEW, 'Custom joint studies must use a separate review directory'
    imu_source=FOURTEEN_DIR/sys.argv[sys.argv.index('--joint')+1]
    assert imu_source.parent==FOURTEEN_DIR
imu=json.loads(imu_source.read_text())
assert imu['status']=='PASS' and imu['source_blend_sha256']==source_hash
assert imu['source_six_wire_sha256']==hashlib.sha256(source_path.read_bytes()).hexdigest()
pool_source=FOURTEEN_DIR/imu.get('source_pool_file','imu_refined_assembly_pools.json' if ASSEMBLY_REVIEW else 'imu_slot_pools.json' if SLOT_PATH else 'imu_wide_pools.json')
assert pool_source.parent==FOURTEEN_DIR and hashlib.sha256(pool_source.read_bytes()).hexdigest()==imu['source_sha256']
sources={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source_path,imu_source,pool_source,FOURTEEN_DIR/'ecowire_sources.json']}
report['routes']+=imu['routes'];wire_solids={};outlines={};envelope_rows=[];start=time.time()
unit_sphere=manifold.Manifold.sphere(1.,32).to_mesh64()
sv=unit_sphere.vert_properties[:,:3];sf=unit_sphere.tri_verts
sn=np.cross(sv[sf[:,1]]-sv[sf[:,0]],sv[sf[:,2]]-sv[sf[:,0]])
sphere_inradius=float(np.min(np.abs(np.sum(sn*sv[sf[:,0]],axis=1))/np.linalg.norm(sn,axis=1)))
for row in report['routes']:
    pts=np.asarray(row['curve_mm']);extra=.02;radius=row['wire_OD_max_mm']/2+extra
    # No resampling of the cubics: retain every checked polyline vertex.
    # End terminal legs are exactly straight and excluded from bend sag.
    R=row.get('minimum_curvature_radius_mm',row.get('analytic_bend_radius_mm'))
    if 'cubic_controls_mm' in row:
        # The slot candidate has an exact straight segment between cubics.
        # Bound curved chord sag from each source cubic independently.
        tv=np.linspace(0,1,181)[:,None];uv=1-tv;lengths=[]
        for cp in row['cubic_controls_mm']:
            cc=np.asarray(cp)
            pp=uv**3*cc[0]+3*uv*uv*tv*cc[1]+3*uv*tv*tv*cc[2]+tv**3*cc[3]
            lengths.extend(np.linalg.norm(np.diff(pp,axis=0),axis=1))
        max_chord=float(max(lengths))
    else:
        # H01-H03 contain long exact straight legs. Derive curved chords
        # from the documented circular-arc generator and its controls.
        cp=np.array(row['controls_mm']);chords=[]
        for a,b,c in zip(cp,cp[1:],cp[2:]):
            u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b)
            theta=math.acos(np.clip(u@v,-1,1))
            if theta<1e-5:continue
            steps=max(3,int(R*theta/.5)+1)-1
            chords.append(2*R*math.sin(theta/(2*steps)))
        max_chord=max(chords)
    sag_bound=max_chord**2/(8*R)*1.01
    sphere_faceting=radius*(1-sphere_inradius)
    assert sag_bound+sphere_faceting<extra, (row['id'],max_chord,sag_bound)
    pieces=[]
    for a,b in zip(pts,pts[1:]):
        delta=b-a;ln=np.linalg.norm(delta)
        if ln>.001:pieces.append(axial(radius,float(ln),(a+b)/2,delta/ln))
    for p in pts[1:-1]:pieces.append(manifold.Manifold.sphere(radius,32).translate(p))
    m=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
    assert m.status()==manifold.Error.NoError
    wire_solids[row['id']]=m;mesh=m.to_mesh64()
    outlines[row['id']]=dict(vertices_mm=mesh.vert_properties[:,:3].tolist(),triangles=mesh.tri_verts.tolist())
    envelope_rows.append(dict(id=row['id'],radial_inflation_mm=extra,max_bend_chord_mm=max_chord,
        sag_bound_mm=sag_bound,sphere_faceting_bound_mm=sphere_faceting,
        positive_connected_components=sum(v.volume()>.00001 for v in m.decompose())))
    print('FOURTEEN_SOLID',row['id'],len(mesh.tri_verts),flush=True)
# Preserve completed sweep work even if a later check fails or is interrupted.
(OUTPUT_DIR/'fourteen_wire_solids.json').write_text(json.dumps(outlines)+'\n')
segment_code=(FOURTEEN_DIR/'select_joint.py').read_text()
segment_code=segment_code[segment_code.index('def exact_segment_min'):segment_code.index('selected=search')]
segment_code=segment_code.replace('valid=det>1e-12','valid=det>np.maximum(aa*cc*1e-14,1e-24)')
exec(segment_code,globals())

def samples_with_bound(points,step=.04):
    pts=np.asarray(points);ds=np.linalg.norm(np.diff(pts,axis=0),axis=1)
    cumulative=np.r_[0.,ds.cumsum()]
    positions=np.linspace(0,cumulative[-1],int(math.ceil(cumulative[-1]/step))+1)
    samples=np.array([np.interp(positions,cumulative,pts[:,i]) for i in range(3)]).T
    # Distance to a closed surface is 1-Lipschitz. Every polyline point is
    # within half this arc-length interval of a sample, including corners.
    bound=float(np.max(np.diff(positions))/2)
    return samples,positions,bound

def pair_hits(m,other_shapes):
    bb=m.bounding_box();rows=[]
    for n,other in other_shapes.items():
        ob=other.bounding_box()
        if any(bb[i+3]<=ob[i]+1e-6 or ob[i+3]<=bb[i]+1e-6 for i in range(3)):continue
        v=max(0,(m^other).volume())
        if v>.001:rows.append(dict(object=n,intersection_mm3=v))
    return rows
rigid={n:s.m for n,s in obstacles.items()};rigid_rows=[]
for row in report['routes']:
    name=row['id'];m=wire_solids[name];hs=pair_hits(m,rigid);near=[];bb=m.bounding_box();gap_checks=[]
    pts,arc,coverage=samples_with_bound(row['curve_mm']);radius=row['wire_OD_max_mm']/2+.02
    for n,other in rigid.items():
        ob=other.bounding_box()
        if any(bb[i+3]+.32<ob[i] or ob[i+3]+.32<bb[i] for i in range(3)):continue
        use=np.ones(len(pts),dtype=bool)
        # Do not omit entire endpoint housings: only their deliberate contact
        # with the declared 5mm straight terminal exit leg is margin-exempt.
        if n=='Plug_'+row['from_port']:use &= arc>row['terminal_straight_mm']
        if n=='Plug_'+row['to_port']:use &= arc<arc[-1]-row['terminal_straight_mm']
        minimum=float('inf');at=None
        for p in pts[use]:
            _,_,_,dist=trees[n].find_nearest(Vector(p))
            if dist<minimum:minimum=float(dist);at=p.tolist()
        lower=minimum-coverage-radius-.0001
        check=dict(object=n,conservative_capsule_gap_lower_bound_mm=lower,nearest_sample_mm=at,
                   coverage_bound_mm=coverage,numeric_allowance_mm=.0001)
        gap_checks.append(check)
        if lower<.3:near.append(check)
    rigid_rows.append(dict(id=name,status='PASS' if not hs and not near else 'FAIL',overlaps=hs,
                           under_0p3_gap=near,gap_checks=gap_checks))
    print('FOURTEEN_RIGID',name,rigid_rows[-1]['status'],len(gap_checks),flush=True)
mutual=[]
for ar,br in itertools.combinations(report['routes'],2):
    a,b=ar['id'],br['id']
    v=max(0,(wire_solids[a]^wire_solids[b]).volume())
    distance,indices=exact_segment_min(ar['curve_mm'],br['curve_mm'])
    nominal=distance-(ar['wire_OD_max_mm']+br['wire_OD_max_mm'])/2
    gap=nominal-.04-.0001
    mutual.append(dict(a=a,b=b,intersection_mm3=v,minimum_polyline_center_distance_mm=distance,
        nominal_polyline_wire_gap_mm=nominal,conservative_inflated_capsule_gap_lower_bound_mm=gap,
        segment_indices=indices,status='PASS' if v<.001 and gap>=.3 else 'FAIL'))
print('FOURTEEN_PAIRS',len(mutual),sum(r['status']=='FAIL' for r in mutual),flush=True)
moving={n:s for n,s in ss.items() if s.group in ['yaw','pitch']};motion=[]
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        for n,s in moving.items():
            m=s.m.transform(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))[:3,:]);mb=m.bounding_box()
            for wid,w in wire_solids.items():
                wb=w.bounding_box()
                if any(wb[i+3]<=mb[i] or mb[i+3]<=wb[i] for i in range(3)):continue
                v=max(0,(w^m).volume())
                if v>.001:motion.append(dict(wire=wid,object=n,yaw_deg=yaw,pitch_deg=pitch,intersection_mm3=v))
    print('FOURTEEN_YAW',yaw,flush=True)
out=dict(revision=P['revision'],source_blend_sha256=source_hash,sources=sources,
    status='PASS' if all(r['status']=='PASS' for r in rigid_rows+mutual) and not motion and all(r['positive_connected_components']==1 for r in envelope_rows) else 'FAIL',
    scope='Fourteen static H01-H04 candidates only; terminal exits still assumed, wire selection not adopted',
    envelopes=envelope_rows,rigid_solids=rigid_rows,wire_to_wire=mutual,head_motion=dict(poses=130,overlaps=motion),
    source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,main_geometry_changed=False,
    cut_lengths_released=False,elapsed_s=time.time()-start,
    limits=['H01-H03 use6712/6711; eight IMU wires use6711, all unselected static wire candidates.',
        'Native numbering and pitch retained; transverse terminal exit locations and actual mating geometry unqualified.',
        'Finite tessellated capsules use0.02mm radial inflation; this is nominal geometry, not strength or contact certification.',
        'Rigid gap lower bounds subtract half the <=0.04mm sample interval, inflated radius and0.0001mm numerical allowance from nearest-surface distances; whole-solid intersections are checked independently.',
        'All91 wire-pair gaps use segment-to-segment polyline minima minus both inflated radii and0.0001mm numerical allowance; no mesh MinGap performance shortcut or endpoint-only clearance claim.',
        '130head poses, not a continuous motion proof.',
        'No H05, moving-head harness, FFC, branch wiring, anchors, service slack or cable-attached disassembly qualification.'])
if SLOT_PATH:
    out['candidate']=slot_candidate
    out['scope']+='; independent unadopted deck slot'
(OUTPUT_DIR/'fourteen_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(OUTPUT_DIR/'fourteen_wire_solids.json').write_text(json.dumps(outlines)+'\n')
print('FOURTEEN_VALIDATION',out['status'],'rigid failures',sum(r['status']=='FAIL' for r in rigid_rows),'mutual',sum(r['status']=='FAIL' for r in mutual),'motion',len(motion),'seconds',out['elapsed_s'],flush=True)
