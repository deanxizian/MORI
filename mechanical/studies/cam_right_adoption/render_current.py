"""Before/after from native pre-adoption and current meshes, no source save."""
from pathlib import Path
import sys,hashlib
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import rigidtr

assert P['revision']=='V1.2-M1.54'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=ROOT/'mori_v1_2.blend';digest=sha(source)
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
native={o.name.removeprefix(PREFIX):o for o in parts()}
scene=bpy.data.scenes.new('CAM_right_current_review');bpy.context.window.scene=scene
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=1000
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('CAM_right_review_world');scene.world.color=(.08,.09,.11)
camera_data=bpy.data.cameras.new('CAM_right_review_camera');camera=bpy.data.objects.new('CAM_right_review_camera',camera_data)
scene.collection.objects.link(camera);camera_data.type='ORTHO';camera_data.clip_start=.1;camera_data.clip_end=1000;scene.camera=camera
moving=P['cam_orientation']['changed_existing_ids'];created=[];files=[]
head=['Pitch_Cradle','Pitch_Yoke','Pitch_Servo','Pitch_Output','Yaw_Servo',*moving]
head+=sorted(n for n in native if n.startswith(('CAM_Mount_','Pitch_Servo_','Yaw_Servo_')))
for name,before,pose in [('before',True,0),('current',False,0),('current_pitch25',False,25),('board_face',False,0)]:
    for ob in created:bpy.data.objects.remove(ob,do_unlink=True)
    created=[];visible=moving if name=='board_face' else head
    for n in visible:
        src=native[n];ob=src.copy();ob.data=src.data.copy();ob.parent=None;ob.matrix_world=src.matrix_world.copy();ob.hide_render=False;scene.collection.objects.link(ob)
        if before and n in moving:
            original=np.load(ROOT/('input_assets/M1_53_'+n+'_visual_before_right.npz'))['vertices_mm']
            inv=ob.matrix_world.inverted()
            for v,xyz in zip(ob.data.vertices,original):v.co=inv@Vector(xyz)
            ob.data.update()
        if pose and src.get('group')=='pitch':ob.matrix_world=rigidtr(0,pose)@ob.matrix_world
        created.append(ob)
    if name=='board_face':location=(0,150,235);target=(0,-23,235);scale=49
    else:location=(94,118,287);target=(0,-9,237);scale=113
    camera.location=location;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.ortho_scale=scale
    scene.render.filepath=str(HERE/(name+'.png'));bpy.ops.render.render(write_still=True)
    files.append(dict(file=name+'.png',sha256=sha(HERE/(name+'.png')),baseline=before,pitch_deg=pose))
assert sha(source)==digest
save_json(HERE/'render_manifest.json',dict(revision=P['revision'],source_blend_sha256=digest,images=files,
    source_unchanged=True,render_kind='Native unscaled geometry, historical CAM vertices only in before image; no illustrative plug added'))
