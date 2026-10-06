"""Actual sections and editable C5 review; immutable main remains unchanged."""
from pathlib import Path
import sys,json,math,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,np,manifold,sha
from validate import rigidtr
from common import bpy,PREFIX,Vector
ctx=Context();scene=bpy.context.scene
b=json.loads((HERE/'C5_build.json').read_text())
v=json.loads((HERE/'C5_verification.json').read_text())
wall=json.loads((HERE/'C5_material.json').read_text())
assert b['status']==v['status']==wall['status']=='PASS'
assert v['build_sha256']==wall['build_sha256']==sha(HERE/'C5_build.json')
def solid(prefix,name):
    p=HERE/f'{prefix}_{name}.npz';d=np.load(p)
    m=manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
    return m,d
core=['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper','Yaw_Bearing']
sets={'main':{n:ctx.ss[n].m for n in core},
      'C4':{n:solid('C4',n)[0] for n in core},
      'C5':{n:solid('C5',n)[0] for n in core}}
head=ctx.ss['Head_Rear'].m.transform(np.asarray(rigidtr(0,25))[:3,:])
tr=np.array([[0,1,0,0],[0,0,1,0],[-1,0,0,8.5]])
section={}
for tag,parts in sets.items():
    layers={**parts,'Head_Rear':head,'Yaw_Reaction_Link':ctx.ss['Yaw_Reaction_Link'].m}
    section[tag]={'horizontal_Z166':{n:[p.tolist() for p in m.slice(166.).to_polygons()] for n,m in layers.items()},
                  'side_X8.5':{n:[p.tolist() for p in m.transform(tr).slice(0).to_polygons()] for n,m in layers.items()}}
(HERE/'C5_review_sections.json').write_text(json.dumps(dict(source_main_sha256=ctx.source_hash,
    script_sha256=sha(__file__),C5_build_sha256=sha(HERE/'C5_build.json'),sections=section))+'\n')
TAG=PREFIX+'C5_REVIEW_'
coll=bpy.data.collections.new(TAG+'Candidate');scene.collection.children.link(coll)
def mat(name,color):
    m=bpy.data.materials.new(TAG+name);m.diffuse_color=(*color,1);m.use_nodes=True
    m.node_tree.nodes.clear()
    p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    output=m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.58
    return m
trial=mat('Unadopted_print',(.22,.42,.45));metal=mat('Bearing_boundary',(.45,.51,.54))
wire=mat('Unselected_wire_allocation',(.93,.42,.065))
objects={}
def display_normals(me,name):
    # Same planar/curved normal policy as the current main, applied only to
    # this preview's owned meshes. Verify that vertices/triangles do not move.
    from head_surface_display import planar_directions
    before=hashlib.sha256(np.asarray([v.co[:] for v in me.vertices]).tobytes()+np.asarray([p.vertices[:] for p in me.polygons]).tobytes()).hexdigest()
    axes=planar_directions(name);threshold=math.cos(math.radians(.05))
    flat=[max(abs(p.normal.dot(a)) for a in axes)>=threshold for p in me.polygons]
    ef=[[] for _ in me.edges]
    for p,pl in zip(me.polygons,flat):
        p.use_smooth=not pl
        for k in p.loop_indices:ef[me.loops[k].edge_index].append(p.index)
    for e,fs in zip(me.edges,ef):
        if len(fs)==2:
            a,b=fs;ang=me.polygons[a].normal.angle(me.polygons[b].normal,0)
            e.use_edge_sharp=ang>math.radians(35) or ((flat[a] or flat[b]) and ang>math.radians(.05))
    me.update();normals=[n.vector[:] for n in me.corner_normals]
    for p,pl in zip(me.polygons,flat):
        if pl:
            for k in p.loop_indices:normals[k]=p.normal[:]
    me.normals_split_custom_set(normals);me.update()
    after=hashlib.sha256(np.asarray([v.co[:] for v in me.vertices]).tobytes()+np.asarray([p.vertices[:] for p in me.polygons]).tobytes()).hexdigest()
    assert before==after
