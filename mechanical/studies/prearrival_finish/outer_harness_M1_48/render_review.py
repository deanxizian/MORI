"""Independent native-geometry review, with true-diameter candidate curves."""
from pathlib import Path
import sys, json, math
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from native_context import *
ctx=Context()
verification=json.loads((HERE/'verification.json').read_text())
assert verification['status']=='PASS' and ctx.source_hash==verification['source_main_sha256']
d=json.loads((HERE/'packing.json').read_text())
curves=np.load(HERE/'packed_curves.npz')
TAG=PREFIX+'OUTER_HARNESS_M1_48_'
scene=bpy.context.scene
coll=bpy.data.collections.new(TAG+'Review')
scene.collection.children.link(coll)

def material(name,color):
    mat=bpy.data.materials.new(TAG+name)
    mat.diffuse_color=(*color,1.)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    nodes.clear()
    node=nodes.new('ShaderNodeBsdfPrincipled')
    output=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node.outputs['BSDF'],output.inputs['Surface'])
    node.inputs['Base Color'].default_value=(*color,1.)
    node.inputs['Roughness'].default_value=.55
    return mat

warm=material('Candidate_wire',(.93,.32,.025))
old=material('Existing_wire_allocation',(.23,.32,.37))
mate_mat=material('Mating_allocation',(.75,.49,.16))

for pin in range(1,5):
    p=curves[f'pin{pin}']
    data=bpy.data.curves.new(TAG+f'J5_{pin}',type='CURVE')
    data.dimensions='3D';data.resolution_u=1;data.bevel_depth=d['wire_OD_mm']/2
    data.bevel_resolution=4;data.use_fill_caps=True
    spline=data.splines.new('POLY');spline.points.add(len(p)-1)
    for dst,v in zip(spline.points,p):dst.co=(*v,1.)
    obj=bpy.data.objects.new(TAG+f'J5_{pin}',data);coll.objects.link(obj)
    data.materials.append(warm)
    obj['category']='PLACEHOLDER';obj['evidence']='ASSUMED'
    obj['scope']='Body-root to neck only; not adopted; true OD 0.6604 mm'
    obj['Motion_J5_pin']=pin

for name,target in ctx.targets.items():
    if not name.startswith('fixed_wire_'):continue
    m=target['m'].to_mesh64()
    mesh=bpy.data.meshes.new(TAG+name)
    mesh.from_pydata(m.vert_properties[:,:3],[],m.tri_verts.tolist());mesh.update()
    obj=bpy.data.objects.new(TAG+name,mesh);coll.objects.link(obj)
    mesh.materials.append(old)
    obj['category']='PLACEHOLDER';obj['evidence']='ASSUMED'

for s in ctx.plug.values():
    s.o.data.materials.clear();s.o.data.materials.append(mate_mat)

core_visible={'Load_Frame','Yaw_Base','Yaw_Bearing','Yaw_Reaction_Link','Yaw_Keeper',
              'Power_Module','MCU_Carrier','MCU_Motion','Rear_Interface_PCB','Body_IMU',
              'Header_E_Straight','Socket_AB','Socket_CD','Socket_E'}
for obj in scene.objects:
    n=obj.name.removeprefix(PREFIX)
    if obj.type in ['MESH','CURVE','FONT']:
        visible=(n in core_visible or obj.name.startswith(TAG) or
                 obj.name.startswith(PREFIX+'PREARRIVAL_Plug_') or
                 n.startswith('Yaw_Base_'))
        obj.hide_render=not visible;obj.hide_set(not visible)
for c in bpy.data.collections:
    if c.name.startswith(PREFIX) and any(x in c.name for x in ['DATUMS','KEEP_OUT','ANNOTATIONS','DOCK','COUPONS']):
        c.hide_render=True

camdata=bpy.data.cameras.new(TAG+'Camera')
cam=bpy.data.objects.new(TAG+'Camera',camdata);coll.objects.link(cam)
scene.camera=cam;camdata.type='ORTHO';camdata.clip_start=.1;camdata.clip_end=3000
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1440;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
views=[('body_routes',(130,-215,260),(0,-6,141),128),
       ('body_routes_top',(0,-4,460),(0,-4,140),123)]
for name,position,target,scale in views:
    cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    camdata.ortho_scale=scale
    scene.render.filepath=str(HERE/(name+'.png'))
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    print('OUTER_REVIEW_RENDER',name,flush=True)

section_names=['Body_Upper','Yaw_Base','Yaw_Bearing','Yaw_Reaction_Link','Pitch_Yoke','Head_Front','Head_Rear','Head_Lower_Guard']
section_solids={n:ctx.ss[n].m for n in section_names if n in ctx.ss}
polygons=lambda section:[p.tolist() for p in section.to_polygons()]
sections=dict(radial={str(r['azimuth_deg']):{n:polygons(m.rotate([0,0,-r['azimuth_deg']]).rotate([90,0,0]).slice(0))
                    for n,m in section_solids.items()} for r in d['selected']},
    horizontal={str(z):{n:polygons(m.slice(z)) for n,m in section_solids.items()} for z in [168.,175.,182.,189.,193.]},
    source_main_sha256=ctx.source_hash,source_verification_sha256=sha(HERE/'verification.json'),
    native_geometry_only=True,units='mm')
(HERE/'sections.json').write_text(json.dumps(sections,ensure_ascii=False,indent=2)+'\n')
ctx.assert_unchanged()
cam.location=views[0][1];cam.rotation_euler=(Vector(views[0][2])-cam.location).to_track_quat('-Z','Y').to_euler()
camdata.ortho_scale=views[0][3]
scene['study_scope']='Four candidate fixed J5-to-neck wires only. Head loop and assembly NOT_TESTED. Main untouched.'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'review.blend'))
assert sha(ctx.main)==ctx.source_hash
print('OUTER_REVIEW_SAVED',flush=True)
