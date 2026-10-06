"""Show the explicit current-main retention trial without saving to the main."""
from pathlib import Path
import sys, json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from current_context import RetentionContext, PROJECT, np, sha
from common import bpy, PREFIX, Vector
ctx=RetentionContext(); scene=bpy.context.scene
assert json.loads((HERE/'anchors.json').read_text())['status']=='PASS'
tools=json.loads((HERE/'tools_and_tail.json').read_text())
TAG=PREFIX+'CAM_RETENTION_REVIEW_'
coll=bpy.data.collections.new(TAG+'Review');scene.collection.children.link(coll)

def mat(name,color):
    m=bpy.data.materials.new(TAG+name);m.diffuse_color=(*color,1.)
    m.use_nodes=True;m.node_tree.nodes.clear()
    p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    output=m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*color,1.);p.inputs['Roughness'].default_value=.6
    return m
trial_mat=mat('Unadopted_print',(.28,.43,.47));tie_mat=mat('Assumed_tie',(.92,.46,.06))
tail_mat=mat('Assumed_loose_tail',(.25,.68,.20))
def add_solid(name,path,material,category):
    data=np.load(path);me=bpy.data.meshes.new(TAG+name)
    me.from_pydata(data['vertices_mm'],[],data['triangles'].tolist());me.update()
    o=bpy.data.objects.new(TAG+name,me);coll.objects.link(o);me.materials.append(material)
    o['category']=category;o['evidence']='ASSUMED';o['state']='PROTOTYPE / UNVALIDATED'
    o['source_file']=str(path.relative_to(PROJECT));o['source_sha256']=sha(path)
    return o
for name,path in [('Yaw_Base',HERE.parent/'yaw_service_M1_48/refined_Yaw_Base.npz'),
                  ('Pitch_Yoke',HERE/'Pitch_Yoke.npz'),('Pitch_Cradle',HERE/'Pitch_Cradle.npz')]:
    add_solid(name,path,trial_mat,'PRINTABLE')
for key in ['yaw','connector']:
    for kind in ['band','head']:
        add_solid(key+'_'+kind,HERE/(key+'_'+kind+'.npz'),tie_mat,'PLACEHOLDER')
tail=add_solid('Loose_tie_tail',HERE/'connector_tail_2.npz',tail_mat,'PLACEHOLDER')
colors=[(.95,.35,.055),(.78,.57,.06),(.91,.25,.19),(.30,.66,.66)]
for pin in range(1,5):
    points=ctx.curves[f'pin{pin}_y0_p0']
    data=bpy.data.curves.new(TAG+f'UART_{pin}',type='CURVE');data.dimensions='3D'
    data.resolution_u=1;data.bevel_depth=.3302;data.bevel_resolution=3;data.use_fill_caps=True
    spline=data.splines.new('POLY');spline.points.add(len(points)-1)
    for dst,point in zip(spline.points,points):dst.co=(*point,1.)
    o=bpy.data.objects.new(TAG+f'UART_{pin}',data);coll.objects.link(o)
    data.materials.append(mat(f'Wire_{pin}',colors[pin-1]))
    o['category']='PLACEHOLDER';o['evidence']='ASSUMED';o['supplier_cut_length']='NOT_RELEASED'
deferred=set(tools['not_yet_installed'])
replaced={'Yaw_Base','Pitch_Yoke','Pitch_Cradle'}
for obj in scene.objects:
    n=obj.name.removeprefix(PREFIX)
    if obj.type in ['MESH','CURVE','FONT']:
        visible=obj.name.startswith(TAG) or (n in ctx.base and n not in deferred|replaced)
        obj.hide_render=not visible;obj.hide_set(not visible)
for c in bpy.data.collections:
    if c.name.startswith(PREFIX) and any(s in c.name for s in ['DATUMS','KEEP_OUT','ANNOTATIONS','DOCK','COUPONS']):c.hide_render=True
camdata=bpy.data.cameras.new(TAG+'Camera');cam=bpy.data.objects.new(TAG+'Camera',camdata);coll.objects.link(cam)
scene.camera=cam;camdata.type='ORTHO';camdata.clip_start=.1;camdata.clip_end=3000
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1440;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
views=[('anchors_front',(-145,185,305),(-9,-6,231),105,False),
       ('anchors_rear',(-125,-180,300),(-9,-7,230),99,False),
       ('tail_workspace',(-145,185,335),(-10,-4,252),144,True)]
for name,position,target,scale,tail_visible in views:
    tail.hide_render=not tail_visible;tail.hide_set(not tail_visible)
    cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    camdata.ortho_scale=scale;scene.render.filepath=str(HERE/(name+'.png'))
    bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
    print('CAM_RETENTION_RENDER',name,flush=True)
ctx.assert_unchanged()
scene['study_scope']='Three independent unadopted print candidates, two assumed ties, four prescribed CAM wires. This is not the complete wiring or assembly.'
scene['source_main_sha256']=ctx.ctx.source_hash
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'review.blend'))
assert sha(ctx.ctx.main)==ctx.ctx.source_hash
