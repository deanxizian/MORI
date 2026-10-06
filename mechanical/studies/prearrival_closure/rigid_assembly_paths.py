"""Finite, staged insertion checks against the immutable current assembly."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']};names=set(ss)
def select(*prefixes):return {n for n in names if n.startswith(prefixes)}
inserts={r['id']:r['host'] for r in P['interface_completion']['inserts']}
def with_inserts(s):return set(s)|{i for i,h in inserts.items() if h in s}
top=select('MCU_Carrier','Power_Module','Carrier_','Power_Board_')
bottom=select('Body_IMU','IMU_','Head_Buck','Wheel_Buck')
core=with_inserts({'Load_Frame'})|top|bottom|{'MCU_Motion'}|select('Socket_','E_Straight_Header')
drive=select('Drive_Bridge','Drive_Motor','S288_Output','Wheel_Axle','Wheel_Bearing','Wheel_Spacer_L_0','Wheel_Spacer_R_0','Wheel_Output','Motor_Top_Pad','Motor_Retainer','Wheel_Cap')
cartridge=drive-select('Drive_Bridge','Motor_Retainer','Wheel_Cap')
yoke=with_inserts({'Pitch_Yoke'})
results=[]
def check(label,moving,fixture,axis,travel,step=1,limit=60,waypoints=None):
    moving=set(moving)&names;fixture=(set(fixture)&names)-moving
    a=np.array(axis,dtype=float);a/=np.linalg.norm(a);bad=[];count=0
    steps=[(float(d),a*d) for d in np.arange(0,travel+.001,step)]
    if waypoints:
        steps=[];sofar=0
        for p,q in zip(waypoints,waypoints[1:]):
            p=np.array(p,dtype=float);q=np.array(q,dtype=float);ln=np.linalg.norm(q-p)
            for t in np.linspace(0,1,int(math.ceil(ln/step))+1):steps.append((sofar+float(t*ln),p+(q-p)*t))
            sofar+=ln
    for d,shift in steps:
        count+=1
        for n in sorted(moving):
            s=ss[n];lo=s.lo+shift;hi=s.hi+shift;m=None
            for other in sorted(fixture):
                t=ss[other]
                if np.any(hi<t.lo) or np.any(t.hi<lo):continue
                if m is None:m=s.m.translate(shift.tolist())
                v=max(0,(m^t.m).volume())
                if v>.05:
                    bad.append(dict(travel_mm=float(d),moving=n,fixed=other,volume_mm3=v))
                    if len(bad)>=limit:break
            if len(bad)>=limit:break
        if len(bad)>=limit:break
    row=dict(id=label,status='PASS' if not bad else 'FAIL',moving=sorted(moving),fixture=sorted(fixture),withdrawal_axis=a.tolist(),travel_mm=travel,waypoint_displacements_mm=waypoints,sample_step_mm=step,samples=count,hits=bad,scope='Nominal rigid solids; reverse path used for insertion. No flexible leads or physical press-fit force.')
    results.append(row);print(label,row['status'],bad[:2],flush=True)

# Parts are handled as independent bench subassemblies, not exploded together
# through one another. Fasteners installed AFTER the represented insertion.
for side,sgn in [('L',-1),('R',1)]:
    shaft={'Wheel_Axle_'+side}
    check('metal_flange_to_S288_'+side,shaft,select('Drive_Motor_'+side,'S288_Output_'+side),[sgn,0,0],50)
    placed=shaft
    for n in ['Wheel_Bearing_'+side+'_Inner','Wheel_Spacer_'+side+'_0','Wheel_Bearing_'+side+'_Outer']:
        check('slide_'+n,{n},placed,[sgn,0,0],45,.5);placed=placed|{n}
check('motor_cartridges_into_open_case',cartridge,with_inserts({'Drive_Bridge'}),[0,0,-1],55)
check('motor_cap',select('Motor_Retainer'),drive-select('Motor_Retainer','Wheel_Cap'),[0,0,-1],35)
for n in ['Body_IMU','Head_Buck','Wheel_Buck']:
    check('underside_'+n,{n},with_inserts({'Load_Frame'}),[0,0,-1],35,.5)
for n in ['MCU_Carrier','Power_Module']:
    check('top_'+n,{n},with_inserts({'Load_Frame'})|bottom,[0,0,1],45,.5)
check('join_populated_frame_to_drive',core,drive,[0,0,1],70,1)
check('fixed_yaw_bridge',with_inserts({'Yaw_Base'}),core|drive,[0,0,1],80,1)
check('yaw_bearing',{'Yaw_Bearing'},{'Yaw_Base'},[0,0,1],30,.5)
check('rotating_yoke',yoke,{'Yaw_Base','Yaw_Bearing'},[0,0,1],90,1)
check('pitch_servo_on_detached_yoke',{'Pitch_Servo','Pitch_Output'},yoke,[1,0,0],90,.5,waypoints=[[0,0,0],[30,0,0],[30,0,60]])
check('yaw_servo_on_detached_yoke',{'Yaw_Servo','Yaw_Output'},yoke|{'Pitch_Servo','Pitch_Output'},[0,0,1],50,.5)
check('bare_cradle_before_short_shafts',with_inserts({'Pitch_Cradle'}),yoke|{'Yaw_Servo','Pitch_Servo','Yaw_Output','Pitch_Output'},[0,0,1],70,1)
check('LCD_to_detached_fork',{'Display_PCB'},{'Display_Frame'},[0,math.cos(math.radians(10)),math.sin(math.radians(10))],40,.5)
check('optical_fork_to_head_cradle',{'Display_Frame','Display_PCB','Camera_PCB','Camera_Lens'},yoke|with_inserts({'Pitch_Cradle'})|{'Yaw_Servo','Pitch_Servo','CAM_Mainboard'},[0,1,0],70,1)
for side,sgn in [('L',-1),('R',1)]:
    check('wheel_on_shaft_'+side,{'Wheel_Hub_'+side,'Tire_'+side,'Wheel_Spacer_'+side+'_1'},drive|core,[sgn,0,0],70,1)

out=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),cases=results,status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',limits=['Failed trial paths must be corrected by a documented order/path or user-approved change; never silently omit the obstructing part.','Head horn/short-shaft assemblies explicitly remain BLOCKED by vendor evidence; bare-cradle placement alone is not completed head transmission assembly.','Current battery, camera, shell, nut-entry and complete wheel-cartridge paths are additionally recorded in M1.43 validation reports.'])
(HERE/'rigid_assembly_paths.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
