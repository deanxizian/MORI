"""Two independently supported parts: level bridge inside tilted shell.

Mechanical geometry is unchanged. Fixture/hand support is NOT qualified.
"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
exec(compile((HERE/'rigid_assembly_paths.py').read_text().split('# Parts are handled')[0],str(HERE/'rigid_assembly_paths.py'),'exec'))
from interface_completion import axial
prior=json.loads((PROJECT/'mechanical/reports/assembly_issue_validation.json').read_text())['body_service']['upper_shell']
upper=set(prior['moving']);bridge={'Yaw_Base','Yaw_Bearing'}|select('Yaw_Base_-1_Nut','Yaw_Base_1_Nut')
fixture=core|drive;origin=Vector((0,0,D['body_z']))
def shellpose(a,y,z):return Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
def collisions(m,others):
    bb=np.array(m.bounding_box());bad=[]
    for n,t in others.items():
        obb=np.array(t.bounding_box())
        if np.any(bb[3:]<obb[:3]) or np.any(obb[3:]<bb[:3]):continue
        v=max(0,(m^t).volume())
        if v>.05:bad.append(dict(fixed=n,volume_mm3=v))
    return bad
def checktwo(label,steps):
    bad=[];count=0
    for trU,trB in steps:
        count+=1;uu={n:ss[n].m.transform(np.array(trU)[:3,:]) for n in upper};bb={n:ss[n].m.transform(np.array(trB)[:3,:]) for n in bridge}
        fixed={n:ss[n].m for n in fixture}
        for n,m in uu.items():bad.extend(dict(sample=count,moving=n,**h) for h in collisions(m,fixed|bb))
        for n,m in bb.items():bad.extend(dict(sample=count,moving=n,**h) for h in collisions(m,fixed))
        if len(bad)>20:break
    r=dict(id=label,status='PASS' if not bad else 'FAIL',samples=count,hits=bad)
    print(label,r['status'],bad[:2],flush=True);return r
rows=[]
# Upper shell follows established tilted/back/up route; bridge stays level
# and is held4mm higher than the shell's translation (not its rotated pose).
# The earlier24mm bridge lift collided with the shell;18mm is screened here.
steps=[(shellpose(15,0,14),Matrix.Translation((0,0,z))) for z in np.arange(0,18.01,.5)]
rows.append(checktwo('bridge_withdraw_18_shell_held_15deg_14up',steps))
steps=[(shellpose(15,y,14),Matrix.Translation((0,y,18))) for y in np.linspace(0,-14,57)]
steps += [(shellpose(15,-14,z),Matrix.Translation((0,-14,z+4))) for z in np.arange(14.5,140.01,.5)]
rows.append(checktwo('shell_and_level_bridge_back14_up140',steps))
steps=[(shellpose(15*u,0,14*u),Matrix.Identity(4)) for u in np.linspace(0,1,61)]
rows.append(checktwo('shell_settle_with_bridge_fixed',steps))
# Long straight L-key and full transverse leg through raised shell clearance.
ft=json.loads((HERE/'assembly_preflight.json').read_text());toolrows=[]
uptr=shellpose(15,0,14);fixed={n:ss[n].m for n in fixture|bridge}
fixed.update({n:ss[n].m.transform(np.array(uptr)[:3,:]) for n in upper})
for r in ft['fasteners']:
    if not r['id'].startswith('Yaw_Base'):continue
    p=np.array(r['head_top_mm']);a=np.array(r['axis']);rad=1.16
    shapes=[axial(rad,70,p+a*35.04,a)];ref=np.array([0.,0,1.]);u=np.cross(a,ref);u/=np.linalg.norm(u);v=np.cross(a,u)
    for angle in range(0,360,5):
        t=math.radians(angle);b=u*math.cos(t)+v*math.sin(t)
        shapes.append(axial(rad,20,p+a*(70-rad)+b*10,b))
    hits=[]
    for i,m in enumerate(shapes):hits.extend(dict(tool_piece=i,**h) for h in collisions(m,fixed))
    insertion=[]
    for d in np.arange(0,25.01,.5):insertion.extend(dict(travel_mm=float(d),**h) for h in collisions(ss[r['id']].m.translate((a*d).tolist()),fixed))
    rr=dict(id=r['id'],status='PASS' if not hits and not insertion else 'FAIL',tool_hits=hits,insertion_hits=insertion,travel_mm=25,tool_envelope='2AF L-key long leg70mm / transverse20mm at73 sampled orientations')
    print('RAISED_SHELL_TOOL',r['id'],rr['status'],hits[:2],insertion[:2],flush=True);toolrows.append(rr)
out=dict(source_blend_sha256=hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),paths=rows,tools=toolrows,status='PASS' if all(r['status']=='PASS' for r in rows+toolrows) else 'BLOCKED',scope='Two independently supported rigid subassemblies. No wire, grip, holding fixture or manual sequence qualification; no geometry changes.')
(HERE/'dual_body_sequence.json').write_text(json.dumps(out,indent=2)+'\n')
