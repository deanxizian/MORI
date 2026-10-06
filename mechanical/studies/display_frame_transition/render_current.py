"""Current-model detail/part views; identical camera to approved comparison."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from render import camera
from monocoque_structure import obj,source_build
here=Path(__file__).parent
load_collections()
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[n].hide_viewport=False
assembled();source_build().materials();bpy.context.view_layer.update()
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1000;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for n in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[n].hide_render=True
o=obj('Display_Frame');o.data.materials.clear();o.data.materials.append(MATS['frame'])
for f in o.data.polygons:f.material_index=0
local={'Display_Frame','Display_PCB','Pitch_Cradle','Pitch_Servo','Yaw_Servo'}|{o.name.removeprefix(PREFIX) for o in parts() if o.name.removeprefix(PREFIX).startswith(('Face_Joint_','LCD_Mount_Screw'))}
manifest={}
for name,visible,loc,target,scale in [('detail',local,(-94,122,306),(-32,28,222),49),('part',{'Display_Frame'},(105,-155,312),(0,28,238),91)]:
 for ob in sc.objects:
  if ob.type=='MESH':ob.hide_render=ob.name.removeprefix(PREFIX) not in visible
 camera('frame_current_'+name,loc,target,scale);sc.render.filepath=str(here/('current_'+name+'.png'));bpy.ops.render.render(write_still=True)
 manifest[name]={'camera_mm':loc,'target_mm':target,'scale_mm':scale,'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
(here/'current_render_manifest.json').write_text(json.dumps({'revision':P['revision'],'views':manifest},indent=2)+'\n')
