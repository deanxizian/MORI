import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from render import camera
out=Path(__file__).parent;bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];sc=bpy.context.scene;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.resolution_x=1100;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
cam={'CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R'}
views={'cam_sd':(cam,(22,-95,278),(0,-23,235),49),'cam_ic':(cam,(-23,80,272),(0,-23,235),49),'camera':({'Camera_PCB','Camera_Lens'},(16,72,293),(0,30,267),16),'lcd_back':({'Display_PCB'},(65,-80,298),(0,45,230),67),'head':({o.name.removeprefix(PREFIX) for o in parts() if o.get('group') in ['pitch','yaw'] and o.name.removeprefix(PREFIX) not in ['Head_Front','Head_Rear','Head_Lower_Guard']},(160,195,377),(0,0,226),151),'camera_fit':({'Display_Frame','Camera_PCB','Camera_Lens'},(30,94,293),(0,28,266),27)}
manifest={}
for name,(visible,loc,target,scale) in views.items():
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
 camera('waveshare_'+name,loc,target,scale);sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 manifest[name]={'camera_mm':loc,'target_mm':target,'ortho_scale_mm':scale,'visible_ids':sorted(visible),'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
save_json(out/'render_manifest.json',{'revision':P['revision'],'source_blend':bpy.data.filepath,'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'geometry_changes_for_render':'NONE','views':manifest})
