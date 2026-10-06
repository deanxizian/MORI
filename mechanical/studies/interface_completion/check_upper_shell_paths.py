import sys,json,math,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
# Assembly-first search: bare upper shell, chassis can be populated after shell is seated.
# All removals are explicitly recorded. Candidate-only, not a claim of complete assembly.
moving=[n for n in ss if n=='Body_Upper' or n.startswith(('Frame_Insert','Shell_Insert'))]
base_removed=[n for n in ss if ss[n].group in ['pitch','yaw'] or n.startswith(('Yaw_','Tire_','Wheel_Hub','Wheel_End','Battery','Head_Buck','Wheel_Buck','Body_IMU','IMU_','Carrier_','MCU_','Power_Module','Power_Board','Speaker','Rear_Interface','USB_Receptacle','Power_Switch','Frame_Screw','Shell_Screw')) or n=='Body_Lower']
fixed={n:s for n,s in ss.items() if n not in moving+base_removed};r=[]
def test(tr):
 for n in moving:
  m=ss[n].m.transform(np.array(tr)[:3,:]);bb=np.array(m.bounding_box())
  for k,s in fixed.items():
   if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
   v=max(0,(m^s.m).volume())
   if v>.05:return [n,k,v]
 return None
# Small tilt about the shell opening (centreZ100), then upward while keeping tilt.
for angle in [0,-5,5,-10,10,-15,15,-20,20]:
 for dy in [0,-.25,.25,-.5,.5,-1,1]:
  fail=None;origin=Vector((0,0,100));tilt=Matrix.Translation(origin)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-origin)
  for frac in np.linspace(0,1,max(2,abs(angle)+1)):
   tr=Matrix.Translation((0,dy*4*frac,4*frac))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(angle*frac),4,'X')@Matrix.Translation(-origin)
   if (hit:=test(tr)):fail={'phase':'initial','fraction':float(frac),'hit':hit};break
  if fail is None:
   for dz in range(4,121,2):
    if (hit:=test(Matrix.Translation((0,dy*dz,dz))@tilt)):fail={'phase':'lift','z':dz,'hit':hit};break
  r.append({'angle_deg':angle,'dy_per_dz':dy,'status':'FAIL' if fail else 'PASS','first_hit':fail})
 print('SHELL_PATH',angle,[(x['dy_per_dz'],x['status']) for x in r if x['angle_deg']==angle],flush=True)
(HERE/'upper_shell_paths.json').write_text(json.dumps({'moving':moving,'removed_first':base_removed,'fixed':list(fixed),'rows':r,'limits':'Assembly-first bare-shell candidate paths; populating boards afterward and real hand/wires must still be checked.'},indent=2))
