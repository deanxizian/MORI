import sys,hashlib,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from render import camera
a=argparse.ArgumentParser();a.add_argument('--views',default='all');a.add_argument('--tag',default='after');args=a.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
out=Path(__file__).parent;bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];sc=bpy.context.scene;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.render.resolution_x=1050;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
cam={'CAM_Mainboard','Pitch_Cradle','Onboard_MIC_L','Onboard_MIC_R'}|{o.name.removeprefix(PREFIX) for o in parts() if 'CAM_Mount_' in o.name}
views={'cam_mount':(cam,(50,95,285),(0,-20,237),67),'battery':({'Battery','Battery_Tray','Battery_Strap','Battery_Pad_Top'},(90,110,155),(0,0,88),110),
 'camera_pocket':({'Display_Frame','Camera_PCB','Camera_Lens'},(30,80,293),(0,28,266),24),
 'camera_rear':({'Head_Front','Camera_PCB','Camera_Lens'},(28,-30,285),(0,29,267),26),
 'head':({o.name.removeprefix(PREFIX) for o in parts() if o.get('group') in ['pitch','yaw'] and o.name.removeprefix(PREFIX) not in ['Head_Front','Head_Rear','Head_Lower_Guard']},(160,195,377),(0,0,226),151)}
manifest={}
for name,(visible,loc,target,scale) in views.items():
 if args.views!='all' and name not in args.views.split(','):continue
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
 camera('completion_'+name,loc,target,scale);sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 manifest[name]={'camera_mm':loc,'target_mm':target,'ortho_scale_mm':scale,'visible_ids':sorted(visible),'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
save_json(out/'render_manifest.json',{'revision':P['revision'],'source_blend':bpy.data.filepath,'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'geometry_changes_for_render':'NONE','views':manifest})
