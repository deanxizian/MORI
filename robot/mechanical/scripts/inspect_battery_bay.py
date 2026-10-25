"""Read-only local assembly views, separate from released render manifests."""
import sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--measure-only',action='store_true');a=p.parse_args(args)
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
from validate import Solid
import hashlib
frame=Solid(bpy.data.objects[PREFIX+'Load_Frame']);tray=Solid(bpy.data.objects[PREFIX+'Battery_Tray']);rows=[]
for sign in [-1,1]:
    for x in [41,43,44]:
        for y in [-18,-12,0,12,18]:
            hits=frame.m.ray_cast([sign*x,y,float(tray.lo[2])+.1],[sign*x,y,float(tray.lo[2])-10])
            seat=float(hits[0].position[2]) if hits else None
            rows.append({'x_mm':sign*x,'y_mm':y,'tray_bottom_z_mm':float(tray.lo[2]),'frame_seat_z_mm':seat,'vertical_gap_mm':None if seat is None else float(tray.lo[2])-seat})
save_json(out/'bearing_measurement.json',{'source_blend':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'method':'Actual frame triangle-solid downward rays at30 points under tray floor, excluding existing screw bores','samples':rows})
if a.measure_only:raise SystemExit(0)
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
bpy.data.objects[PREFIX+'Studio_Ground'].hide_render=True
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=sc.render.resolution_y=1000;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for view,visible in [('bay',{'Load_Frame','Battery_Tray','Battery','Drive_Bridge','Yaw_Base','Speaker','Speaker_Mount'}),('frame',{'Load_Frame'}),('tray',{'Battery_Tray','Battery'})]:
    for o in sc.objects:
        if o.get('role') in ['part','routing','display_content']:o.hide_render=o.name.removeprefix(PREFIX) not in visible
    camera('inspect_battery_bay',(135,490,255),(0,0,92),165)
    sc.render.filepath=str(out/(view+'.png'));bpy.ops.render.render(write_still=True)
