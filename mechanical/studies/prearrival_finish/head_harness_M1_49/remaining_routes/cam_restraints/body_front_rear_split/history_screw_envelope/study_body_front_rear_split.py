"""Independent body-shell split study. No approved geometry is replaced.

Two front/rear pieces retain the current body mother surface and four frame
mounts. Obsolete horizontal seam hardware is omitted. Four underside tool
ports are proposed, explicitly unapproved. Rigid paths are finite samples.
"""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'body_front_rear_split'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,manifold,P,D
from validate import Solid,rigidtr
from interface_completion import axial
from monocoque_structure import source_build
ctx=Context();started=time.time()
inputs=[ROOT/'mechanical/scripts/build.py',ROOT/'mechanical/scripts/validate.py',
        ROOT/'mechanical/scripts/interface_completion.py']
def box(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
def save(n,m):
    a=m.to_mesh64();p=OUT/(n+'.npz')
    np.savez_compressed(p,vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
    return dict(file=str(p.relative_to(ROOT)),sha256=sha(p),volume_mm3=float(m.volume()),
                islands=len(m.decompose()),manifold=str(m.status()),bounds_mm=list(m.bounding_box()))
def collision(m,fixed):
    bb=np.asarray(m.bounding_box());out=[]
    for n,t in fixed.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
        overlap=m^t;v=float(overlap.volume())
        if abs(v)>1e-5:out.append(dict(target=n,overlap_mm3=v,bounds_mm=list(overlap.bounding_box())))
    return out

# Derive only the repair skin from the same current generator parameters.
b=source_build()
o=b.body_outer('candidate_body_split_outer');outer=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True)
o=b.body_outer('candidate_body_split_inner',P['shell_thickness_mm']);inner=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True)
skin=outer-inner
original=ctx.ss['Body_Upper'].m+ctx.ss['Body_Lower'].m
zones=manifold.Manifold()
for sx in [-1,1]:
 for sy in [-1,1]:
    xx=sorted([sx*16.2,sx*90]);yy=sorted([sy*65,sy*90])
    zones+=box([xx[0],yy[0],0],[xx[1],yy[1],107])
# Replace the old four seam lugs/sleeves/counterbores by the exact mother skin.
joined=(original-zones)+(skin^zones)
gap=P['seam_gap_mm']/2
joined+=skin^box([-200,-200,D['body_z']-gap-.01],[200,200,D['body_z']+gap+.01])
before_ports=joined
for x,y in P['shell_service']['frame_mount_xy_mm']:
    joined-=axial(3.3,180,[x,y,20],[0,0,1])
front=joined^box([-200,gap,0],[200,200,300])
rear=joined^box([-200,-200,0],[200,-gap,300])
forms={'Body_Front_candidate':front,'Body_Rear_candidate':rear}
records={n:save(n,m) for n,m in forms.items()}
assert all(v['islands']==1 and v['manifold']=='Error.NoError' for v in records.values()),records
native={n:s.m for n,s in ctx.ss.items()}
retired={n for n in native if n.startswith(('Shell_Screw_','Shell_Insert_'))}
fasteners={n for n in native if n.startswith('Frame_Screw_')}
front_follow={n for n in native if n.startswith('Speaker')}
rear_follow={n for n in native if n.startswith('Rear_Interface_')}|{'Power_Switch','USB_Receptacle'}
for n in native:
    if n.startswith('Frame_Insert_'):
        (front_follow if (ctx.ss[n].lo[1]+ctx.ss[n].hi[1])>0 else rear_follow).add(n)
modules={
 'front':{**{n:native[n] for n in front_follow},'Body_Front_candidate':front},
 'rear':{**{n:native[n] for n in rear_follow},'Body_Rear_candidate':rear,
         **{'Plug_'+n:ctx.plug[n].m for n in ['rear_J2','rear_J3']}}
}
base_fixed={n:m for n,m in native.items() if n not in retired|fasteners|front_follow|rear_follow|{'Body_Upper','Body_Lower'}}
base_fixed.update({'Plug_'+n:s.m for n,s in ctx.plug.items() if n not in ['rear_J2','rear_J3']})
paths=[]
for wheels in ['present','tyres_hubs_deferred']:
    fixed={n:m for n,m in base_fixed.items() if wheels=='present' or n not in
           {'Tire_L','Tire_R','Wheel_Hub_L','Wheel_Hub_R','Wheel_End_Screw_L','Wheel_End_Screw_R','Wheel_End_Washer_L','Wheel_End_Washer_R'}}
    for label,sign in [('front',1),('rear',-1)]:
        group=modules[label];first=None;checked=0
        for travel in np.arange(0,220.01,1.):
            for n,m in group.items():
                hh=collision(m.translate([0,float(travel)*sign,0]),fixed)
                if hh:first=dict(travel_mm=float(travel),moving=n,hits=hh);break
            checked+=1
            if first:break
        row=dict(module=label,wheels=wheels,status='BLOCKED' if first else 'PASS',
                 direction=[0,sign,0],travel_mm=220,step_mm=1,checked_samples=checked,first_failure=first)
        paths.append(row);print('BODY_SPLIT_PATH',json.dumps(row),flush=True)

