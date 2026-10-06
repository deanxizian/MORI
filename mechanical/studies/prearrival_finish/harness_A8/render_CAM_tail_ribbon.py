"""Show the temporary tail alongside unchanged candidate robot geometry."""
from pathlib import Path
import sys,json,hashlib
RR_SCRIPT=Path(__file__).resolve();RR_ROOT=RR_SCRIPT.parent;RR_OUT=RR_ROOT/'cam_tail_ribbon'
sys.path.insert(0,str(RR_ROOT.parents[3]/'mechanical/scripts'))
sys.path.insert(0,str(RR_ROOT.parents[3]/'mechanical/scripts/vendor'))
from common import *
from render import camera
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
RR_SOURCE=RR_ROOT/'cam_wired_cradle/review.blend'
assert Path(bpy.data.filepath)==RR_SOURCE
record=json.loads((RR_OUT/'inner_corridor.json').read_text())
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
names={'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Pitch_Cradle','CAM_Mainboard'}|{
    n for n in physical if n.startswith(('CAM_Mount_','Head_Cradle_Insert_','Onboard_MIC_','Head_Pitch_Ear_','Head_Yaw_Ear_'))}
for o in bpy.context.scene.objects:
    if o.type not in ['MESH','CURVE']:continue
    old_extra=o.name.startswith(('A8_CAM_INSERT_wire','A8_CAM_INSERT_catalogue_housing','A8_CAM_INSERT_yaw_tie','A8_CAM_CONNECTOR_'))
    o.hide_render=o.name.removeprefix(PREFIX) not in names and not old_extra
a=np.load(RR_OUT/'inner_tail_34.npz')
mesh=bpy.data.meshes.new('A8_TAIL_RIBBON_GEOMETRY');mesh.from_pydata(a['vertices_mm'].tolist(),[],a['triangles'].tolist());mesh.update()
tail=bpy.data.objects.new('A8_TEMPORARY_CAM_TIE_TAIL',mesh);bpy.context.scene.collection.objects.link(tail)
mesh.materials.append(material('A8_TIE_TEMPORARY',(.98,.53,.08),roughness=.5))
tail['study_owner']='CAM_TAIL_RIBBON';tail['part_class']='PLACEHOLDER';tail['data_status']='ASSUMED'
tail['scope']='Temporary free-tail route,110mm allocation; catalogue upper cross-section1.3x2.7mm; not a finished-cut length or robot part'
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
for name,eye,target,scale in [
    ('tail_overview',(-145,160,330),(-12,20,228),146),
    ('tail_top',(-13,17,420),(-13,17,220),146),
    ('tail_local',(-113,79,280),(-20,-4,221),92)]:
    camera('A8_TAIL_'+name,eye,target,scale);sc.render.filepath=str(RR_OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','sha256':sha(RR_OUT/(name+'.png'))})
assert all(geometry_record(o)==before[n] for n,o in physical.items())
sc['independent_unapproved_study']='Temporary CAM tie-tail routing. Full harness/assembly remains BLOCKED.'
camera('A8_TAIL_saved',(-145,160,330),(-12,20,228),146)
bpy.ops.wm.save_as_mainfile(filepath=str(RR_OUT/'review.blend'))
(RR_OUT/'render_manifest.json').write_text(json.dumps({
    'status':'PASS','script_sha256':sha(RR_SCRIPT),'source_main_sha256':record['source_main_sha256'],
    'source_candidate_sha256':sha(RR_SOURCE),'screen_sha256':sha(RR_OUT/'inner_corridor.json'),
    'tail_sha256':sha(RR_OUT/'inner_tail_34.npz'),'review_sha256':sha(RR_OUT/'review.blend'),
    'physical_parts_preserved_unchanged':len(physical),'images':images,
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
print('CAM_TAIL_RENDER_DONE',len(images),flush=True)
