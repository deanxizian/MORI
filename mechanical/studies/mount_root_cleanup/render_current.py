"""Actual current geometry; no display-only changes to structural surfaces."""
import sys,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from render import camera
out=Path(__file__).parent
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
show={'Pitch_Cradle','CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R'}|{o.name.removeprefix(PREFIX) for o in parts() if 'CAM_Mount_' in o.name}
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.render.resolution_x=1000;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for n in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[n].hide_render=True
views=[('after_rear',(70,-125,290),(0,-27,242),62,show),('after_front',(55,100,280),(0,-25,240),65,show)]
# Reverse views expose the other retained integral mount roots in the audit.
views += [('shell_inside',(80,-100,0),(0,0,125),170,{'Body_Upper'}),('deck_top',(100,-150,235),(0,-10,108),163,{'Load_Frame'}),('deck_bottom',(85,-130,18),(0,-10,108),163,{'Load_Frame'})]
manifest={}
for name,loc,tgt,scale,visible in views:
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
 camera('mount_'+name,loc,tgt,scale);sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 manifest[name]={'ids':sorted(visible),'camera_mm':loc,'target_mm':tgt,'scale_mm':scale,'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
save_json(out/'render_manifest.json',{'revision':P['revision'],'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'geometry_changes_for_render':'NONE','views':manifest})
