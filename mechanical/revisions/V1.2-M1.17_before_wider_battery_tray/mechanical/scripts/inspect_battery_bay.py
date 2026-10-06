"""Read-only local assembly views, separate from released render manifests."""
import sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args(args)
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
bpy.data.objects[PREFIX+'Studio_Ground'].hide_render=True
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=sc.render.resolution_y=1000;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for view,visible in [('bay',{'Load_Frame','Battery_Tray','Battery','Drive_Bridge','Yaw_Base','Speaker','Speaker_Mount'}),('frame',{'Load_Frame'}),('tray',{'Battery_Tray','Battery'})]:
    for o in sc.objects:
        if o.get('role') in ['part','routing','display_content']:o.hide_render=o.name.removeprefix(PREFIX) not in visible
    camera('inspect_battery_bay',(135,490,255),(0,0,92),165)
    sc.render.filepath=str(out/(view+'.png'));bpy.ops.render.render(write_still=True)
