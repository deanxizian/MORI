"""Current saved assembly detail views, plus explicitly marked local wire samples."""
from pathlib import Path
import sys,hashlib
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[2]/'scripts'))
from common import *
from render import camera
from neck_capacity import local_curves
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load_collections();assembled();bpy.context.view_layer.update()
source=ROOT/'mori_v1_2.blend';source_hash=sha(source)
obs={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in obs.items()}
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(.78,.81,.83)
scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1280;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
pack,data,_=local_curves(P['neck_harness_capacity']);wires=[];tag=PREFIX+'NECK_REVIEW_'
for i,row in enumerate(pack['selected']):
    pts=data[f'wire{i}_y0'];cu=bpy.data.curves.new(tag+str(i),'CURVE')
    cu.dimensions='3D';cu.bevel_depth=row['OD_mm']/2;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
    for target,p in zip(sp.points,pts):target.co=(*p,1)
    o=bpy.data.objects.new(tag+str(i),cu);scene.collection.objects.link(o);o.color=(.95,.4,.05,1)
    o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['role']='local_route_review'
    o['evidence_scope']='11 local space samples, not complete or selected harness';wires.append(o)
images=[]
def view(name,keep,eye,target,scale,wire=False):
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for n in keep:
        o=obs[n];o.hide_render=False;o.hide_set(False)
        o.color=(.34,.48,.52,1) if o.get('category')=='PRINTABLE' else (.72,.73,.74,1)
    for o in wires:o.hide_render=not wire
    cam=camera('M1_49_'+name,eye,target,scale);cam.data.clip_start=.1
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','sha256':sha(OUT/(name+'.png')),'native_parts':sorted(keep),'local_wire_samples':wire})
core={'Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper','Yaw_Bearing'}
mount={'Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Servo','Pitch_Servo',
       'Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1','Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1'}
view('supports',core|mount,(150,-220,280),(0,-2,172),132)
view('local_wires',core|mount,(150,-220,280),(0,-2,172),132,True)
view('neck_detail',{'Pitch_Yoke','Yaw_Bearing','Yaw_Reaction_Link'},(140,-220,245),(0,0,166),76,True)
assert all(geometry_record(o)==before[n] for n,o in obs.items())
assert sha(source)==source_hash
save_json(OUT/'render_manifest.json',{'revision':P['revision'],'source_blend_sha256':source_hash,
    'images':images,'robot_geometry_unchanged':True,'saved_to_main':False,'script_sha256':sha(Path(__file__))})
