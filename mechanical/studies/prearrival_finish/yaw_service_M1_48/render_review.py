"""Editable independent route review. Native assembly file is read-only."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,sha,np
from common import bpy,PREFIX,Vector
ctx=Context();scene=bpy.context.scene
check=json.loads((HERE/'refined_adaptive_all.json').read_text())
assert check['status']=='PASS' and check['source_main_sha256']==ctx.source_hash
TAG=PREFIX+'YAW_SERVICE_REVIEW_'
coll=bpy.data.collections.new(TAG+'Review');scene.collection.children.link(coll)

def mat(name,color):
    m=bpy.data.materials.new(TAG+name);m.diffuse_color=(*color,1.)
    m.use_nodes=True;m.node_tree.nodes.clear()
    p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    output=m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*color,1.);p.inputs['Roughness'].default_value=.55
    return m
trial_mat=mat('Unadopted_print',(.28,.43,.47))
colors=[(.95,.35,.055),(.78,.57,.06),(.91,.25,.19),(.30,.66,.66)]
for name in ['Yaw_Base','Pitch_Yoke']:
    d=np.load(HERE/f'refined_{name}.npz')
    me=bpy.data.meshes.new(TAG+name);me.from_pydata(d['vertices_mm'],[],d['triangles'].tolist());me.update()
    o=bpy.data.objects.new(TAG+name,me);coll.objects.link(o);me.materials.append(trial_mat)
    o['category']='PRINTABLE';o['evidence']='ASSUMED';o['state']='PROTOTYPE / UNVALIDATED'
    o['scope']='Unadopted two-print channel candidate; strength and complete installation NOT_TESTED'
curves=np.load(HERE/'internal_full_curves.npz')
for pin in range(1,5):
    p=curves[f'pin{pin}_y0_p0']
    data=bpy.data.curves.new(TAG+f'UART_{pin}',type='CURVE')
    data.dimensions='3D';data.resolution_u=1;data.bevel_depth=.3302;data.bevel_resolution=3;data.use_fill_caps=True
    spline=data.splines.new('POLY');spline.points.add(len(p)-1)
    for dst,q in zip(spline.points,p):dst.co=(*q,1.)
    o=bpy.data.objects.new(TAG+f'UART_{pin}',data);coll.objects.link(o)
    data.materials.append(mat(f'Wire_{pin}',colors[pin-1]))
    o['category']='PLACEHOLDER';o['evidence']='ASSUMED';o['wire_OD_mm']=.6604
    o['Motion_J5_pin']=pin;o['CAM_mating_pin']='BLOCKED';o['supplier_cut_length']='NOT_RELEASED'
keep={'Load_Frame','Yaw_Reaction_Link','Yaw_Bearing','Yaw_Anti_Lift_Keeper','MCU_Carrier','MCU_Motion',
      'Power_Module','Rear_Interface_PCB','Head_CAM_Board','CAM_Board','CAM_Module'}
for obj in scene.objects:
    n=obj.name.removeprefix(PREFIX)
    if obj.type in ['MESH','CURVE','FONT']:
        visible=(obj.name.startswith(TAG) or n in keep or n.startswith(('Yaw_Servo','Pitch_Servo','Head_Yaw_Ear','Head_Pitch_Ear')))
        obj.hide_render=not visible;obj.hide_set(not visible)
for c in bpy.data.collections:
    if c.name.startswith(PREFIX) and any(s in c.name for s in ['DATUMS','KEEP_OUT','ANNOTATIONS','DOCK','COUPONS']):c.hide_render=True
camdata=bpy.data.cameras.new(TAG+'Camera');cam=bpy.data.objects.new(TAG+'Camera',camdata);coll.objects.link(cam)
scene.camera=cam;camdata.type='ORTHO';camdata.clip_start=.1;camdata.clip_end=3000
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1440;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
views=[('complete_route',(160,-240,260),(0,-7,177),163),('upper_route',(-135,-180,295),(0,-3,201),121)]
for name,position,target,scale in views:
    cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    camdata.ortho_scale=scale;scene.render.filepath=str(HERE/(name+'.png'))
    bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
    print('ROUTE_REVIEW_RENDER',name,flush=True)
ctx.assert_unchanged()
scene['study_scope']='Independent 4-wire/two-print candidate; remaining 7 head wires, FFC, retention and full assembly unresolved. Main M1.48 untouched.'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'review.blend'))
assert sha(ctx.main)==ctx.source_hash
