"""Noncanonical exterior-only experiments; same sphere/shell/wheel functions, no saved alternate truth."""
import sys,json,math,bpy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as c
import build as b
from render import camera
out=c.ROOT/'renders/variants';out.mkdir(parents=True,exist_ok=True);records=[]
for side in [58,60,62,64]:
 c.P['body_side_cut_x_mm']=side;c.D=c.derived();b.D=c.D;sc=c.setup_scene()
 b.materials()
 b.shells();b.optics();b.wheel_and_drive();b.studio()
 allowed=['Body_Upper','Body_Lower','Head_Front','Head_Rear','Tire_L','Tire_R','Wheel_Hub_L','Wheel_Hub_R','Wheel_Cap_L','Wheel_Cap_R','Face_Protector','Display_Module','Display_PCB','Camera_Lens','Camera_Window','Camera_Baffle','Eye_L','Eye_R']
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(c.PREFIX) not in allowed
 sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.render.resolution_x=640;sc.render.resolution_y=760;sc.render.resolution_percentage=100
 camera('sidecut_'+str(side),(0,650,128),(0,0,128),294);sc.render.filepath=str(out/('sidecut_'+str(side)+'.png'));bpy.ops.render.render(write_still=True)
 records.append({'side_cut_abs_x_mm':side,'pocket_seat_width_mm':2*side,'body_front_width_mm':max(c.bounds(bpy.data.objects[c.PREFIX+n])[0][1] for n in ['Body_Upper','Body_Lower'])-min(c.bounds(bpy.data.objects[c.PREFIX+n])[0][0] for n in ['Body_Upper','Body_Lower']),'head_diameter_mm':105,'overall_width_mm':2*(side+4+18+.8),'selected':side==62,'image':'renders/variants/sidecut_'+str(side)+'.png'})
c.save_json(c.ROOT/'reports/parameter_comparison.json',{'source':'Ephemeral in-memory perturbation of canonical side-cut parameter; no alternate .blend/config truth saved','scope':'Exterior silhouette experiment only, not a hardware qualification of each variant','candidates':records,'decision':'A2 retains the 62 mm pocket seat and unchanged wheel mounting/overall width. Local round pockets retain about 150 mm upper-body frontal fullness. Side-cut dimension is no longer the full body width. Variants compare wheel inset only; no hardware approval inferred.'})
print('COMPARISON_COMPLETE',flush=True)
