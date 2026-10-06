"""Show board-only seating and the remaining straight-driver obstruction."""
from pathlib import Path
import sys,json,hashlib
RB_SCRIPT=Path(__file__).resolve();A8=RB_SCRIPT.parent;OUT=A8/'cam_board_last';ROOT=A8.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(ROOT/'mechanical/scripts/vendor'))
from common import *
from render import camera
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SOURCE=A8/'cam_wired_cradle/review.blend';assert Path(bpy.data.filepath)==SOURCE
screen=json.loads((OUT/'screen.json').read_text());check=json.loads((OUT/'verification.json').read_text())
assert screen['status']=='PASS' and check['status']=='BLOCKED'
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
show={'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Pitch_Cradle','CAM_Mainboard'}|{n for n in physical if n.startswith(('CAM_Mount_','Onboard_MIC_','Head_Cradle_Insert_'))}
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE']:o.hide_render=o.name.removeprefix(PREFIX) not in show
# Only presentation copies receive translations; source matrices stay intact.
copies={}
for n in ['CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R']:
    original=physical[n];copy=original.copy();copy.name='A8_BOARD_LAST_'+n
    bpy.context.scene.collection.objects.link(copy);copy.parent=None;copy.matrix_world=original.matrix_world.copy()
    copy['study_owner']='CAM_BOARD_LAST';copies[n]=copy;original.hide_render=True
extras=[]
def mesh(name,path,vkey='vertices_mm',fkey='triangles',color=(.95,.55,.12)):
    data=np.load(path);d=bpy.data.meshes.new(name);d.from_pydata(data[vkey].tolist(),[],data[fkey].tolist());d.update()
    o=bpy.data.objects.new('A8_BOARD_LAST_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_BOARD_LAST_MAT_'+name,color,roughness=.55));o['study_owner']='CAM_BOARD_LAST';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED';extras.append(o);return o
plug=mesh('catalogue_housing',A8/'cam_pitch_port/allocation_meshes.npz','housing_v','housing_f')
tool=mesh('straight_driver_blade',OUT/'straight_driver_blade.npz',color=(.9,.08,.06))
curves=np.load(OUT/'curves.npz');wires=[];colors=[(.06,.57,.66),(.9,.23,.07),(.28,.62,.1),(.63,.25,.77)]
def pose(h,tool_visible):
    for n,o in copies.items():o.matrix_world=Matrix.Translation((0,0,h))@physical[n].matrix_world
    plug.matrix_world=Matrix.Translation((0,0,h));tool.hide_render=not tool_visible
    for n,o in physical.items():
        if n.startswith('CAM_Mount_Screw_'):o.hide_render=bool(h)
    for o in wires:bpy.data.objects.remove(o,do_unlink=True)
    wires.clear()
    for i in range(4):
        pts=curves[f'seating_plug{h:g}_board{h:g}_slot{i}']
        d=bpy.data.curves.new(f'BOARD_LAST_WIRE{i}','CURVE');d.dimensions='3D';d.bevel_depth=.3302;d.bevel_resolution=3;d.use_fill_caps=True
        s=d.splines.new('POLY');s.points.add(len(pts)-1)
        for q,p in zip(s.points,pts):q.co=(*p,1)
        o=bpy.data.objects.new(f'A8_BOARD_LAST_wire{i}',d);bpy.context.scene.collection.objects.link(o)
        d.materials.append(material(f'A8_BOARD_LAST_WIRE_MAT{i}',colors[i],roughness=.5));wires.append(o)
        o['study_owner']='CAM_BOARD_LAST';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    bpy.context.view_layer.update()
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';images=[]
for label,h,tool_visible,eye,target,scale in [
    ('board_raised6',6.,False,(-105,130,313),(-5,-3,235),111),
    ('screw_tool_obstruction',0.,True,(-106,105,309),(-17,-2,223),85)]:
    pose(h,tool_visible);camera('A8_BOARD_LAST_'+label,eye,target,scale);sc.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':label+'.png','sha256':sha(OUT/(label+'.png')),'CAM_lift_mm':h,'tool_visible':tool_visible})
pose(0.,False)
for n,o in copies.items():o.hide_render=True;physical[n].hide_render=False
bpy.context.view_layer.update();assert all(geometry_record(o)==before[n] for n,o in physical.items())
sc['independent_unapproved_study']='CAM board-only seating; straight tool to lower-left screw blocked by Pitch_Servo. Full harness incomplete.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'review.blend'))
(OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(RB_SCRIPT),'source_main_sha256':screen['main_source_sha256'],
    'source_candidate_sha256':sha(SOURCE),'screen_sha256':sha(OUT/'screen.json'),'verification_sha256':sha(OUT/'verification.json'),
    'physical_parts_preserved_unchanged':len(physical),'review_sha256':sha(OUT/'review.blend'),'images':images,
    'scope':'Independent rendering; candidate motion is not a complete assembly sequence','main_applied':False,'whole_harness':'BLOCKED'},ensure_ascii=False,indent=2)+'\n')
print('CAM_BOARD_LAST_RENDER_DONE',len(images),flush=True)
