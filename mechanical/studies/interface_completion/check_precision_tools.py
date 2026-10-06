"""Actual stage-dependent tool envelopes and rigid assembly paths, no render offsets."""
import sys,json,math,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,broad
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']};names=set(ss)
f=json.loads((HERE/'fastener_current.json').read_text());out=[]
updated_inserts={r['screw']:r for r in json.loads((HERE/'insert_candidate.json').read_text())['rows'] if r.get('screw_length_mm')}
def select(*prefixes):return {n for n in names if n.startswith(prefixes)}
skin=select('Head_Front','Head_Rear','Head_Cradle_Screw','Head_Seam_')
body_shell=select('Body_Upper','Body_Lower','Speaker','Rear_Interface','USB_Receptacle','Power_Switch','Frame_Screw','Frame_Insert','Shell_')
battery=select('Battery');headparts={n for n,s in ss.items() if s.group in ['yaw','pitch']}
yawbase=select('Yaw_Base','Yaw_Reaction','Yaw_Horn','Yaw_Output','Yaw_Lock','Yaw_Bearing')
wheels=select('Tire_','Wheel_Hub_','Wheel_End_','Wheel_Spacer_L_1','Wheel_Spacer_R_1')
body_core=names-headparts-yawbase-body_shell-battery-wheels
top_boards=select('MCU_Carrier','MCU_Motion','Power_Module','Carrier_','Power_Board_')
bottom_boards=select('Head_Buck','Wheel_Buck','Body_IMU','IMU_')
for r in f:
 n=r['id'];a=np.array(r['extracted_axis_outward']);stage='';bench=set()
 if n in ['Yaw_Lock_Screw','Pitch_Lock_Screw'] or n.startswith('Yaw_Reaction_'):
  out.append({'id':n,'status':'BLOCKED','reason':'SCS0009 horn/reaction/short-shaft interface explicitly deferred pending manufacturer data.'});continue
 if n.startswith('Wheel_Output_'):
  side=n.split('_')[3];bench=select('Drive_Motor_'+side,'S288_Output_'+side,'Wheel_Axle_'+side,'Wheel_Output_Screw_'+side);stage='1 detached motor + metal output flange, before bearings'
 elif n.startswith(('Head_Buck_','Wheel_Buck_','IMU_')):bench={'Load_Frame'}|bottom_boards;stage='2 underside PCBs on detached Load_Frame, before drive/battery'
 elif n.startswith(('Carrier_','Power_Board_')):bench={'Load_Frame'}|bottom_boards|top_boards-{'MCU_Motion'};stage='3 top PCBs on Load_Frame; core inserted after carrier screws'
 elif n.startswith('Drive_'):bench=body_core;stage='4 join drive to populated Load_Frame, before yaw bridge/battery/shells'
 elif n.startswith('Wheel_Cap_'):bench=body_core;stage='5 close motor/bearing cap, before lower shell'
 elif n.startswith('Yaw_Base_'):bench=names-headparts-body_shell-wheels;stage='6 fixed yaw bridge onto core, wheels and body shells absent'
 elif n.startswith(('Speaker_','Rear_Interface_')):bench=body_shell-{'Body_Lower'}-select('Frame_Screw','Shell_Screw');stage='7 detached upper shell: speaker and rear interface PCB'
 elif n.startswith('Frame_'):bench=names-headparts-wheels-battery-{'Body_Lower'};stage='8 fix upper shell to frame, before lower shell/battery'
 elif n.startswith('Head_Pitch_'):bench=select('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_');stage='9 pitch servo on detached yoke, before yaw servo'
 elif n.startswith('Head_Yaw_'):bench={x for x,s in ss.items() if s.group=='yaw'};stage='10 yaw servo after pitch servo, cradle/display absent'
 elif n.startswith('CAM_'):bench=select('Pitch_Cradle','CAM_Mainboard','Onboard_MIC_','CAM_Mount_','Head_Cradle_Insert');stage='11 CAM on detached Pitch_Cradle'
 elif n.startswith('LCD_'):bench=select('Display_Frame','Display_PCB','LCD_Mount_');stage='12 LCD on detached Display_Frame'
 elif n.startswith('Face_'):bench=headparts-skin;stage='13 optical frame to cradle, head shells absent'
 elif n.startswith('Head_Cradle_'):bench=names-{'Head_Rear'}-select('Head_Seam_');stage='14 front head shell fixed from top, then rear shell'
 elif n.startswith('Head_Seam_'):bench=names;stage='15 rear head shell'
 elif n.startswith('Battery_Retainer_'):bench=names-body_shell-wheels;stage='16 retained battery/tray slides into body, wheels absent'
 elif n.startswith('Shell_'):bench=names;stage='17 lower body shell'
 elif n.startswith('Wheel_End_'):bench=names;stage='18 wheels last'
 else:out.append({'id':n,'status':'BLOCKED','reason':'No explicit assembly stage assigned'});continue
 face=np.array(r['tool_start_mm'])
 if n in updated_inserts:
  ir=updated_inserts[n];face=np.array(ir['screw_head_bearing_mm'])+a*ir['head_height_mm']
 elif n.startswith(('Face_Joint','Drive_')):face+=a*(1.4-r['nominal_head_height_mm'])
 tests=[]
 for length,diameter,handle_length in [(30,16,25),(40,12,94),(50,12,94),(60,12,94),(30,10,90),(25,10,90),(20,10,90)]:
  tr=Matrix.Translation(Vector(face+a*.03))@Vector(a).to_track_quat('Z','Y').to_matrix().to_4x4();tool=manifold.Manifold.cylinder(length,1.5,1.5,48).transform(np.array(tr)[:3,:]);handle=manifold.Manifold.cylinder(handle_length,diameter/2,diameter/2,48).transform(np.array(tr@Matrix.Translation((0,0,length)))[:3,:]);hits=[]
  for part in sorted(bench-{n}):
   for kind,m in [('shaft',tool),('handle',handle)]:
    b=np.array(m.bounding_box());t=ss[part]
    if np.any(b[3:]<t.lo) or np.any(t.hi<b[:3]):continue
    vol=max(0,(m^t.m).volume())
    if vol>.02:hits.append({'kind':kind,'part':part,'volume_mm3':vol})
  tests.append({'free_shaft_length_mm':length,'handle_diameter_mm':diameter,'handle_length_mm':handle_length,'hits':hits})
 best=next((t for t in tests if not t['hits']),tests[-1]);out.append({'id':n,'stage':stage,'included_parts':sorted(bench),'status':'PASS' if not best['hits'] else 'FAIL','selected_tool_test':best,'tested_tools':tests})
(HERE/'precision_tool_checks.json').write_text(json.dumps(out,indent=2));print('TOOLS',[(r['id'],r.get('selected_tool_test')) for r in out if r.get('status')=='FAIL' or r['id']=='Head_Pitch_Ear_1_Screw'],flush=True)