for name in core:
    _,data=solid('C5',name)
    me=bpy.data.meshes.new(TAG+name);me.from_pydata(data['vertices_mm'],[],data['triangles'].tolist());me.update()
    o=bpy.data.objects.new(TAG+name,me);coll.objects.link(o);objects[name]=o
    me.materials.append(metal if name=='Yaw_Bearing' else trial)
    o['category']='PURCHASED_REFERENCE' if name=='Yaw_Bearing' else 'PRINTABLE'
    o['data_status']='VENDOR_DOCUMENTED' if name=='Yaw_Bearing' else 'ASSUMED'
    o['evidence_scope']='NSK boundary dimensions only; no internal race CAD or physical fit' if name=='Yaw_Bearing' else 'Trial C5 design; PA12 strength NOT_TESTED'
    o['state']='PROTOTYPE / UNVALIDATED';o['main_applied']=False
    o['source_file']=str((HERE/f'C5_{name}.npz').relative_to(ROOT));o['source_sha256']=sha(HERE/f'C5_{name}.npz')
    display_normals(me,name)
pack=json.loads((HERE/'C4_packing.json').read_text());curves=np.load(HERE/'C4_packed_curves.npz')
for i,row in enumerate(pack['selected']):
    points=curves[f'wire{i}_y0'];data=bpy.data.curves.new(TAG+f'Local_wire_{i}',type='CURVE')
    data.dimensions='3D';data.resolution_u=1;data.bevel_depth=row['OD_mm']/2;data.bevel_resolution=3;data.use_fill_caps=True
    sp=data.splines.new('POLY');sp.points.add(len(points)-1)
    for dst,q in zip(sp.points,points):dst.co=(*q,1.)
    o=bpy.data.objects.new(TAG+f'Local_wire_{i}',data);coll.objects.link(o);data.materials.append(wire)
    o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='Local space sample; not an actual selected full harness'
    o['diameter_mm']=row['OD_mm'];o['supplier_cut_length']='NOT_RELEASED'
keep={'Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Servo','Pitch_Servo',
      'Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1','Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1'}
for o in scene.objects:
    if o.name.startswith(PREFIX) and o.type in ['MESH','CURVE','FONT']:
        visible=o.name.startswith(TAG) or o.name.removeprefix(PREFIX) in keep
        o.hide_render=not visible;o.hide_set(not visible)
for c in bpy.data.collections:
    if c.name.startswith(PREFIX) and any(s in c.name for s in ['DATUMS','KEEP_OUT','ANNOTATIONS','DOCK','COUPONS']):c.hide_render=True
cd=bpy.data.cameras.new(TAG+'Camera');camera=bpy.data.objects.new(TAG+'Camera',cd);coll.objects.link(camera)
scene.camera=camera;cd.type='ORTHO';cd.clip_start=.1;cd.clip_end=3000
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1280;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
for name,pos,target,scale,base_visible in [
    ('C5_supports',(150,-220,280),(0,-2,172),132,True),
    ('C5_neck',(140,-220,245),(0,0,166),76,False)]:
    objects['Yaw_Base'].hide_render=not base_visible
    objects['Yaw_Anti_Lift_Keeper'].hide_render=not base_visible
    camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    cd.ortho_scale=scale;scene.render.filepath=str(HERE/(name+'.png'))
    bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
    print('C5_RENDER',name,flush=True)
for o in objects.values():o.hide_render=False;o.hide_set(False)
camera.location=(150,-220,280);camera.rotation_euler=(Vector((0,-2,172))-camera.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=132
ctx.assert_unchanged()
scene['study_scope']='C5 independent 3-print and bearing-boundary candidate. 11 local curves only; full endpoints, wired assembly and physical tests unresolved.'
scene['source_main_sha256']=ctx.source_hash
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'C5_review.blend'))
assert sha(ctx.main)==ctx.source_hash
print('C5_REVIEW_SAVED',flush=True)
