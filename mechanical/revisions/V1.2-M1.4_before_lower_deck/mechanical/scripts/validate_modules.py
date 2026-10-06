"""M1.4's declared bench-assembly sequence: shafts, nuts and module extraction.
This deliberately does not certify tool handles, threads or real cable unplugging.
"""
from common import *


def validate_modules(solids,Solid,intersect_volume,check):
    if P.get('structure',{}).get('architecture')!='simple_modules':return
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text())
    skin={'Body_Upper','Body_Lower','Head_Front','Head_Rear','Face_Mask','Face_Protector','Camera_Window','Camera_Baffle','Body_Top_Shroud'}
    tools=[];failures=[]
    for j in plan['joints']:
        removed=set(skin)|{j['id']+'_Screw'}
        if j['id'].startswith('Drive_'):
            removed|={'Battery','Battery_Tray'}|{n for n in solids if n.startswith('Battery_Retainer')}
        if j['id'].startswith(('Gimbal_Base_','Yaw_Base_')):
            removed|={n for n,a in solids.items() if a.group=='pitch'}
        if j['id'].startswith('Yaw_Base_'):
            removed|={n for n,a in solids.items() if a.group=='yaw'}
        x,y=j['xy_mm'];base=j['head_base_mm']+2.1
        o=cyl('assembly_tool',(x,y,base+15),2.1,30);tool=Solid(o);bad=[]
        for n,a in solids.items():
            if n not in removed:
                v=intersect_volume(tool,a)
                if v>.01:bad.append({'part':n,'overlap_mm3':round(v,3)})
        bpy.data.objects.remove(o,do_unlink=True)
        row={'joint':j['id'],'removed':sorted(removed),'shaft_diameter_mm':4.2,'shaft_length_mm':30,'failures':bad}
        tools.append(row)
        if bad:failures.append(row)
    for sign in [-1,1]:
        for rel in [-6.2,.8]:
            o=cyl('face_tool',(sign*64.3,plan['side_face_joints']['y_mm'],D['head_z']+rel),2.1,30,'X');tool=Solid(o);bad=[]
            for n,a in solids.items():
                if n in skin or n.startswith('Face_Joint_'):continue
                v=intersect_volume(tool,a)
                if v>.01:bad.append({'part':n,'overlap_mm3':round(v,3)})
            bpy.data.objects.remove(o,do_unlink=True)
            row={'joint':'Face_'+str(sign)+'_'+str(rel),'removed':sorted(skin)+['Face_Joint screws'],'shaft_diameter_mm':4.2,'shaft_length_mm':30,'failures':bad};tools.append(row)
            if bad:failures.append(row)
    check('module_screwdriver_access','FAIL' if failures else 'PASS','新增短螺钉的规定装配阶段工具杆路径',{'tested':len(tools),'failures':failures,'details':'module_service_checks.json'},'4.2mm diameter x30mm shank at actual head approach, triangle-solid intersections; named prerequisite removals; handle/fingers and actual screw recess NOT_TESTED')
    # Every case states what has already been removed. Tool access and component
    # extraction are evaluated separately instead of relying on an exploded image.
    cases=[]
    headfront=['Display_Frame','Display_PCB','Camera_PCB','Camera_Lens']
    headfront=[n for n in headfront if n in solids]
    headfront += [n for n in solids if n.startswith('Face_Joint_') and n.endswith('_Nut')]
    cases.append(('Face_assembly',headfront,(0,1,0),60,set(skin)|{n for n in solids if n.startswith('Face_Joint_') and n.endswith('_Screw')}))
    body_removed=set(skin)|{'Battery','Battery_Tray'}|{n for n in solids if n.startswith(('Wheel_','Tire_','Battery_Retainer','Deck_','Drive_')) and (n!='Drive_Bridge' and not n.startswith('Drive_Motor'))}
    for sign,side in [(-1,'L'),(1,'R')]:cases.append(('Side_'+side,['Body_Cheek_'+side],(sign,0,0),54,body_removed))
    yaw_removed=set(skin)|{n for n,a in solids.items() if a.group in ['yaw','pitch']}|{n for n in solids if n.startswith('Yaw_Base_')}
    cases.append(('Yaw_socket',['Yaw_Base','Yaw_Bearing'],(0,0,1),60,yaw_removed))
    results=[];bad_cases=[]
    for label,moving,direction,travel,removed in cases:
        errors=[]
        for distance in range(0,travel+1,3):
            tr=Matrix.Translation(Vector(direction)*distance)
            for n in moving:
                a=Solid(solids[n].o,solids[n],tr)
                for k,target in solids.items():
                    if k in removed or k in moving:continue
                    v=intersect_volume(a,target)
                    if v>.01:errors.append({'travel_mm':distance,'moving':n,'part':k,'overlap_mm3':round(v,3)})
        row={'case':label,'moving':moving,'removed':sorted(removed),'direction':direction,'step_mm':3,'travel_mm':travel,'failures':errors};results.append(row)
        if errors:bad_cases.append(row)
    check('simple_module_removal','FAIL' if bad_cases else 'PASS','屏幕组件、侧板与Yaw座的有限直线拆装采样',{'cases':len(cases),'failed_cases':len(bad_cases),'details':'module_service_checks.json'},'Actual triangle-solid translation each3mm; head/body skins and specified fasteners removed first. No flexible cable or human-hand proof.')
    save_json(ROOT/'reports/module_service_checks.json',{'tools':tools,'removal_cases':results,'limits':'Only explicit bench sequence and straight shank paths. Final supplier screws, nuts, thermal inserts, hands/handles and connectors require real assembly samples.'})
