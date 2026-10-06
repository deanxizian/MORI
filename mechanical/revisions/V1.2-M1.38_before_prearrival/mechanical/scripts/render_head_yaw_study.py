"""Actual Blender placement preview. Separate study; not an assembly release."""
import sys, hashlib, json, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *
from render import camera, line, textlabel

out = ROOT/'studies/yaw_servo_in_head'
report = json.loads((out/'placement_study.json').read_text())
source = ROOT/'mori_v1_2.blend'
assert hashlib.sha256(source.read_bytes()).hexdigest() == report['source_model_sha256']
bpy.context.window.scene = bpy.data.scenes['MORI_V1_Assembly']
load_collections(); assembled(); sc=bpy.context.scene
selected = report['selected_full_sampling']
shaft=bpy.data.objects[PREFIX+'Yaw_Output']
old_tip=Vector((0,0,bounds(shaft)[2][1]))
tip=Vector((0,0,selected['tip_ground_z_mm']))
tr=Matrix.Translation(tip)@Matrix.Rotation(math.radians(selected['clock_deg']),4,'Z')@Matrix.Rotation(math.pi,4,'X')@Matrix.Translation(-old_tip)
material('study_servo',(.015,.48,.64),metallic=.2)
material('annotation',(.04,.63,.8),emission=.5)
for n,group in [('Yaw_Servo','yaw'),('Yaw_Output','body'),('Yaw_Horn','body'),('Yaw_Lock_Screw','body')]:
    o=bpy.data.objects[PREFIX+n];mw=tr@o.matrix_world
    o.parent=bpy.data.objects[PREFIX+('CTRL_Yaw' if group=='yaw' else 'CTRL_Root')]
    o.matrix_world=mw;o['group']=group;o['export_candidate']=False
    o['verification_status']='PLACEMENT_ONLY_MOUNTING_NOT_DESIGNED'
    if n=='Yaw_Servo':
        o.data.materials.clear();o.data.materials.append(MATS['study_servo'])
bpy.context.view_layer.update()
hide={'Body_Upper','Body_Lower','Head_Front','Face_Mask','Face_Protector','Display_Module','Display_PCB','Display_Frame','Display_Connector','Eye_L','Eye_R','Power_Module'}
for o in sc.objects:
    if o.get('role') in ['part','routing','display_content']:
        o.hide_render=o.name.removeprefix(PREFIX) in hide
        o.hide_set(o.hide_render)
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[n].hide_render=True;COLS[n].hide_viewport=True
COLS['ANNOTATIONS'].hide_render=False;COLS['ANNOTATIONS'].hide_viewport=False
ground=bpy.data.objects[PREFIX+'Studio_Ground'];ground.hide_render=True
box_bounds=report['removed_from_body_case_bounds_xyz_mm']
corners=[Vector((box_bounds[0][i],box_bounds[1][j],box_bounds[2][k])) for i in range(2) for j in range(2) for k in range(2)]
for i,a in enumerate(corners):
    for j,b in enumerate(corners):
        if i<j and sum(abs(a[k]-b[k])>1e-4 for k in range(3))==1:line('study_old_servo_envelope',a,b,.35)
cam=camera('head_yaw_placement',(270,480,290),(0,0,185),245)
# Labels and leaders are annotations, not invented load-carrying structures.
def label(name,txt,loc,size):
    o=textlabel(name,txt,loc,size);o.rotation_euler=cam.rotation_euler.copy();o['role']='annotation'
    # Orthographic overlay: moving toward the camera preserves projection and
    # prevents the annotation being hidden by the actual model.
    o.location+=(cam.location-Vector((0,0,185))).normalized()*180
label('study_title','YAW SERVO IN HEAD / PLACEMENT STUDY',(-15,30,293),4.2)
label('study_new_servo','YAW CASE / PITCH-INDEPENDENT',(59,38,216),3.2)
line('study_servo_leader',(6,10,208),(53,29,214),.25)
label('study_old_space','OLD SERVO POSITION',(58,42,149),3.4)
line('study_space_leader',(20,4,141),(49,30,148),.25)
label('study_limit','FIXED REACTION LINK + MOUNTS: NOT DESIGNED',(0,35,83),3.5)
label('study_screen','LCD HIDDEN FOR VIEW / INCLUDED IN COLLISION CHECK',(0,35,76),3)
sc['study_status']='Placement only; missing body-fixed reaction link, servo mounting and bearing-support redesign. Not printable assembly.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.overlay.show_extras=False
            area.spaces.active.region_3d.view_distance=250
            area.spaces.active.region_3d.view_location=(0,0,190)
bpy.ops.object.select_all(action='DESELECT')
servo=bpy.data.objects[PREFIX+'Yaw_Servo'];servo.select_set(True);bpy.context.view_layer.objects.active=servo
bpy.ops.wm.save_as_mainfile(filepath=str(out/'yaw_servo_in_head_PLACEMENT_ONLY.blend'))
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.resolution_x=1100;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
sc.render.filepath=str(out/'placement_preview.png');bpy.ops.render.render(write_still=True)
save_json(out/'preview_provenance.json',{'source_model_sha256':report['source_model_sha256'],
    'study_blend_sha256':hashlib.sha256((out/'yaw_servo_in_head_PLACEMENT_ONLY.blend').read_bytes()).hexdigest(),
    'render_sha256':hashlib.sha256((out/'placement_preview.png').read_bytes()).hexdigest(),
    'actual_blender_render':True,'LCD_hidden_for_view_only':True,'original_released_model_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==report['source_model_sha256'],
    'status':'PLACEMENT_ONLY_NOT_A_COMPLETE_ASSEMBLY'})
print('HEAD_YAW_PREVIEW_COMPLETE',flush=True)
