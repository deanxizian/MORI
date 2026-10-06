"""Current actual Blender geometry views of the new board/socket stack."""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera
load_collections();assembled();bpy.context.view_layer.update()
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.display.shading.light='STUDIO';sc.display.shading.show_cavity=True
sc.render.resolution_x=1400;sc.render.resolution_y=1050;sc.render.resolution_percentage=100;sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
out=ROOT/'renders/p5r7';out.mkdir(exist_ok=True)
groups=[('boards',{'MCU_Motion','MCU_Carrier','Socket_AC','Socket_BD','Socket_E','E_Straight_Header','Rear_Interface_PCB','Load_Frame','Yaw_Base'},(140,-190,235),(0,-28,132),132),('stack',{'MCU_Motion','MCU_Carrier','Socket_AC','Socket_BD','Socket_E','E_Straight_Header'},(75,-180,156),(-7,-44,130),64)]
for name,visible,eye,target,scale in groups:
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=True
    for n in visible:bpy.data.objects[PREFIX+n].hide_render=False
    camera(name,eye,target,scale);sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
save_json(ROOT/'reports/p5r7_views.json',dict(revision=P['revision'],source_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),files=['renders/p5r7/boards.png','renders/p5r7/stack.png'],scope='Exact current assembled vertices; visibility and cameras only, no presentation displacement or source save.'))
