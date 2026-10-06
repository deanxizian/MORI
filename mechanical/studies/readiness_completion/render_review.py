import sys,hashlib,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from render import camera
a=argparse.ArgumentParser();a.add_argument('--views',default='all');a.add_argument('--tag',default='after');args=a.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
out=Path(__file__).parent;bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];sc=bpy.context.scene;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.render.resolution_x=1050;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
head={o.name.removeprefix(PREFIX) for o in parts() if o.get('group') in ['pitch','yaw']}
views={
 'head_assembled':(head|{'Eye_L','Eye_R'},(150,190,350),(0,0,240),135),
 'head_recess':({'Head_Front','Pitch_Cradle','Head_Cradle_Screw_1','Head_Cradle_Insert_1'},(110,80,320),(46.75,3.5,253),35),
 'LCD_rear':({'Display_Frame','Display_PCB','LCD_Mount_Screw_0','LCD_Mount_Screw_1','LCD_Mount_Screw_2'},(55,-120,270),(0,31,233),83),
 'shell_inside':({'Head_Front','Head_Cradle_Screw_1','Head_Cradle_Screw_-1','Head_Seam_Insert_1','Head_Seam_Insert_-1'},(100,-160,300),(0,12,237),132),
 'rear_closed':({'Body_Upper','USB_Receptacle'},(50,-220,190),(0,-75,135),72)}
manifest={}
for name,(visible,loc,target,scale) in views.items():
 if args.views!='all' and name not in args.views.split(','):continue
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
 camera('completion_'+name,loc,target,scale);sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 manifest[name]={'camera_mm':loc,'target_mm':target,'ortho_scale_mm':scale,'visible_ids':sorted(visible),'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
save_json(out/'render_manifest.json',{'revision':P['revision'],'source_blend':bpy.data.filepath,'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'geometry_changes_for_render':'NONE','views':manifest})
