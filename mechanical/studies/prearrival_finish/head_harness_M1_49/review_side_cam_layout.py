"""Render the current checked neck/side-tail scope without filling missing fans."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
N=HERE/'remaining_routes/neck_side_tail_gentle';S=HERE/'remaining_routes/cam_side_following'
OUT=HERE/'remaining_routes/side_cam_review';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import bpy,COLS
from validate import rigidtr
from render import camera
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());nr=read(N/'join_screen.json')
reports=[N/'join_screen.json'];sr=read(S/'loop_screen.json') if (S/'loop_screen.json').exists() else None
if sr:reports.append(S/'loop_screen.json')
for path in reports:
    r=read(path)
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert nr['status']=='PASS' and sha(N/'neck_curves.npz')==nr['neck_curve_sha256'] and sha(N/'tails.npz')==nr['tail_sha256']
neck=np.load(N/'neck_curves.npz');tails=np.load(N/'tails.npz');service=bool(sr and sr['status']=='PASS')
if service:assert sha(S/'curves.npz')==sr['curve_sha256']
upper=np.load(S/'curves.npz') if service else None
tag='MORI_SIDE_CAM_REVIEW__';new=[];clones={}
# Render baked world-space copies. Never change an original's matrix: assigning
# matrix_world can alter decomposition and trigger a different result on save.
for n,s in ctx.ss.items():
    if (s.group in ['yaw','pitch'] or n in ['Yaw_Base','Yaw_Bearing','Load_Frame']) and n not in ['Head_Front','Head_Rear']:
        mesh=bpy.data.meshes.new(tag+'solid_'+n);mesh.from_pydata(s.v.tolist(),[],s.f.tolist());mesh.update()
        o=bpy.data.objects.new(tag+'solid_'+n,mesh);bpy.context.scene.collection.objects.link(o);o.color=s.o.color
        o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='Baked visualization copy of unchanged native solid';clones[n]=o
def add(key,p,radius,color):
    cu=bpy.data.curves.new(tag+key,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(p)-1)
    for v,point in zip(sp.points,p):v.co=(*point,1)
    o=bpy.data.objects.new(tag+key,cu);bpy.context.scene.collection.objects.link(o);o.color=color
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='Independent partial route; fixed connecting fans and complete harness qualification absent';new.append(o)
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(.86,.88,.90);scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1400;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';images=[]
palette=[(.04,.71,.79,1),(.12,.75,.3,1),(.85,.27,.66,1),(.95,.57,.08,1)]
for pitch in [25,0]:
    for o in new:bpy.data.objects.remove(o,do_unlink=True)
    new=[];tr=rigidtr(0,pitch);mat=np.asarray(tr)
    for n,o in clones.items():
        o.matrix_world=tr if ctx.ss[n].group=='pitch' else rigidtr(0,0)
    for slot in range(11):add('neck_'+str(slot),neck[f'wire{slot}_y0'],nr['OD_mm'][slot]/2,(1.,.58,.09,1))
    for pin in range(1,5):
        p=upper[f'pin{pin}_y0_p{pitch}'] if service else tails[f'pin{pin}']@mat[:3,:3].T+mat[:3,3]
        add('CAM_'+str(pin),p,.3302,palette[pin-1])
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for o in clones.values():o.hide_render=False;o.hide_set(False)
    for o in new:o.hide_render=False;o.hide_set(False)
    name=f'side_cam_pitch_{pitch}';cam=camera(tag+name,(-130,-160,304),(-12,-1,224),112);cam.data.clip_start=.1
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png')),pitch_deg=pitch))
ctx.assert_unchanged();blend=OUT/'MORI_M1_49_side_CAM_candidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
case=next(r for r in nr['results'] if r['status']=='PASS')
inputs=reports+[N/'neck_curves.npz',N/'tails.npz']+([S/'curves.npz'] if service else [])
r=dict(status='PASS',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},images=images,blend_sha256=sha(blend),
       scope='Visual delivery of checked neck and moving side tails; fixed connecting fans remain intentionally absent.',
       includes_service_loops=service,service_loop_check=sr['status'] if sr else 'NOT_TESTED',neck_tail_check=nr['status'],
       changed_neck_slots=case['changed_slots'],offset_mm=case['shift_y_mm'],new_native_checks=case['native_checks'],new_tail_pair_checks=case['tail_pair_checks'],
       new_neck_pair_checks=len(case['pairs']),main_changed=False,C6_main_applied=False,full_harness='BLOCKED',
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('SIDE_CAM_REVIEW',r['status'],service,flush=True)
