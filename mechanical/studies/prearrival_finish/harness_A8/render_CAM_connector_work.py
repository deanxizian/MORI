"""Render the actual connector-side bench work allocation, without adoption."""
from pathlib import Path
import sys,json,hashlib
CW_SCRIPT=Path(__file__).resolve();CW_ROOT=CW_SCRIPT.parent
sys.path.insert(0,str(CW_ROOT.parents[3]/'mechanical/scripts'))
from common import *
from render import camera
from validate_head_cleanup import geometry_record

CW_OUT=CW_ROOT/'cam_connector_install'
CW_SOURCE=CW_ROOT/'cam_pitch_anchor/connector_anchor/review.blend'
assert Path(bpy.data.filepath)==CW_SOURCE
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
work=json.loads((CW_OUT/'work_access.json').read_text())
assert work['status']=='PASS' and work['preferred_angle_deg']==180.
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
added={}
def mesh_object(name,v,f,color):
    d=bpy.data.meshes.new('A8_CAM_WORK_'+name);d.from_pydata(v.tolist(),[],f.tolist());d.update()
    o=bpy.data.objects.new('A8_CAM_WORK_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_CAM_WORK_MAT_'+name,color,roughness=.7))
    o['study_owner']='A8_CAM_CONNECTOR_WORK';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Working allocation, not vendor CAD or physical measurement';added[name]=o
    return o
def npz_object(name,path,color):
    a=np.load(path);return mesh_object(name,a['vertices_mm'],a['triangles'],color)
def edges(name,path,color):
    o=npz_object(name+'_solid',path,color);mesh=o.data;adj={}
    for p in mesh.polygons:
        for e in p.edge_keys:adj.setdefault(tuple(sorted(e)),[]).append(p.normal.copy())
    d=bpy.data.curves.new('A8_CAM_WORK_'+name,'CURVE');d.dimensions='3D';d.bevel_depth=.10;d.bevel_resolution=2
    for e,normals in adj.items():
        if len(normals)==2 and normals[0].dot(normals[1])>.99:continue
        s=d.splines.new('POLY');s.points.add(1)
        for point,i in zip(s.points,e):point.co=(*mesh.vertices[i].co,1.)
    shown=bpy.data.objects.new('A8_CAM_WORK_'+name,d);bpy.context.scene.collection.objects.link(shown)
    d.materials.append(material('A8_CAM_WORK_EDGE_'+name,color,roughness=.6))
    shown['study_owner']='A8_CAM_CONNECTOR_WORK';shown['scope']='Presentation edges of solid work envelope';added[name]=shown
    o.hide_render=True;o.hide_viewport=True
edges('cutter',CW_OUT/'tool_180.0.npz',(.06,.57,.33))
edges('tail_work',CW_OUT/'tail_corridor.npz',(.76,.43,.08))
# Display the same catalogue mating allocation included in the collision test.
aa=np.load(CW_ROOT/'cam_pitch_port/allocation_meshes.npz')
mesh_object('CAM_catalogue_housing',aa['housing_v'],aa['housing_f'],(.94,.64,.2))
tails=np.load(CW_ROOT/'cam_fan_in/short_tail_v2/tails.npz')
colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.10),(.63,.25,.77)]
for slot in range(4):
    pt=tails[f'slot{slot}'][0];p=np.array([[pt[0],pt[1],200.],pt])
    d=bpy.data.curves.new(f'A8_CAM_WORK_local_wire_{slot}','CURVE');d.dimensions='3D';d.bevel_depth=.3302;d.bevel_resolution=3;d.use_fill_caps=True
    s=d.splines.new('POLY');s.points.add(1)
    for a,b in zip(s.points,p):a.co=(*b,1)
    o=bpy.data.objects.new(f'A8_CAM_WORK_local_wire_{slot}',d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material(f'A8_CAM_WORK_WIREMAT_{slot}',colors[slot],roughness=.6))
    o['study_owner']='A8_CAM_CONNECTOR_WORK';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Only Z200..214.6 local staging; not full loose wire or pin colour';added[f'wire_{slot}']=o

tie_objects=[o for o in bpy.data.objects if o.name in ['A8_CAM_CONNECTOR_head','A8_CAM_CONNECTOR_band']]
assert len(tie_objects)==2
def visible(keys,extra_physical=()):
    names=set(work['fixture_ids'])|set(extra_physical)
    shown={added[k] for k in keys}|set(tie_objects)
    for o in bpy.context.scene.objects:
        if o.type in ['MESH','CURVE']:o.hide_render=o not in shown and o.name.removeprefix(PREFIX) not in names
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
def snap(name,eye,target,scale,scope):
    camera('A8_CAM_WORK_'+name,eye,target,scale);sc.render.filepath=str(CW_OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','sha256':sha(CW_OUT/(name+'.png')),'scope':scope})
basic={'CAM_catalogue_housing'}|{f'wire_{i}' for i in range(4)}
visible(basic|{'cutter'})
snap('work_detail',(-2,46,187),(-14,-24,210),38,'Detached CAM/cradle; green solid-work envelope edges, amber catalogue plug/tie; only local wire staging')
visible(basic|{'cutter','tail_work'})
snap('work_overview',(110,145,230),(-8,-1,168),235,'Full cutter below detached cradle, tail work corridor toward front; no hands or whole harness')
visible(basic|{'cutter'},{'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Yaw_Base','Yaw_Reaction_Link'})
snap('installed_tool_conflict',(92,130,266),(-11,-2,201),132,'Rejected in-place attempt: the same cutter intersects the assembled yaw/body structures')
visible(basic|{'cutter'})
camera('A8_CAM_WORK_final',(-2,46,187),(-14,-24,210),38)
bpy.context.view_layer.update();assert all(geometry_record(o)==before[n] for n,o in physical.items())
sc['independent_unapproved_study']='CAM connector bench tools; main M1.47 unchanged; whole harness incomplete'
bpy.ops.wm.save_as_mainfile(filepath=str(CW_OUT/'review.blend'))
report={'status':'PASS','script_sha256':sha(CW_SCRIPT),'source_candidate_sha256':sha(CW_SOURCE),
        'source_work_report_sha256':sha(CW_OUT/'work_access.json'),'physical_parts_unchanged':len(physical),
        'review_sha256':sha(CW_OUT/'review.blend'),'images':images,'main_applied':False,
        'source_main_sha256':sha(CW_ROOT.parents[3]/'mechanical/mori_v1_2.blend'),'whole_harness':'BLOCKED'}
(CW_OUT/'render_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_WORK_RENDER',len(images),'PASS',flush=True)
