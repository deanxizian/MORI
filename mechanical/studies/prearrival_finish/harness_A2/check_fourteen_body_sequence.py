# -*- coding: utf-8 -*-
"""Replay the approved rigid body/bridge path around fourteen static wires.

No flexible deformation, hand support or extra harness is inferred.
"""
from pathlib import Path
import json,hashlib,time,sys
HERE14=Path(__file__).resolve().parent
ASSEMBLY_REVIEW='--assembly-reviewed' in sys.argv
REVIEW_DIR=HERE14/'assembly_safe_review' if ASSEMBLY_REVIEW else HERE14
script=(HERE14/'validate_candidate.py').read_text().split('wire_solids={}')[0]
exec(compile(script,str(HERE14/'validate_candidate.py'),'exec'),globals())
start=time.time();verified=json.loads((REVIEW_DIR/'fourteen_validation.json').read_text())
assert verified['status']=='PASS' and verified['source_blend_sha256']==source_hash
wires={}
for n,d in json.loads((REVIEW_DIR/'fourteen_wire_solids.json').read_text()).items():
    wires[n]=manifold.Manifold(manifold.Mesh64(np.array(d['vertices_mm'],dtype=np.float64),np.array(d['triangles'],dtype=np.uint64)))
    assert wires[n].status()==manifold.Error.NoError
ENDPLUGS='--endpoint-plugs' in sys.argv
if ENDPLUGS:
    wires={'Plug_'+p:plug[p].m for p in ['power_J17','motion_J1','motion_J2','power_J13','motion_J3','power_J14','motion_J4','imu_J1']}
prior_path=PROJECT/'mechanical/reports/assembly_issue_validation.json'
current_path=PROJECT/'mechanical/reports/head_retention_body_sequence.json'
current=json.loads(current_path.read_text());assert current['status']=='PASS' and current['source_blend_sha256']==source_hash
upper=set(json.loads(prior_path.read_text())['body_service']['upper_shell']['moving'])
bridge={'Yaw_Base','Yaw_Bearing'}|{n for n in ss if n.startswith(('Yaw_Base_-1_Nut','Yaw_Base_1_Nut','Yaw_Keeper_Insert_'))}
up_solids={n:ss[n].m for n in upper}
up_solids.update({'Plug_'+p:plug[p].m for p in ['rear_J2','rear_J3']})
bridge_solids={n:ss[n].m for n in bridge}
origin=Vector((0,0,D['body_z']))
def shellpose(a,y,z):
    return Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
def wire_hits(m):
    bb=m.bounding_box();hits=[]
    for wid,w in wires.items():
        ob=w.bounding_box()
        if any(bb[i+3]<=ob[i] or ob[i+3]<=bb[i] for i in range(3)):continue
        vol=max(0,(m^w).volume())
        if vol>.001:hits.append(dict(wire=wid,intersection_mm3=vol))
    return hits
def replay(label,steps):
    hits=[]
    for k,(u,b) in enumerate(steps):
        for group,tr in [(up_solids,u),(bridge_solids,b)]:
            for name,m in group.items():
                hits.extend(dict(sample=k,moving=name,**h) for h in wire_hits(m.transform(np.array(tr)[:3,:])))
    by_pair={}
    for h in hits:
        key=(h['moving'],h['wire'])
        if key not in by_pair:by_pair[key]=dict(moving=key[0],wire=key[1],first_sample=h['sample'],last_sample=h['sample'],max_intersection_mm3=h['intersection_mm3'])
        else:
            by_pair[key]['last_sample']=h['sample'];by_pair[key]['max_intersection_mm3']=max(by_pair[key]['max_intersection_mm3'],h['intersection_mm3'])
    row=dict(id=label,status='PASS' if not hits else 'FAIL',samples=len(steps),hit_count=len(hits),pairs=list(by_pair.values()),first_hits=hits[:12])
    print('WIRE_BODY_PATH',label,row['status'],row['samples'],row['pairs'][:3],flush=True)
    return row
paths=[]
paths.append(replay('bridge_withdraw18_shell_held15deg14up',[(shellpose(15,0,14),Matrix.Translation((0,0,z))) for z in np.arange(0,18.01,.5)]))
steps=[(shellpose(15,y,14),Matrix.Translation((0,y,18))) for y in np.linspace(0,-14,57)]
steps += [(shellpose(15,-14,z),Matrix.Translation((0,-14,z+4))) for z in np.arange(14.5,140.01,.5)]
paths.append(replay('shell_and_level_bridge_back14_up140',steps))
paths.append(replay('shell_settle_bridge_fixed',[(shellpose(15*u,0,14*u),Matrix.Identity(4)) for u in np.linspace(0,1,61)]))
ft=json.loads((PROJECT/'mechanical/studies/prearrival_closure/assembly_preflight.json').read_text());tools=[]
for r in ft['fasteners']:
    if not r['id'].startswith('Yaw_Base'):continue
    p=np.array(r['head_top_mm']);a=np.array(r['axis']);rad=1.16
    shapes=[axial(rad,70,p+a*35.04,a)];u=np.cross(a,np.array([0.,0,1.]));u/=np.linalg.norm(u);v=np.cross(a,u)
    for angle in range(0,360,5):
        t=math.radians(angle);b=u*math.cos(t)+v*math.sin(t)
        shapes.append(axial(rad,20,p+a*(70-rad)+b*10,b))
    hits=[]
    for k,m in enumerate(shapes):hits.extend(dict(piece=k,**h) for h in wire_hits(m))
    screw_hits=[]
    for d in np.arange(0,25.01,.5):
        screw_hits.extend(dict(travel_mm=float(d),**h) for h in wire_hits(ss[r['id']].m.translate((a*d).tolist())))
    tools.append(dict(id=r['id'],status='PASS' if not hits and not screw_hits else 'FAIL',tool_hits=hits,screw_hits=screw_hits))
    print('WIRE_BRIDGE_TOOL',r['id'],tools[-1]['status'],flush=True)
out=dict(revision=P['revision'],source_blend_sha256=source_hash,status='PASS' if all(r['status']=='PASS' for r in paths+tools) else 'FAIL',
    scope='Eight fixed H01-H04 endpoint mating housing envelopes only' if ENDPLUGS else 'Only additional interactions of approved body/bridge sequence with fourteen assumed static H01-H04 wires',
    source_paths_sha256=hashlib.sha256(current_path.read_bytes()).hexdigest(),
    source_wire_check_sha256=hashlib.sha256((REVIEW_DIR/'fourteen_validation.json').read_bytes()).hexdigest(),
    paths=paths,tools=tools,position_samples=sum(r['samples'] for r in paths),main_geometry_changed=False,
    endpoint_plugs_only=ENDPLUGS,fixed_objects=sorted(wires),
    source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,elapsed_s=time.time()-start,
    limits=['Wire shapes held fixed with their fixed-board endpoints; no transient flex/handling claim.',
        'Rear mating housing envelopes move with upper shell, but rear wires, speaker leads, head harness and other omitted branches remain untested.',
        'Only intersections at407 specified body positions and finite tool orientations checked; no intersample motion or tolerance proof.',
        'Static route geometry remains a candidate; no assembly release, cut lengths or strain-relief acceptance.'])
(REVIEW_DIR/('endpoint_plug_body_sequence.json' if ENDPLUGS else 'fourteen_body_sequence.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('FOURTEEN_BODY_SEQUENCE',out['status'],out['position_samples'],out['elapsed_s'],flush=True)
