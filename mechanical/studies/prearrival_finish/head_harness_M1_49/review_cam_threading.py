"""Review only the tested formation and explicit obstructions; no main edits."""
from pathlib import Path
import json, sys, time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'threading_review'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import bpy,COLS,manifold
from render import camera
from cam_threading_geometry import service

ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
F=REST/'threading_formation_v2';D=REST/'threading_descent';K=REST/'contact_corridor'
B=REST/'bench_preassembly_v2';G=REST/'sliding_guide_v4';C=REST/'return_clamp_v3'
reports=[F/'review.json',D/'review.json',K/'review.json'];inputs=list(reports)
for path in reports:
    r=read(path)
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert read(reports[0])['status']=='PASS'
deferred=set(read(B/'review.json')['not_yet_installed'])|{'Plug_motion_J5'}
inputs.append(B/'review.json')
tag='MORI_CAM_THREAD_REVIEW__';scene=bpy.context.scene;objects=[];natives={}
def mesh(name,v,f,color):
    me=bpy.data.meshes.new(tag+name);me.from_pydata(np.asarray(v).tolist(),[],np.asarray(f).tolist());me.update()
    o=bpy.data.objects.new(tag+name,me);scene.collection.objects.link(o);o.color=color
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Review copy, nominal candidate only';objects.append(o);return o
def stored(path):
    inputs.append(path);a=np.load(path);return a['vertices_mm'],a['triangles']
for name,s in ctx.ss.items():
    if name in deferred or name in ['Body_Upper','Body_Lower'] or s.group not in ['yaw','pitch','body']:continue
    v,f=s.v,s.f
    if name=='Pitch_Cradle':v,f=stored(C/'Pitch_Cradle_candidate.npz')
    if name=='Pitch_Yoke':v,f=stored(G/'Pitch_Yoke_candidate.npz')
    if name=='Yaw_Base':v,f=stored(BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz')
    natives[name]=mesh(name,v,f,(.66,.71,.73,1))

def wire(name,p,color,r=.3302):
    cu=bpy.data.curves.new(tag+name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(p)-1)
    for a,b in zip(sp.points,p):a.co=(*b,1)
    o=bpy.data.objects.new(tag+name,cu);scene.collection.objects.link(o);o.color=color
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';objects.append(o);return o
def box_outline(name,lo,hi):
    vertices=np.array([[x,y,z] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]])
    out=[]
    for i,p in enumerate(vertices):
        for j in range(i+1,len(vertices)):
            if np.count_nonzero(np.abs(p-vertices[j])>1e-6)==1:
                out.append(wire(name+str(i)+'_'+str(j),np.array([p,vertices[j]]),(.96,.44,.06,1),.06))
    return out
def show(items):
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True;o.hide_set(True)
    for o in items:o.hide_render=False;o.hide_set(False)
for col in COLS.values():col.hide_render=False;col.hide_viewport=False
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=False;scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(.9,.92,.94)
scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1400;scene.render.resolution_y=1150;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
images=[]
def render(name,items,eye,target,scale,scope):
    show(items);cam=camera(tag+name,eye,target,scale);cam.data.clip_start=.1
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png')),scope=scope))

inputs.extend([F/'states.npz',BASE/'cam_side_fans/c6_join/candidate_curves.npz',B/'bench_curves.npz',HERE/'cam_threading_geometry.py'])
states=np.load(F/'states.npz');curves=np.load(BASE/'cam_side_fans/c6_join/candidate_curves.npz');bench=np.load(B/'bench_curves.npz')
palette=[(.02,.47,.79,1),(.09,.64,.23,1),(.78,.2,.6,1),(.9,.54,.04,1)]
loose=[]
for pin in range(1,5):
    p=states['approach_pin1'] if pin==1 else states[f'parking_pin{pin}']
    loose.append(wire('forming_'+str(pin),p,palette[pin-1]))
loose+=box_outline('formation_contact',[-27.84,-11.75,264.3],[-25.76,-10.25,270.])
render('formation',list(natives.values())+loose,(-255,370,401),(-12,-13,327),320,
       'Pin1 ready above guide; pins2-4 still parked. Other free terminal ends extend above crop. No full feed claim.')

# A concrete later obstruction, not just the conservative first threshold.
# At rear Z252, actual stored points of pin1 lie strictly inside the nominal
# pin2 contact box. That is sufficient to show this particular sequence fails.
q=bench['CAM_2']-[180,0,0];i=int(np.flatnonzero(q[:,2]>=224.6000061-1e-7)[0])
fixed=q[:i+1];length=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()-np.linalg.norm(np.diff(fixed,axis=0),axis=1).sum())
free,meta=service(q[i],length,[-26.8,-11.,252.]);moving=np.vstack([fixed[:-1],free])
previous=curves['CAM_1_y0_p0'];lo=np.array([-27.84,-11.75,246.3]);hi=np.array([-25.76,-10.25,252.])
inside=np.flatnonzero(np.all(previous>lo+.05,axis=1)&np.all(previous<hi-.05,axis=1));assert len(inside)>0
witness=previous[inside[len(inside)//2]]
detail=[wire('earlier_pin1',previous,palette[0]),wire('moving_pin2',moving,palette[1])]+box_outline('blocked_contact',lo,hi)
dot=manifold.Manifold.sphere(.5,32).translate(witness);a=dot.to_mesh64();detail.append(mesh('intersection_witness',a.vert_properties[:,:3],a.tri_verts,(.95,.05,.06,1)))
render('descent_conflict',list(natives.values())+detail,(-62,76,281),(-27,-12,249),32,
       'Orange wireframe is nominal PH outline; red point is a stored pin1 centreline point inside the pin2 contact at rear Z252.')

v,f=stored(G/'Pitch_Yoke_candidate.npz');solid=manifold.Manifold(manifold.Mesh64(v,f.astype(np.uint64)))
cut=solid^manifold.Manifold.cube([80,50,60]).translate([-60,-60.2,170.]);a=cut.to_mesh64()
section=mesh('Pitch_Yoke_review_section',a.vert_properties[:,:3],a.tri_verts,(.64,.7,.73,1))
v,f=stored(K/'blocked_contact_pin1.npz');contact=mesh('nominal_PH_neck_obstruction',v,f,(.97,.55,.1,1))
path=np.load(K/'paths.npz')['pin1_screened'];inputs.append(K/'paths.npz')
pathobj=wire('restricted_contact_path',path,(.08,.56,.77,1),.12)
render('neck_corridor_section',[section,contact,pathobj],(-55,47,226),(-9,-12,194),37,
       'Yoke is sectioned at Y=-10.2 for view only; amber contact is at its first gap failure. Main and candidate solids were not changed.')

show(list(natives.values())+detail);camera(tag+'editable',(-62,76,281),(-27,-12,249),40)
ctx.assert_unchanged();blend=OUT/'MORI_M1_49_CAM_threading_review.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
r=dict(status='PASS',scope='Review generation and explicit centreline-inside-contact witness; not full assembly release',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},images=images,
    obstruction=dict(pin=2,earlier_pin=1,contact_rear_mm=[-26.8,-11.,252.],contact_box_lo_mm=lo.tolist(),contact_box_hi_mm=hi.tolist(),
        stored_centerline_points_strictly_inside=len(inside),witness_point_mm=witness.tolist(),minimum_strict_inset_mm=.05),
    blend_sha256=sha(blend),main_changed=False,approved=False,full_harness='BLOCKED',physical_fit='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CAM_THREAD_REVIEW_DONE',r['status'],len(inside),flush=True)
