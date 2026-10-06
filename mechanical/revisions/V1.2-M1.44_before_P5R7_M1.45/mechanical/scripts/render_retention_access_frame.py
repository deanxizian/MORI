"""Render the actual animation's 60-degree keeper access pose; no save."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from assembly_animation import SCENE_NAME
manifest=json.loads((ROOT/'animation/manifest.json').read_text())
stage=next(s for s in manifest['stages'] if s['source_step']==22)
scene=bpy.data.scenes[SCENE_NAME];bpy.context.window.scene=scene
scene.frame_set(stage['start']+99);bpy.context.view_layer.update()
scene.render.image_settings.media_type='IMAGE';scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(ROOT/'studies/head_axial_retention/adopted/access_60deg.png')
bpy.ops.render.render(write_still=True)
print('RETENTION_ACCESS_FRAME',scene.frame_current,flush=True)
