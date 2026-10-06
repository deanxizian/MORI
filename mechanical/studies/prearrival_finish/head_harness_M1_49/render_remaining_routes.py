"""Show the verified five-line subassembly and its conflicts with old CAM paths."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes'
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import *
from render import camera
ctx=Context();base=OUT/'five_before_cam_reroute'
report=json.loads((base/'lower_five_screen.json').read_text());assert report['status']=='PASS'
for f,h in {**report['sources'],**report['inputs']}.items():assert sha(PROJECT/f)==h,f
data=np.load(base/'lower_five_candidates.npz');assert sha(base/'lower_five_candidates.npz')==report['curve_sha256']
cam=np.load(HERE/'cam_joined_candidates.npz');cam_report=json.loads((HERE/'cam_joined_verification.json').read_text())
assert sha(HERE/'cam_joined_candidates.npz')==cam_report['curve_sha256']
tag='MORI_WIRE_JOINT_STUDY_149__';new=[];old=[]
for o in list(bpy.data.objects):
    if o.name.startswith(tag):bpy.data.objects.remove(o,do_unlink=True)
def wire(label,points,radius,color,scope):
    cu=bpy.data.curves.new(tag+label,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
    for v,p in zip(sp.points,points):v.co=(*p,1)
    ob=bpy.data.objects.new(tag+label,cu);bpy.context.scene.collection.objects.link(ob);ob.color=color
    ob['category']='PLACEHOLDER';ob['data_status']='ASSUMED';ob['robot_part']=False
    ob['scope']=scope;ob['full_harness']='BLOCKED';ob['not_cut_length']=True
    return ob
palette=[(.04,.45,.58,1),(.03,.64,.52,1),(.22,.67,.81,1),(.5,.26,.76,1),(.7,.39,.75,1)]
for row,color in zip(sorted(report['selected'],key=lambda r:r['endpoint']),palette):
    new.append(wire(row['endpoint'],data[row['endpoint']+'_y0'],.5842,color,'Five-line lower subassembly only; CAM body routing excluded and must be redesigned'))
for pin in range(1,5):old.append(wire('OLD_CAM_pin'+str(pin),cam[f'pin{pin}_y0_p0'],.3302,(.85,.18,.1,1),'Old independent CAM route, visibly conflicts with five-line lower proposal; NOT a combined assembly'))
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT'
scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(.81,.85,.87);scene.view_settings.view_transform='Standard'
scene.render.film_transparent=False;scene.render.resolution_x=1280;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';records=[]
def view(name,keep,show_old,eye,target,scale):
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for n,s in ctx.ss.items():
        s.o.hide_render=n not in keep
        if s.o.get('category')=='PRINTABLE':s.o.color=(.54,.62,.64,1)
    for o in new:o.hide_render=False;o.hide_set(False)
    for o in old:o.hide_render=not show_old;o.hide_set(not show_old)
    cam_obj=camera('Joint149_'+name,eye,target,scale);cam_obj.data.clip_start=.1
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    records.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png')),visible_native_parts=sorted(keep),old_CAM_shown=show_old))
boards={'Power_Module','MCU_Carrier','MCU_Motion','Load_Frame','Yaw_Bearing','CAM_Mainboard','Yaw_Servo','Pitch_Servo'}
view('five_lower_overview',boards|{'Yaw_Base','Yaw_Anti_Lift_Keeper','Pitch_Yoke'},False,(190,-270,260),(0,-4,169),155)
view('five_lower_exposed',{'Power_Module','MCU_Carrier','Yaw_Bearing'},False,(-170,-220,245),(0,-12,166),128)
view('old_CAM_conflict_overlay',{'Power_Module','MCU_Carrier','Yaw_Bearing'},True,(-160,-220,280),(0,-15,141),92)
bpy.context.view_layer.update();ctx.assert_unchanged()
dest=OUT/'MORI_M1_49_wire_joint_study.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest));ctx.assert_unchanged()
manifest=dict(status='PASS',scope='Preview generation only; overlay is explicitly incompatible and not a finished harness',
    source_blend_sha256=ctx.source_hash,source_report_sha256=sha(base/'lower_five_screen.json'),
    images=records,blend_sha256=sha(dest),main_changed=False,full_harness='BLOCKED',script_sha256=sha(Path(__file__)))
(OUT/'render_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