# Tools and real frame screws enter from below with the closed candidate shell.
# The body can be inverted in a bench fixture; no floor/standing claim.
fixed={n:m for n,m in native.items() if n not in retired|fasteners|{'Body_Upper','Body_Lower'}}
fixed.update(forms)
fixed.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))})
toolrows=[]
for i,(x,y) in enumerate(P['shell_service']['frame_mount_xy_mm']):
    # Conservative straight shaft plus handle; nominal cross-drive compatibility
    # is not established by this geometric envelope.
    shaft=axial(2.5,125,[x,y,109-62.5],[0,0,1])
    handle=axial(10,60,[x,y,109-125-30],[0,0,1])
    parts=[shaft,handle];hits=[]
    for j,m in enumerate(parts):
        mesh=m.to_mesh64();v=np.asarray(mesh.vert_properties[:,:3]);hull=manifold.Manifold.hull_points(np.r_[v,v+[0,0,-150]].tolist())
        hits += [dict(piece=j,**h) for h in collision(hull,fixed)]
    screw=ctx.ss[f'Frame_Screw_{i}'].m
    s=ctx.ss[f'Frame_Screw_{i}'];r=np.linalg.norm(s.v[:,:2]-[x,y],axis=1)
    headtop=float(s.v[r>1.5001,2].max())
    head=screw^box([x-10,y-10,0],[x+10,y+10,headtop])
    shank=screw^box([x-10,y-10,headtop],[x+10,y+10,250])
    assert abs((screw-(head+shank)).volume())<1e-6
    for j,m in enumerate([head,shank]):
        mesh=m.to_mesh64();v=np.asarray(mesh.vert_properties[:,:3]);hull=manifold.Manifold.hull_points(np.r_[v,v+[0,0,-150]].tolist())
        hits += [dict(piece='screw_'+str(j),**h) for h in collision(hull,fixed)]
    row=dict(screw=f'Frame_Screw_{i}',axis_mm=[x,y],status='BLOCKED' if hits else 'PASS',hits=hits)
    toolrows.append(row);print('BODY_SPLIT_FRAME_ACCESS',json.dumps(row),flush=True)

# Changed shell against the full moving head at the project's 130 poses.
motion=[]
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
    for n,s in ctx.ss.items():
        if s.group not in ['yaw','pitch']:continue
        tr=np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))[:3,:]
        hh=collision(s.m.transform(tr),forms)
        if hh:motion.append(dict(yaw_deg=yaw,pitch_deg=pitch,part=n,hits=hh))
    print('BODY_SPLIT_MOTION',yaw,pitch,len(motion),flush=True)

# Explicit edit boundary: every difference lies in old seam repair, new seam,
# horizontal seam fill, or the four proposed underside ports.
new=front+rear;allowed=zones+box([-200,-200,99.79],[200,200,100.21])+box([-200,-gap-.01,0],[200,gap+.01,300])
for x,y in P['shell_service']['frame_mount_xy_mm']:allowed+=axial(3.301,180.02,[x,y,20],[0,0,1])
outside=((new-original)+(original-new))-allowed
assert abs(outside.volume())<1e-5
ctx.assert_unchanged()
r=dict(status='PASS' if all(x['status']=='PASS' for x in paths+toolrows) and not motion else 'BLOCKED',
    scope='Unapproved two-piece front/rear body split with original four frame mounts; rigid route and tool study',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},parts=records,
    modules={k:sorted(v) for k,v in modules.items()},omitted=sorted(retired),deferred_frame_screws=sorted(fasteners),
    shell_prints_before=2,shell_prints_after=2,fasteners_removed=8,fasteners_added=0,
    proposed_new_tool_ports=dict(count=4,diameter_mm=6.6,axis_xy_mm=P['shell_service']['frame_mount_xy_mm'],entry='underside'),
    paths=paths,frame_tool_access=toolrows,head_motion=dict(poses=130,status='FAIL' if motion else 'PASS',failures=motion),
    material_change_outside_declared_regions_mm3=float(outside.volume()),
    nominal_tool='ASSUMED diameter5 x125mm shaft; diameter20 x60mm handle; 150mm continuous axial entry/exit hulls',
    existing_fastener_drive_compatibility='NOT_TESTED',seam_alignment_and_strength='NOT_TESTED',
    wire_deformation='NOT_TESTED',complete_assembly='BLOCKED',full_harness='BLOCKED',
    main_changed=False,approved=False,C6_main_applied=False,Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('BODY_FRONT_REAR_SPLIT_DONE',r['status'],r['elapsed_s'],flush=True)
