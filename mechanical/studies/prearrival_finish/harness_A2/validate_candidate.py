# -*- coding: utf-8 -*-
"""Closed wire-envelope and head-pose audit of the six selected body leads."""
from pathlib import Path
import json,hashlib,itertools,time
STUDY=Path(__file__).resolve().parent
SCRIPT=Path(__file__).resolve()
__file__=str(STUDY.parent/'body_routes_current.py')
bootstrap=Path(__file__).read_text().split('prior=json.loads')[0]
exec(compile(bootstrap,__file__,'exec'),globals())
__file__=str(SCRIPT)
from validate import rigidtr
from interface_completion import axial
source_path=STUDY/'ecowire_joint.json';report=json.loads(source_path.read_text())
assert report['source_blend_sha256']==source_hash and report['status']=='PASS'
wire_solids={};outlines={}
for row in report['routes']:
    pts=np.array(row['curve_mm']);radius=row['wire_OD_max_mm']/2+.01
    pieces=[]
    for a,b in zip(pts,pts[1:]):
        delta=b-a;ln=np.linalg.norm(delta)
        if ln>.001:pieces.append(axial(radius,float(ln),(a+b)/2,delta/ln))
    for p in pts[1:-1]:pieces.append(manifold.Manifold.sphere(radius,32).translate(p))
    m=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
    assert m.status()==manifold.Error.NoError
    wire_solids[row['id']]=m
    d=m.to_mesh64();outlines[row['id']]=dict(vertices_mm=d.vert_properties[:,:3].tolist(),triangles=d.tri_verts.tolist())
def pair_hits(m,obstacles):
    bb=m.bounding_box();rows=[]
    for n,other in obstacles.items():
        ob=other.bounding_box()
        if any(bb[i+3]<=ob[i]+1e-6 or ob[i+3]<=bb[i]+1e-6 for i in range(3)):continue
        v=max(0,(m^other).volume())
        if v>.001:rows.append(dict(object=n,intersection_mm3=v))
    return rows
rigid={n:s.m for n,s in obstacles.items()}
rows=[]
for row in report['routes']:
    name=row['id'];m=wire_solids[name];hs=pair_hits(m,rigid)
    rows.append(dict(id=name,status='FAIL' if hs else 'PASS',overlaps=hs,
        positive_connected_components=sum(x.volume()>.00001 for x in m.decompose()),
        swept_radius_mm=row['wire_OD_max_mm']/2+.01))
mutual=[]
for a,b in itertools.combinations(wire_solids,2):
    v=max(0,(wire_solids[a]^wire_solids[b]).volume())
    gap=wire_solids[a].min_gap(wire_solids[b],5.)
    mutual.append(dict(a=a,b=b,intersection_mm3=v,nominal_tessellated_solid_gap_mm=gap,
        status='PASS' if v<.001 and gap>=.3 else 'FAIL'))
moving={n:s for n,s in ss.items() if s.group in ['yaw','pitch']};motion=[];start=time.time()
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        for n,s in moving.items():
            m=s.m.transform(np.array(rigidtr(yaw,pitch if s.group=='pitch' else 0))[:3,:])
            mb=m.bounding_box()
            for wid,w in wire_solids.items():
                wb=w.bounding_box()
                if any(wb[i+3]<=mb[i] or mb[i+3]<=wb[i] for i in range(3)):continue
                v=max(0,(w^m).volume())
                if v>.001:motion.append(dict(wire=wid,object=n,yaw_deg=yaw,pitch_deg=pitch,intersection_mm3=v))
    print('WIRE_HEAD_YAW',yaw,flush=True)

out=dict(revision=P['revision'],source_blend_sha256=source_hash,source_joint_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    status='PASS' if all(r['status']=='PASS' for r in rows+mutual) and not motion else 'FAIL',
    scope='Only six static H01-H03 wire envelopes, with provisional terminal exits; not installed harness release',
    rigid_solids=rows,wire_to_wire=mutual,head_motion=dict(poses=130,overlaps=motion),
    source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,
    geometry_change=False,cut_lengths_released=False,elapsed_s=time.time()-start,
    limits=['The six wires use unselected EcoWire6711/6712 manufacturer dimensions; pin pitch documented, exit transverse location still assumed.',
        '0.01mm radius inflation covers arc chord sag up to0.5mm tessellation; cylinders use finite circular tessellation, not a strength or microscopic contact model.',
        'Head motion is a130-pose finite check, not an intersample proof.',
        'No other harness, tie/sleeve, terminal strain relief, service-slack or board-removal qualification.',
        'Selecting a bend-radius sample and demonstrating space does not release purchasing, crimping or production.'])
(STUDY/'ecowire_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(STUDY/'ecowire_wire_solids.json').write_text(json.dumps(outlines)+'\n')
print('WIRE_VALIDATION',out['status'],'static',sum(len(x['overlaps']) for x in rows),'motion',len(motion),flush=True)
