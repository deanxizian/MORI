"""Checks for M1.9's actual relocated assemblies; no claimed real PCB fit."""
from common import *

def validate_belly(solids,Solid,intersect_volume,check):
    if not P.get('belly_relayout',{}).get('enabled'):return
    s=P['belly_relayout'];deck=solids['Load_Frame'];battery=solids['Battery'];power=solids['Power_Module'];carrier=solids.get('Power_Board_Carrier')
    wheel=[]
    for side in ['L','R']:
        m=solids['Drive_Motor_'+side];out=solids['S288_Output_'+side+'_Outer'];c=(out.lo+out.hi)/2
        wheel.append({'side':side,'rotation_deg':s['wheel_servo_rotation_deg'][side],'bounds_xyz_mm':list(zip(m.lo.tolist(),m.hi.tolist())),
                      'top_mm':float(m.hi[2]),'output_yz_mm':c[1:].tolist(),
                      'shell_min_gap_mm':min(m.m.min_gap(solids[n].m,30) for n in ['Body_Upper','Body_Lower'])})
    top=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    measurements={'wheel_motors':wheel,'battery_center_mm':P['layout']['battery_center_mm'],
      'battery_allocation_mm':P['layout']['battery_max_xyz_mm'],'deck_top_mm':top,'battery_to_deck_mm':float((P['layout']['deck_z_mm']-P['layout']['deck_thickness_mm']/2)-battery.hi[2]),
      'power_capacity_xyz_mm':(power.hi-power.lo).tolist(),'power_capacity_center_mm':((power.hi+power.lo)/2).tolist(),
      'power_bottom_to_carrier_top_mm':float(power.lo[2]-carrier.hi[2]) if carrier else None,
      'power_to_yaw_bridge_min_gap_mm':power.m.min_gap(solids['Yaw_Base'].m,20),
      'fixed_reaction_link_group':solids['Yaw_Reaction_Link'].group,'servo_case_group':solids['Yaw_Servo'].group,'yaw_output_group':solids['Yaw_Output'].group,
      'yaw_servo_bounds_xyz_mm':list(zip(solids['Yaw_Servo'].lo.tolist(),solids['Yaw_Servo'].hi.tolist())),
      'limits':'Power envelope is80x55 PCB plus16mm front/3mm rear component limits, NOT P3 actual populated CAD. Battery uses manufacturer nominal envelope. Gaps exclude unmeasured plugs, tolerances and flex. Finite collision and motion checks are separate.'}
    ok=all(abs(w['output_yz_mm'][0])<.02 and abs(w['output_yz_mm'][1]-D['wheel_z'])<.02 and abs(w['top_mm']-62.5)<.02 and w['shell_min_gap_mm']>=3 for w in wheel)
    ok=ok and measurements['battery_to_deck_mm']>=4.99 and (abs(measurements['power_bottom_to_carrier_top_mm'])<.02 if carrier else True) and measurements['power_to_yaw_bridge_min_gap_mm']>=1
    ok=ok and solids['Yaw_Servo'].group=='yaw' and all(solids[n].group=='body' for n in ['Yaw_Output','Yaw_Horn','Yaw_Reaction_Link'])
    check('belly_relayout_datums','PASS' if ok else 'FAIL','横躺轮驱、头内Yaw与降低电池/板卡区的实际坐标和支承分组',measurements,'Actual solid bounds/distances and motion group inspection; 1:1 source audit, static interference and sampled joint motion reported separately.')
    # Bench sequence: remove pitch head, disconnect wires, unlock the spline,
    # then lift servo case/output before extracting the keyed reaction link.
    skin={'Head_Front','Head_Rear','Body_Upper','Body_Lower','Face_Mask','Face_Protector','Camera_Window','Camera_Baffle','Body_Top_Shroud'}
    removed=skin|{n for n,a in solids.items() if a.group=='pitch'}|{n for n in solids if n.startswith('Head_Yaw_Ear_')}|{'Yaw_Lock_Screw'}
    cases=[('Head_yaw_servo',['Yaw_Servo','Yaw_Output'],45,removed.copy())]
    removed|={'Yaw_Servo','Yaw_Output'}|{n for n in solids if n.startswith('Yaw_Reaction_Retainer')}
    u_parts=[n for n,a in solids.items() if a.group=='yaw' and n not in ['Yaw_Servo','Yaw_Turntable'] and not n.startswith(('Gimbal_Base_','Head_Yaw_Ear_'))]
    removed|={n for n in solids if n.startswith('Gimbal_Base_')}
    reaction=['Yaw_Reaction_Link','Yaw_Horn','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut']
    if P.get('part_consolidation',{}).get('enabled'):
        cases.append(('Combined_yaw_U_and_released_reaction',u_parts+reaction,66,removed.copy()))
    else:
        cases.append(('Yaw_U_support',u_parts,60,removed.copy()))
        removed|=set(u_parts)
        cases.append(('Reaction_link',reaction,66,removed.copy()))
    rows=[]
    for label,names,travel,removed in cases:
        errors=[]
        for z in range(0,travel+1,3):
            tr=Matrix.Translation((0,0,z))
            for n in names:
                a=Solid(solids[n].o,solids[n],tr)
                for k,b in solids.items():
                    if k in removed or k in names:continue
                    v=intersect_volume(a,b)
                    if v>.01:errors.append({'travel_mm':z,'moving':n,'target':k,'overlap_mm3':round(v,3)})
        rows.append({'case':label,'moving':names,'removed':sorted(removed),'travel_mm':travel,'step_mm':3,'failures':errors})
    check('head_yaw_bench_removal','FAIL' if any(r['failures'] for r in rows) else 'PASS','倒装Yaw与可拆反力轴的规定顺序取出检查',{'cases':len(rows),'failures':sum(len(r['failures']) for r in rows),'details':'belly_relayout_validation.json'},'Rigid triangle-solid translations every3mm. Pitch head disconnected and removed; ear/spline/cross-retainer screws removed in stated order. Real cable connectors, hands and thread fits NOT_TESTED.')
    tools=[]
    for i,y in enumerate([-8.55,19.95]):
        bolt=solids['Head_Yaw_Ear_'+str(i)+'_Screw'];start=float(bolt.hi[2])+.3
        o=cyl('yaw_ear_tool',(0,y,start+15),2.1,30);t=Solid(o)
        skip=skin|{n for n,a in solids.items() if a.group=='pitch'}|{bolt.name}
        bad=[{'part':n,'volume_mm3':round(v,3)} for n,a in solids.items() if n not in skip and (v:=intersect_volume(t,a))>.01]
        tools.append({'name':bolt.name,'shaft_diameter_mm':4.2,'length_mm':30,'removed':sorted(skip),'failures':bad});bpy.data.objects.remove(o,do_unlink=True)
    check('head_yaw_ear_tools','FAIL' if any(t['failures'] for t in tools) else 'PASS','头内Yaw两安装耳的直线工具杆空间',{'tools':tools},'Actual4.2mm diameter30mm shanks before fitting pitch head; excludes handle, thread and supplier screw recess qualification.')
    save_json(ROOT/'reports/belly_relayout_validation.json',{'measurements':measurements,'removal_cases':rows,'tools':tools,'status':'PASS' if ok and not any(r['failures'] for r in rows) and not any(t['failures'] for t in tools) else 'FAIL','pending':['Real S3 populated board/connector CAD','Selected battery lead/strap envelope','Real20T horn and clamp torque','Reaction link deflection and bearing retention','Thermal and dynamic balancing tests']})
