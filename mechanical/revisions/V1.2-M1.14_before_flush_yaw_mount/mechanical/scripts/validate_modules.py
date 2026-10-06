"""Simple-module bench assembly, flat deck seating and service clearances.
This deliberately does not certify tool handles, threads or real cable unplugging.
"""
from common import *


def validate_modules(solids,Solid,intersect_volume,check):
    if P.get('structure',{}).get('architecture')!='simple_modules':return
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text())
    if P['structure']['simple_modules'].get('head_frame_profile')=='flat_chamfered_u':
        cradle=solids['Pitch_Cradle'];center=np.array([0.,0.,D['head_z']])
        radius=np.linalg.norm(cradle.v-center,axis=1)
        old=json.loads((PROJECT/P['structure']['comparison_baseline']['report']).read_text())['after']['Pitch_Cradle']['volume_mm3']
        # Limit is the actual spherical shell's inner radius; shell fixing tabs
        # are checked separately by the full solid-intersection pass.
        gap=D['head_radius']-P['shell_thickness_mm']-float(radius.max())
        data={'profile':'planar U with straight chamfers; round functional holes',
              'before_volume_cm3':round(old/1000,2),'after_volume_cm3':round(cradle.m.volume()/1000,2),
              'maximum_vertex_radius_mm':round(float(radius.max()),3),'nominal_inner_sphere_radial_margin_mm':round(gap,3),
              'head_shell_attachment_xy_mm':[[48,3],[-48,3]],'shaft_centres_mm':[[44,0,D['head_z']],[-44,0,D['head_z']]],
              'limits':'Radial envelope and actual mesh volume only; full assembly overlaps and motion are separate checks. Thin ear edges, FDM strength and final shell/PCB fastening remain unqualified.'}
        save_json(ROOT/'reports/flat_head_check.json',data)
        check('flat_head_support_envelope','PASS' if gap>=.3 else 'FAIL','平板头托在球壳内的名义包络与材料体积',data,
              'All actual cradle vertices against nominal inner sphere; convex sphere contains triangles when vertices are inside. Local shell lugs require separate actual-solid checks.')
    if P['structure']['simple_modules'].get('flat_servo_seat'):
        top=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
        bottom=top-P['layout']['deck_thickness_mm']
        servo_bottom=float(solids['Yaw_Servo'].lo[2])
        # Sample the complete footprint under the servo body, including centre.
        # Ray intersections verify the actual mesh is planar, not an AABB proxy.
        samples=[]
        tree=solids['Load_Frame'].bvh()
        for x in [-4,0,6,12,16]:
            for y in [-5,0,5]:
                hit=tree.ray_cast(Vector((x,y,top+1)),Vector((0,0,-1)),P['layout']['deck_thickness_mm']+2)
                samples.append({'xy_mm':[x,y],'top_z_mm':None if hit[0] is None else round(hit[0].z,4)})
        local_flat=all(r['top_z_mm'] is not None and abs(r['top_z_mm']-top)<.02 for r in samples)
        uniform_lower=abs(float(solids['Load_Frame'].lo[2])-bottom)<.02
        volume=intersect_volume(solids['Load_Frame'],solids['Yaw_Servo'])
        battery_gap=bottom-float(solids['Battery'].hi[2])
        data={'deck_top_z_mm':top,'deck_bottom_z_mm':bottom,'servo_bottom_z_mm':round(servo_bottom,3),
              'seating_gap_mm':round(servo_bottom-top,3),'battery_to_plate_nominal_vertical_gap_mm':round(battery_gap,3),
              'lower_plane_no_hanging_shelf':uniform_lower,'footprint_rays':samples,'servo_overlap_mm3':round(volume,4),
              'limits':'Bottom seating and nominal allocation only. Servo fastening, real battery leads, compression and supplier measurements remain unqualified.'}
        save_json(ROOT/'reports/lowered_deck_check.json',data)
        ok=local_flat and uniform_lower and abs(servo_bottom-top)<.02 and volume<.01 and battery_gap>=5
        check('lowered_flat_deck','PASS' if ok else 'FAIL','降低平板、舵机平面落座与电池上方空间',data,
              'Actual mesh ray tests at15 footprint points; triangle-solid overlap; minimum plane Z; battery gap is nominal vertical allocation, not full wiring qualification')
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
        if P.get('belly_relayout',{}).get('enabled') and j['id'].startswith(('Deck_','Power_Carrier_')):
            # Deck/carrier are fitted before the removable yaw bridge/head.
            removed|={n for n,a in solids.items() if a.group in ['yaw','pitch']}|{n for n in solids if n.startswith(('Yaw_Base','Yaw_Reaction','Yaw_Horn','Yaw_Output','Yaw_Lock'))}|{'Yaw_Bearing'}
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
        for rel in plan['side_face_joints']['z_relative_head_mm']:
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
    for sign,side in [(-1,'L'),(1,'R')]:
        if 'Body_Cheek_'+side in solids:cases.append(('Side_'+side,['Body_Cheek_'+side],(sign,0,0),54,body_removed))
    if P.get('belly_relayout',{}).get('enabled'):body_removed|={n for n in solids if n.startswith(('Yaw_Base_','Yaw_Reaction'))}
    yaw_removed=set(skin)|{n for n,a in solids.items() if a.group in ['yaw','pitch']}|{n for n in solids if n.startswith('Yaw_Base_')}
    if P.get('belly_relayout',{}).get('enabled'):yaw_removed|={n for n in solids if n.startswith(('Yaw_Reaction','Yaw_Horn','Yaw_Output','Yaw_Lock'))}
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
