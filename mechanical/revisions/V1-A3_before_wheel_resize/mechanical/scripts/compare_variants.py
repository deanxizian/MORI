"""Noncanonical exterior-only experiments; same sphere/shell/wheel functions, no saved alternate truth."""
import sys,json,math,bpy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as c
import build as b
from render import camera
out=c.ROOT/'renders/variants';out.mkdir(parents=True,exist_ok=True);records=[];selected_side=c.P['body_side_cut_x_mm']
for side in sorted(set([56,58,59,62,selected_side])):
 c.P['body_side_cut_x_mm']=side;c.D=c.derived();b.D=c.D;sc=c.setup_scene()
 b.materials()
 b.shells();b.optics();b.wheel_and_drive();b.studio()
 allowed=['Body_Upper','Body_Lower','Head_Front','Head_Rear','Tire_L','Tire_R','Wheel_Hub_L','Wheel_Hub_R','Wheel_Cap_L','Wheel_Cap_R','Face_Protector','Display_Module','Display_PCB','Camera_Lens','Camera_Window','Camera_Baffle','Eye_L','Eye_R']
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(c.PREFIX) not in allowed
 sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.render.resolution_x=640;sc.render.resolution_y=760;sc.render.resolution_percentage=100
 camera('sidecut_'+str(side),(0,650,128),(0,0,128),294);sc.render.filepath=str(out/('sidecut_'+str(side)+'.png'));bpy.ops.render.render(write_still=True)
 records.append({'side_cut_abs_x_mm':side,'pocket_seat_width_mm':2*side,'body_front_width_mm':max(c.bounds(bpy.data.objects[c.PREFIX+n])[0][1] for n in ['Body_Upper','Body_Lower'])-min(c.bounds(bpy.data.objects[c.PREFIX+n])[0][0] for n in ['Body_Upper','Body_Lower']),'head_diameter_mm':c.P['head_diameter_mm'],'overall_width_mm':2*(side+c.P['wheel_body_gap_mm']+c.P['wheel_width_mm']+.8),'selected':side==selected_side,'image':'renders/variants/sidecut_'+str(side)+'.png'})
c.save_json(c.ROOT/'reports/parameter_comparison.json',{'source':'Ephemeral in-memory perturbation of canonical pocket-seat parameter; no alternate .blend/config truth saved','scope':'Exterior silhouette experiment only, not a hardware qualification of each variant','candidates':records,'decision':f'A3 selects the {selected_side} mm pocket seat: both wheels are {c.P["wheel_inset_revision"]["inset_per_side_mm"]} mm further inward than A2 while retaining the target 4 mm shell gap. Body mothers, wheel diameter/width and bearings remain unchanged. Variants compare wheel inset only; no hardware approval inferred.'})
print('COMPARISON_COMPLETE',flush=True)
