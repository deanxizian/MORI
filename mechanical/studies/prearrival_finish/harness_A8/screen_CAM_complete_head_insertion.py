"""Screen the complete head against the old bridge-only assembly order.

Independent, reversible kinematic study on current M1.47 source solids.  The
three existing, unadopted CAM routing prints are substituted in memory only.
This first pass deliberately checks rigid membership before flexible supply.
"""
import sys, json, hashlib, time, math
from pathlib import Path
SCRIPT = Path(__file__).resolve(); A8 = SCRIPT.parent; PROJECT = A8.parents[3]
sys.path.insert(0, str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid

OUT = A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head'
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
main = PROJECT/'mechanical/mori_v1_2.blend'; source_hash = sha(main)
protected = {str(p.relative_to(PROJECT)): sha(p) for p in [main,
    PROJECT/'config/geometry.json', PROJECT/'contracts/mechanical_interfaces.json', PROJECT/'contracts/components.json']}
load_collections(); assembled(); bpy.context.view_layer.update()
source_objects = {o.name.removeprefix(PREFIX): o for o in parts() if o.type == 'MESH' and o.get('group') not in ['dock','coupon']}
assert len(source_objects) == 209
ss = {n: Solid(o) for n,o in source_objects.items()}
solids = {n:s.m for n,s in ss.items()}
replacements = {
    'Yaw_Base': A8/'cam_anchors/candidate_v3/cleaned/Yaw_Base.npz',
    'Pitch_Yoke': A8/'cam_anchors/candidate_v3/cleaned/Pitch_Yoke.npz',
    'Pitch_Cradle': A8/'cam_pitch_anchor/connector_anchor/Pitch_Cradle.npz',
}
for n,p in replacements.items():
    a=np.load(p); m=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles']))
    assert m.status()==manifold.Error.NoError and m.volume()>0
    solids[n]=m
prior_path=PROJECT/'mechanical/reports/assembly_issue_validation.json'
upper=set(json.loads(prior_path.read_text())['body_service']['upper_shell']['moving'])
moving={n for n,s in ss.items() if s.group in ['yaw','pitch']}
moving|={n for n in ss if n.startswith(('Yaw_',)) and n not in ['Yaw_Base_-1_Screw','Yaw_Base_1_Screw']}
deferred={'Body_Lower','Yaw_Base_-1_Screw','Yaw_Base_1_Screw'}
deferred|={n for n in ss if n.startswith(('Shell_Screw_','Frame_Screw_','Wheel_Hub_','Tire_','Wheel_End_','Wheel_Spacer_L_1','Wheel_Spacer_R_1'))}
fixture=set(ss)-upper-moving-deferred
assert not (upper&moving or upper&deferred or fixture&moving)
assert upper|moving|fixture|deferred==set(ss)
shell_late={'Head_Front','Head_Rear'}|{n for n in ss if n.startswith(('Head_Cradle_Screw_','Head_Seam_Screw_','Head_Seam_Insert_'))}
# Cradle fixing inserts belong to the cradle and remain in the prewired core.
assert shell_late<=moving
origin=Vector((0,0,D['body_z']))
I=np.eye(4)
def trans(y=0.,z=0.):
    m=np.eye(4);m[:3,3]=[0.,y,z];return m
def shellpose(a,y,z):
    return np.asarray(Matrix.Translation((0,y,z))@Matrix.Translation(origin)@
        Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin))
def pairs(A,B,limit=6):
    hits=[]
    for n,a in A.items():
        ba=np.asarray(a.bounding_box())
        for k,b in B.items():
            bb=np.asarray(b.bounding_box())
            if np.any(ba[3:]<bb[:3]-1e-6) or np.any(bb[3:]<ba[:3]-1e-6):continue
            v=max(0.,float((a^b).volume()))
            if v>1e-5:
                hits.append(dict(moving=n,obstacle=k,intersection_mm3=v))
                if len(hits)>=limit:return hits
    return hits
def placed(ids,T):return {n:solids[n].transform(T[:3,:4]) for n in sorted(ids)}

headsets={'complete_head_with_shells':moving,'prewired_core_shells_later':moving-shell_late}
stages=[
 ('bridge_seat_shell_held',[(shellpose(15,0,14),trans(z=float(z))) for z in np.linspace(0,18,37)]),
 ('rear_translation',[(shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in np.linspace(0,-14,29)]),
 ('lift_to_bench',[(shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in np.linspace(14,140,64)]),
 ('shell_settle',[(shellpose(15*float(u),0,14*float(u)),I) for u in np.linspace(0,1,61)]),
]
rows=[];started=time.time();fixed=placed(fixture,I)
for label,ids in headsets.items():
    for stage,poses in stages:
        failures=[];checked=0
        for index,(st,ht) in enumerate(poses):
            head=placed(ids,ht);body=placed(upper,st)
            hits=pairs(head,fixed)+pairs(body,fixed)+pairs(body,head)
            checked+=1
            if hits:
                failures=[dict(index=index,shell_transform=st.tolist(),head_transform=ht.tolist(),hits=hits)];break
        row=dict(candidate=label,stage=stage,status='BLOCKED' if failures else 'PASS',checked_positions=checked,
            planned_positions=len(poses),failures=failures)
        rows.append(row);print('COMPLETE_HEAD_RIGID',label,stage,row['status'],checked,failures[:1],flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite rigid-member screen of old bridge-only sequence; not a complete wired assembly proof',
    script_sha256=sha(SCRIPT),source_main_sha256=source_hash,source_objects=len(ss),
    protected_sources=protected,source_upper_membership_sha256=sha(prior_path),
    substituted_unadopted_prints={n:dict(path=str(p.relative_to(PROJECT)),sha256=sha(p)) for n,p in replacements.items()},
    membership=dict(upper_body=sorted(upper),fixture=sorted(fixture),deferred=sorted(deferred),
        complete_head=sorted(moving),shells_later=sorted(shell_late)),rows=rows,
    rigid_intersection_threshold_mm3=1e-5,continuous_motion='NOT_TESTED',full_length_wires='NOT_TESTED',
    plug_and_tie_installation='NOT_TESTED',transmission_interfaces='BLOCKED_PENDING_VENDOR',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'rigid_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('COMPLETE_HEAD_RIGID_DONE',report['status'],round(time.time()-started,2),flush=True)
