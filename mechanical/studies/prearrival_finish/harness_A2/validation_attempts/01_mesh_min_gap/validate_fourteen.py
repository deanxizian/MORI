# -*- coding: utf-8 -*-
"""Full static14-wire envelope check on untouched M1.47 assembly."""
from pathlib import Path
import json,hashlib,time,itertools
FOURTEEN_DIR=Path(__file__).resolve().parent
helper=(FOURTEEN_DIR/'validate_candidate.py').read_text().split('wire_solids={}')[0]
exec(compile(helper,str(FOURTEEN_DIR/'validate_candidate.py'),'exec'),globals())
imu_source=FOURTEEN_DIR/'imu_wide_joint.json';imu=json.loads(imu_source.read_text())
assert imu['status']=='PASS' and imu['source_blend_sha256']==source_hash
assert imu['source_six_wire_sha256']==hashlib.sha256(source_path.read_bytes()).hexdigest()
sources={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source_path,imu_source,FOURTEEN_DIR/'imu_wide_pools.json',FOURTEEN_DIR/'ecowire_sources.json']}
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
        max_chord=float(np.max(np.linalg.norm(np.diff(pts[1:-1],axis=0),axis=1)))
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
    name=row['id'];m=wire_solids[name];hs=pair_hits(m,rigid);near=[];bb=m.bounding_box()
    for n,other in rigid.items():
        # Full solid overlap remains checked even for endpoint housings.
        # Only the deliberate exit-face zero gap is excluded from margin.
        if n in ['Plug_'+row['from_port'],'Plug_'+row['to_port']]:continue
        ob=other.bounding_box()
        if any(bb[i+3]+.31<ob[i] or ob[i+3]+.31<bb[i] for i in range(3)):continue
        gap=m.min_gap(other,.31)
        if gap<.3:near.append(dict(object=n,surface_gap_mm=gap))
    rigid_rows.append(dict(id=name,status='PASS' if not hs and not near else 'FAIL',overlaps=hs,under_0p3_gap=near))
mutual=[]
for a,b in itertools.combinations(wire_solids,2):
    v=max(0,(wire_solids[a]^wire_solids[b]).volume());gap=wire_solids[a].min_gap(wire_solids[b],5.)
    mutual.append(dict(a=a,b=b,intersection_mm3=v,nominal_tessellated_solid_gap_mm=gap,status='PASS' if v<.001 and gap>=.3 else 'FAIL'))
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
        '130head poses, not a continuous motion proof.',
        'No H05, moving-head harness, FFC, branch wiring, anchors, service slack or cable-attached disassembly qualification.'])
(FOURTEEN_DIR/'fourteen_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(FOURTEEN_DIR/'fourteen_wire_solids.json').write_text(json.dumps(outlines)+'\n')
print('FOURTEEN_VALIDATION',out['status'],'rigid failures',sum(r['status']=='FAIL' for r in rigid_rows),'mutual',sum(r['status']=='FAIL' for r in mutual),'motion',len(motion),'seconds',out['elapsed_s'],flush=True)
