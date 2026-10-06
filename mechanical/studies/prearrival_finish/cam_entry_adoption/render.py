"""Render the current saved CAM board; no substituted candidate geometry."""
from pathlib import Path
import hashlib,json,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import bpy,np,P,PREFIX,load_collections,assembled,COLS,D
from render import camera
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'mechanical/mori_v1_2.blend';source_hash=sha(source)
assert Path(bpy.data.filepath)==source and P['revision']=='V1.2-M1.50'
load_collections()
for col in COLS.values():col.hide_viewport=False;col.hide_render=False
assembled();bpy.context.view_layer.update()
scene=bpy.context.scene
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True;o.hide_set(True)
board=bpy.data.objects[PREFIX+'CAM_Mainboard'];board.hide_render=False;board.hide_set(False)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='MATERIAL'
scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=False
scene.display.shading.background_type='WORLD';scene.world.color=(.92,.94,.95)
scene.view_settings.view_transform='Standard';scene.render.resolution_x=1200
scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
center=np.array(P['layout']['cam_board_center_from_head_mm']);center[2]+=D['head_z']
views=[('camera_entry',[-.06,-24.8,226.76],[5,-24,15],21),
       ('display_entry',[-15.56,-21.2,234.81],[-22,18,10],18),
       ('SD',center,[0,-100,0],44),('IC',center,[0,100,0],44)]
images=[]
for label,target,offset,scale in views:
    target=np.asarray(target);camera('MORI_CAM_ENTRY_CURRENT_'+label,target+offset,target,scale)
    file=OUT/(label+'.png');scene.render.filepath=str(file);bpy.ops.render.render(write_still=True)
    images.append(dict(file=str(file.relative_to(ROOT)),sha256=sha(file),target_mm=target.tolist(),eye_offset_mm=offset,ortho_scale_mm=scale))
assert sha(source)==source_hash
(OUT/'render_manifest.json').write_text(json.dumps(dict(status='PASS',revision=P['revision'],
    source_blend_sha256=source_hash,source_changed=False,geometry_substitution=False,
    images=images,script_sha256=sha(Path(__file__))),ensure_ascii=False,indent=2)+'\n')
print('CAM_ENTRY_CURRENT_RENDER_PASS',flush=True)
