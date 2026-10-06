"""Explore a removable upper shell with its speaker and rear PCB retained."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
moving=['Body_Upper']+[n for n in ss if n.startswith(('Frame_Insert','Shell_Insert','Speaker','Rear_Interface','USB_Receptacle','Power_Switch'))]
removed=[n for n in ss if ss[n].group in ['yaw','pitch'] or n.startswith(('Yaw_','Frame_Screw','Shell_Screw','Tire_','Wheel_Hub','Wheel_End')) or n=='Body_Lower']
fixed={n:s for n,s in ss.items() if n not in moving+removed};origin=Vector((0,0,100));results=[]
def test(tr):
 for n in moving:
  m=ss[n].m.transform(np.array(tr)[:3,:]);bb=np.array(m.bounding_box())
  for k,s in fixed.items():
   if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
   v=max(0,(m^s.m).volume())
   if v>.05:return [n,k,v]
 return None
def pose(a,y,z):return Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
for angle in [5,10,15,20,25]:
 nominal=math.ceil(42*math.sin(math.radians(angle))+15*(1-math.cos(math.radians(angle)))+.8)
 for lift in [nominal,nominal+1,nominal+2]:
  first=None
  for u in np.linspace(0,1,angle*2+1):
   if (hit:=test(pose(angle*u,0,lift*u))):first={'phase':'tilt','fraction':float(u),'hit':hit};break
  for back in [-8,-10,-12,-14,-16]:
   fail=first
   if fail is None:
    for y in np.linspace(0,back,abs(back)*2+1):
     if (hit:=test(pose(angle,y,lift))):fail={'phase':'back','y':float(y),'hit':hit};break
   if fail is None:
    for z in np.arange(lift,140.01,1):
     if (hit:=test(pose(angle,back,z))):fail={'phase':'lift','z':float(z),'hit':hit};break
   results.append({'angle_deg':angle,'initial_lift_mm':lift,'back_mm':back,'status':'FAIL' if fail else 'PASS','first_hit':fail})
 print('BODY_TILT',angle,[(r['initial_lift_mm'],r['back_mm']) for r in results if r['angle_deg']==angle and r['status']=='PASS'],flush=True)
(HERE/'body_shell_tilt_service.json').write_text(json.dumps({'rows':results,'moving':moving,'removed_first':removed,'limits':'Candidate only. Finite rigid paths with speaker/rear PCB mounted. Head/bridge, wheels and lower shell removed; wiring disconnected. Hand grip, tolerance and prerequisite tools unqualified.'},indent=2))
