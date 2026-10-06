"""Read-only camera composition review on the current animation."""
import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path(__file__).resolve().parent
sc=bpy.data.scenes['MORI_Assembly_Animation'];bpy.context.window.scene=sc;sc.frame_set(1667)
cam=sc.camera
sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
for o in sc.objects:
 if 'Speaker' in o.get('source_object','') or 'Rear_Interface_PCB' in o.get('source_object',''):
  print(o.name,list(o.matrix_world.translation),o.hide_render,flush=True)
for name,loc in [('high_oblique',(450,0,820)),('overhead',(0,0,900)),('opposite',(-450,0,820))]:
 cam.location=loc;cam.rotation_euler=(Vector((0,0,102))-cam.location).to_track_quat('-Z','Y').to_euler()
 sc.render.filepath=str(out/('bench_'+name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(600,0,680);cam.rotation_euler=(Vector((0,0,102))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='PERSP';cam.data.lens=35;factor=(3*cam.data.sensor_width/cam.data.lens)/cam.data.ortho_scale
for o in sc.objects:
 if o.parent==cam and o.type=='FONT':
  o.location.x*=factor;o.location.y*=factor;o.scale*=factor
sc.render.filepath=str(out/'bench_perspective.png');bpy.ops.render.render(write_still=True)
import math
sc.frame_set(1667)
for name,x,angle in [('Front_Shell',-125,math.pi),('Rear_Shell',125,0)]:
 o=sc.objects['MORI_ANIM__'+name];o.location=(x,0,0);o.rotation_euler.z=angle;o.keyframe_insert(data_path='location',frame=1667)
cam.data.type='ORTHO';cam.data.ortho_scale=600
cam.location=(220,700,350);cam.rotation_euler=(Vector((0,0,102))-cam.location).to_track_quat('-Z','Y').to_euler()
for o in sc.objects:
 if o.parent==cam and o.type=='FONT':
  o.location.x*=600/790/factor;o.location.y*=600/790/factor;o.scale*=600/790/factor
bpy.context.view_layer.update()
sc.render.filepath=str(out/'bench_rotated_display.png');bpy.ops.render.render(write_still=True)
