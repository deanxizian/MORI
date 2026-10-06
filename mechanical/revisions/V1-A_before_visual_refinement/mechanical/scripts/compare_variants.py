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
 for name,col in [('shell',(.83,.81,.75)),('frame',(.20,.27,.30)),('tire',(.04,.045,.05)),('metal',(.5,.52,.54)),('pcb',(.03,.19,.13)),('dark',(.003,.004,.006)),('belt',(.07,.07,.07)),('ground',(.2,.23,.28))]:c.material(name,col)
 c.material('glass',(.9,.97,1),transmission=1,roughness=.12);c.material('eye',(.07,.83,.92),emission=2)
 b.shells();b.optics();b.wheel_and_drive();b.studio()
 allowed=['Body_Upper','Body_Lower','Head_Front','Head_Rear','Tire_L','Tire_R','Wheel_Hub_L','Wheel_Hub_R','Wheel_Cap_L','Wheel_Cap_R','Face_Protector','Display_Module','Display_PCB','Camera_Lens','Camera_Window','Eye_L','Eye_R']
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(c.PREFIX) not in allowed
 sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.render.resolution_x=640;sc.render.resolution_y=760;sc.render.resolution_percentage=100
 camera('sidecut_'+str(side),(0,650,128),(0,0,128),294);sc.render.filepath=str(out/('sidecut_'+str(side)+'.png'));bpy.ops.render.render(write_still=True)
 records.append({'side_cut_abs_x_mm':side,'cut_body_front_width_mm':2*side,'head_diameter_mm':105,'width_ratio':round(2*side/105,3),'overall_width_mm':2*(side+4+18+.8),'selected':side==62,'image':'renders/variants/sidecut_'+str(side)+'.png'})
c.save_json(c.ROOT/'reports/parameter_comparison.json',{'source':'Ephemeral in-memory perturbation of canonical side-cut parameter; no alternate .blend/config truth saved','scope':'Exterior silhouette experiment only, not a hardware qualification of each variant','candidates':records,'decision':'62 mm selected: 124 mm frontal body / 105 mm head = 1.181. 58 and 60 look too close to head width; 64 adds 4 mm total wheel width without required gain. 1.15 ratio is this design study preference, not an external specification.'})
print('COMPARISON_COMPLETE',flush=True)
