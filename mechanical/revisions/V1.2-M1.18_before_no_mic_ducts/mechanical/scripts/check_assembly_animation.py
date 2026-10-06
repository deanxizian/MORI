"""Read-back checks of the editable animation and the actual encoded video."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from assembly_animation import ANIM_OWNER,AP,OUT,SCENE_NAME
source_scene=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=source_scene
bpy.context.view_layer.update()
source_matrices={o.name:o.matrix_world.copy() for o in source_scene.objects}
scene=bpy.data.scenes[SCENE_NAME];bpy.context.window.scene=scene
report=json.loads((OUT/'manifest.json').read_text())
actors={o.name.removeprefix(AP):o for o in scene.objects if o.get('presentation_actor')}
scene.frame_set(scene.frame_end);bpy.context.view_layer.update()
errors={}
for name,o in actors.items():
    src=bpy.data.objects[o['source_object']]
    assert o.data is src.data
    errors[name]=float(np.max(np.abs(np.asarray(o.matrix_world)-np.asarray(source_matrices[src.name]))))
    assert not o.hide_render and not o.hide_viewport
assert set(actors)==set(report['part_stages'])
assert max(errors.values())<.0001
assert len(scene.timeline_markers)==18
assert all(o.animation_data and o.animation_data.action for o in actors.values())
assert all(o.get('export_candidate') is False for o in actors.values())
source=Path(report['source_blend']);assert hashlib.sha256(source.read_bytes()).hexdigest()==report['source_blend_sha256']
native=[]
for s in report['stages']:
    scene.frame_set(s['end']);bpy.context.view_layer.update()
    native.append({'step':s['index'],'frame':s['end'],'camera':scene.camera.name,'visible_actors':sum(not o.hide_render for o in actors.values())})
    assert scene.camera.name==AP+f'Camera_{s["index"]:02d}'
video=OUT/'MORI_assembly.mp4'
assert video.exists() and video.stat().st_size>100_000
clip=bpy.data.movieclips.load(str(video));assert list(clip.size)==report['resolution'];assert clip.frame_duration==scene.frame_end
assert abs(clip.fps-report['fps'])<.01
result={'status':'PASS','source_is_unchanged':True,'readback_actor_count':len(actors),'all_actor_meshes_match_source':True,'final_matrix_max_error_mm':max(errors.values()),'editable_object_actions':len(actors),'timeline_markers':len(scene.timeline_markers),'stage_camera_and_visibility':native,'video':{'file':'MORI_assembly.mp4','bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'decoded_dimensions_px':list(clip.size),'decoded_frames':clip.frame_duration,'decoded_fps':clip.fps,'duration_seconds':clip.frame_duration/clip.fps},'continuous_collision_check':'NOT_TESTED','physical_assembly_process':'NOT_QUALIFIED'}
save_json(OUT/'validation.json',result)
report['rendered_video']=True;report['video']=result['video'];report['readback_validation']='animation/validation.json';report['animation_blend_sha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest();save_json(OUT/'manifest.json',report)
print('ANIMATION_VALIDATED',json.dumps(result,ensure_ascii=False))
