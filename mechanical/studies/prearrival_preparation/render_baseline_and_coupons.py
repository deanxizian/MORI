import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from render import camera
load_collections();sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.background_type='VIEWPORT';sc.display.shading.background_color=(.86,.89,.92);sc.render.film_transparent=False;sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100
if 'coupons' in bpy.data.filepath:
 for c in bpy.data.collections:c.hide_render=False
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=not o.name.startswith(PREFIX+'C0')
 sc.render.resolution_x=1300;sc.render.resolution_y=950
 camera('coupons',(110,-250,450),(68,90,0),360);sc.render.filepath=str(HERE/'jlc_coupons/overview.png')
else:
 assembled();visible={'Head_Front','Head_Rear','Camera_Lens','Camera_PCB','Display_PCB','Eye_L','Eye_R'}
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
 sc.render.resolution_x=950;sc.render.resolution_y=1000
 camera('camera_aperture_baseline',(0,210,274),(0,20,247),98);sc.render.filepath=str(HERE/'camera_aperture_baseline.png')
bpy.ops.render.render(write_still=True)
print('RENDER_REVIEW_COMPLETE',sc.render.filepath,flush=True)
