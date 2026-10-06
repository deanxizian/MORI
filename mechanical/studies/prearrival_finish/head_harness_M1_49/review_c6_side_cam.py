"""Render the conditional C6 / continuous CAM candidate without changing native objects."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
JOIN=BASE/'cam_side_fans/c6_join';C6=BASE/'c6_left_slot_entry';OUT=JOIN/'review';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import bpy,COLS
from validate import rigidtr
from render import camera
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());report=read(JOIN/'join_review.json')
assert report['status']=='PASS' and not report['approved'] and not report['main_changed']
for f,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(JOIN/'candidate_curves.npz')==report['curve_sha256']
curves=np.load(JOIN/'candidate_curves.npz');c6=np.load(C6/'Yaw_Base_candidate.npz')
tag='MORI_C6_SIDE_CAM_VIEW__';clones={};wires=[];scene=bpy.context.scene
for n,s in ctx.ss.items():
    if n in ['Head_Front','Head_Rear','Body_Upper','Body_Lower'] or s.group not in ['yaw','pitch','body']:continue
    v=c6['vertices_mm'] if n=='Yaw_Base' else s.v;f=c6['triangles'] if n=='Yaw_Base' else s.f
    mesh=bpy.data.meshes.new(tag+n);mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update()
    o=bpy.data.objects.new(tag+n,mesh);scene.collection.objects.link(o);o.color=(.68,.56,.32,1) if n=='Yaw_Base' else s.o.color
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='UNAPPROVED C6 visualization' if n=='Yaw_Base' else 'Baked unchanged native solid';clones[n]=o
def wire(key,p,radius,color):
    cu=bpy.data.curves.new(tag+key,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(p)-1)
    for a,b in zip(sp.points,p):a.co=(*b,1.)
    o=bpy.data.objects.new(tag+key,cu);scene.collection.objects.link(o);o.color=color
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='Conditional continuous reference curve; no supplier cut length release';wires.append(o)
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False;scene.display.shading.background_type='WORLD'
scene.world.color=(.86,.88,.90);scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
palette=[(.04,.71,.79,1),(.12,.75,.3,1),(.85,.27,.66,1),(.95,.57,.08,1)];images=[]
for name,yaw,pitch,eye,target,scale in [('continuous_CAM_head',0,0,(-130,-160,304),(-12,-1,224),115),('continuous_CAM_body',0,0,(-150,-205,206),(-2,-1,161),155),('continuous_CAM_motion',60,25,(-155,-195,305),(0,0,213),150)]:
    for o in wires:bpy.data.objects.remove(o,do_unlink=True)
    wires=[]
    for n,o in clones.items():o.matrix_world=rigidtr(yaw,pitch) if ctx.ss[n].group=='pitch' else rigidtr(yaw,0) if ctx.ss[n].group=='yaw' else rigidtr(0,0)
    for pin in range(1,5):wire('CAM_'+str(pin),curves[f'CAM_{pin}_y{yaw}_p{pitch}'],.3302,palette[pin-1])
    for name0 in ['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2']:wire(name0,curves[f'{name0}_y{yaw}'],.5842,(.78,.57,.17,1))
    for slot in [3,6]:wire('SPK_reservation_'+str(slot),curves[f'SPK_reservation_{slot}_y{yaw}'],.4445,(.55,.55,.55,1))
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for o in list(clones.values())+wires:o.hide_render=False;o.hide_set(False)
    cam=camera(tag+name,eye,target,scale);cam.data.clip_start=.1;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True);images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png')),yaw_deg=yaw,pitch_deg=pitch))
ctx.assert_unchanged();blend=OUT/'MORI_M1_49_continuous_CAM_C6_candidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
inputs=[JOIN/'join_review.json',JOIN/'candidate_curves.npz',C6/'Yaw_Base_candidate.npz']
r=dict(status='PASS',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},images=images,blend_sha256=sha(blend),
    scope='Visual evidence of independent C6 candidate and four connected CAM routes. Other upper endpoints and restraint remain incomplete.',
    original_geometry_fingerprints_after_save='PASS',main_changed=False,C6_approved=False,C6_main_applied=False,full_harness='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('C6_SIDE_CAM_REVIEW',r['status'],flush=True)
