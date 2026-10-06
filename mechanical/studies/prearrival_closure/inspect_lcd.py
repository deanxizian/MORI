import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
from render import camera
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={n:Solid(bpy.data.objects[PREFIX+n]) for n in ['Display_PCB','Display_Frame']}
m=ss['Display_PCB'].m^ss['Display_Frame'].m
data={'scene':bpy.context.scene.name,'volume':m.volume(),'overlap_bbox':m.bounding_box(),'parts':{}}
for n,s in ss.items():
    o=s.o;data['parts'][n]=dict(bounds=[s.lo.tolist(),s.hi.tolist()],properties={k:str(v)[:600] for k,v in o.items() if 'validation' in k or 'source' in k},matrix=[list(r) for r in o.matrix_world])
    if o.get('validation_proxy'):
        p=bpy.data.objects[o['validation_proxy']];data['parts'][n]['proxy_matrix']=[list(r) for r in p.matrix_world];data['parts'][n]['proxy_parent']=p.parent.name if p.parent else None
(HERE/'lcd_diagnostic.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(json.dumps(data,ensure_ascii=False),flush=True)
for o in bpy.context.scene.objects:o.hide_render=o not in [s.o for s in ss.values()]
q=m.to_mesh();o=mesh('CLOSURE_LCD_overlap',q.vert_properties[:,:3],q.tri_verts);o.hide_render=False;o.color=(1,.1,.02,1)
for n,s in ss.items():s.o.color=(.4,.6,.7,1) if n=='Display_Frame' else (.8,.8,.8,1)
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='OBJECT';sc.display.shading.show_cavity=True
sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
camera('closure_lcd',(95,-160,320),(0,32,233),83);sc.render.filepath=str(HERE/'lcd_diagnostic.png');bpy.ops.render.render(write_still=True)
