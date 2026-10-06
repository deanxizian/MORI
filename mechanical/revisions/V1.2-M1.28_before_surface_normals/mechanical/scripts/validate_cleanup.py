"""New-interface checks supplement, never waive, full mesh interference checks."""
from common import *
def validate_cleanup(solids,Solid,iv,check):
    q=P.get('layout_cleanup',{})
    if not q.get('enabled'):return
    if q.get('display_surface_mount')=='radial_on_mother_sphere':
        from optics_mount import display_transform
        mask=solids['Face_Mask'];inv=np.array(display_transform().inverted())
        raw=mask.v@inv[:3,:3].T+inv[:3,3]
        r=P['display']['mask_outer_diameter_mm']/2
        rr=np.hypot(raw[:,0],raw[:,2]-D['head_z'])
        rim=mask.v[(np.abs(rr-r)<.02)&(np.abs(raw[:,1]-(D['face_y']+.5))<.02)]
        err=np.linalg.norm(rim-np.array([0,0,D['head_z']]),axis=1)-D['head_radius']
        data={'rim_vertices':len(rim),'radial_surface_error_min_max_mm':[float(err.min()),float(err.max())],
              'outer_rim_plane_distance_mm':math.sqrt(D['head_radius']**2-r*r),'mount_pitch_deg':q['display_mount_pitch_deg'],
              'flat_hardware_unscaled':True,'surface':'Mother sphere, radial circle rim; inner display/cover remain flat',
              'active_center_lift_mm':float((display_transform()@Vector((0,P['display']['vendor_front_y_from_head_mm'],D['head_z']))).z-D['head_z'])}
        check('face_rim_on_sphere','PASS' if len(rim)>=64 and max(abs(err))<.03 else 'FAIL','黑色圆脸外缘与头球面接齐，消除倾斜造成的非对称凹台',data,'Actual mask front-rim mesh vertices versus analytic mother sphere; 0.03mm tessellation tolerance, not a manufacturing flushness guarantee.')
        save_json(ROOT/'reports/face_surface_fit.json',data)
        deck=solids['Load_Frame'];tree=deck.bvh();samples=[]
        for sign in [-1,1]:
            for y in range(-26,27,2):
                x=sign*(q['frame_side_half_width_mm']-.2)
                h=tree.ray_cast(Vector((x,y,117)),Vector((0,0,-1)),10)[0]
                h2=None if h is None else tree.ray_cast(h+Vector((0,0,-.01)),Vector((0,0,-1)),12)[0]
                samples.append({'x_mm':x,'y_mm':y,'top_z_mm':None if h is None else h.z,'bottom_z_mm':None if h2 is None else h2.z,'thickness_mm':None if h2 is None else h.z-h2.z})
        flat=all(a['thickness_mm'] is not None and abs(a['thickness_mm']-P['layout']['deck_thickness_mm'])<.02 for a in samples)
        gap=min(deck.m.min_gap(solids['Tire_'+s].m,20) for s in ['L','R'])
        data={'full_side_width_mm':2*q['frame_side_half_width_mm'],'side_wall_min_x_abs_mm':P['body_side_cut_x_mm']-P['shell_thickness_mm'], 'minimum_frame_tire_gap_mm':gap,'samples':samples}
        check('load_frame_uncut_side_lands','PASS' if flat and gap>=3 else 'FAIL','托板左右整边收窄，轮窝附近底面仍保留完整4mm平板',data,'54 paired ray intersections at x=+/-51.8mm, y=-26..26 step2; actual solid tyre gap. Shell/assembly collision and strength are separate checks.')
        save_json(ROOT/'reports/frame_side_clearance.json',data)
    im=solids['Body_IMU'];bat=solids['Battery'];deck=solids['Load_Frame'];bottom=P['layout']['deck_z_mm']-P['layout']['deck_thickness_mm']/2
    gap=im.m.min_gap(bat.m,30);plug=bpy.data.objects[PREFIX+'IMU_Plug_Reserve'];p=Solid(plug)
    collisions=[{'part':n,'mm3':round(v,3)} for n,b in solids.items() if n!='Body_IMU' and (v:=iv(p,b))>.01]
    check('imu_underside_rigid_mount','PASS' if im.hi[2]<bottom and gap>=3 and not collisions else 'FAIL','原生20×16 IMU装到主托板底面，器件向下；检查电池及插头空间',{'board_bounds_mm':list(zip(im.lo.tolist(),im.hi.tolist())),'deck_underside_plane_z_mm':bottom,'battery_actual_solid_gap_mm':gap,'plug_allocation_mm':[14,7,10],'plug_conflicts':collisions,'axis_transform':'imu_mount_transform.json'},'Received native PCB geometry at1:1; mating plug and ICM die-to-board axes require verification. PCB normal is -Z, not firmware calibration.')
    absent=[n for n in ['Function_Button','Button_Cap','Body_Cheek_L','Body_Cheek_R','Power_Board_Carrier'] if n in solids]
    check('removed_redundant_parts','PASS' if not absent else 'FAIL','移除独立功能键；两侧短板与主托板合并，删除独立电源托板',{'unexpected_objects':absent,'changes':'layout_cleanup_changes.json'})
    check('level_head_independent_optics','PASS' if P['head_joint']['default_pitch_deg']==0 else 'FAIL','头底切面保持水平，屏幕/相机单独固定上仰',json.loads((ROOT/'reports/optical_mounts.json').read_text()),'Applied rigid mounting transforms only to optics, with a new upright screen fork; mechanical controller zero is unchanged. Full assembly/ray/motion checks are separate.')
    # New PCB screw access: bench assembly before electronics/head installation.
    toolrows=[]
    for n in ['IMU_Screw_0','IMU_Screw_1','Rear_Interface_Screw_0','Rear_Interface_Screw_1']:
        a=solids[n];c=(a.lo+a.hi)/2;under=True;start=float(a.lo[2] if under else a.hi[2]);sgn=-1 if under else 1
        tool=cyl('new_board_tool',(c[0],c[1],start+sgn*15.2),2.1,30);ts=Solid(tool)
        targets=['Load_Frame','Body_IMU'] if n.startswith('IMU_') else ['Body_Upper','Rear_Interface_PCB','Power_Switch','USB_Receptacle']
        bad=[{'part':k,'mm3':round(v,3)} for k in targets if (v:=iv(ts,solids[k]))>.01]
        toolrows.append({'screw':n,'direction':'-Z' if under else '+Z','bench_prerequisite':'IMU before battery/drive; interface PCB on detached upper shell','failures':bad});bpy.data.objects.remove(tool,do_unlink=True)
    check('new_PCB_bench_tool_access','FAIL' if any(x['failures'] for x in toolrows) else 'PASS','IMU底面与后接口板的台面装配工具杆空间',toolrows,'4.2mm diameter30mm shafts, prescribed bench sequence. Not a whole-hand/driver-handle proof.')
    if not P.get('native_electronics',{}).get('enabled'):
        check('rear_interface_double_sided_selection','BLOCKED','后接口板已生成板框、壳体安装座及上下开口；双面侧出器件待另任务选型',json.loads((ROOT/'reports/rear_interface_geometry.json').read_text()),'Nominal interfaces are requirements. No exact purchased switch/USB CAD or electrical pin assignment is claimed.')
        check('native_P3_handoff','BLOCKED','P2原生基板/IMU已1:1摆入，电源80×55容量已纳入；P3原生坐标已交接，完整装件与插头适配仍未完成',{'mechanical_design_dimensions_changed':False,'P2_reference_files':['mechanical/studies/pcb_P2_fit/motion_mesh.json','mechanical/studies/pcb_P2_fit/imu_mesh.json'],'power_capacity':'config/geometry.json#/layout_cleanup/power_bay'},'No edits to KiCad files. P2 library CAD is a reference, never labeled final P3 physical hardware.')

    check('imu_three_anchor_recommendation','BLOCKED','P3交接指出IMU两孔与厂家至少三固定点建议仍需结构适配',{'handoff':'hardware/v1_2/handoff/mechanical_P3.json','current_holes':2,'physical_response':'NOT_TESTED'},'This revision retains the two native holes; rigid mesh fit does not certify PCB strain/vibration. No unapproved board hole added.')

    # Same-group wires do not move relative to their seats, but still need real
    # passages. The general motion pass checks cross-group sweeps separately.
    wirebad=[]
    for o in bpy.context.scene.objects:
        if o.get('role')!='routing':continue
        a=Solid(o)
        for n,b in solids.items():
            if a.group==b.group and (v:=iv(a,b))>.05:wirebad.append({'route':a.name,'part':n,'intersection_mm3':round(v,3)})
    check('static_same_group_wire_passages','PASS' if not wirebad else 'FAIL','全部已画线束预留与同组实体的通孔/槽检查',{'failures':wirebad,'volume_threshold_mm3':.05},'Triangle-solid intersections of the actual routing tubes, including same-group parts. Does not certify real connectors, minimum cable bend radius or strain relief.')
    rows=[]
    cases=[('Rear_interface_bench',['Rear_Interface_PCB','Power_Switch','USB_Receptacle'],['Body_Upper'],(0,0,-1),35),('Load_frame_bench',['Load_Frame','Body_IMU','IMU_Screw_0','IMU_Screw_1','IMU_Insert_0','IMU_Insert_1'],['Drive_Bridge','Drive_Motor_L','Drive_Motor_R','Tire_L','Tire_R','Motor_Retainer'],(0,0,1),54)]
    for label,moving,obstacles,direction,length in cases:
        bad=[]
        for step in range(0,length+1,2):
            tr=Matrix.Translation(Vector(direction)*step)
            for n in moving:
                a=Solid(solids[n].o,solids[n],tr)
                for k in obstacles:
                    if (v:=iv(a,solids[k]))>.01:bad.append({'travel_mm':step,'part':n,'obstacle':k,'volume_mm3':round(v,3)})
        rows.append({'case':label,'moving':moving,'obstacles':obstacles,'direction':direction,'travel_mm':length,'step_mm':2,'failures':bad})
    check('merged_frame_and_rear_PCB_removal','PASS' if not any(r['failures'] for r in rows) else 'FAIL','一体短侧板主框与后接口板的规定台面拆出路径',{'cases':rows,'prerequisites':['Rear PCB: upper shell detached, wires disconnected and two underside screws removed; lower along-Z on detached shell; disconnect all connectors','Main frame: remove shells, battery/tray, head/yaw bridge, top electronics and four lower drive joints first; lift frame with underside IMU']},'Finite2mm translation samples with listed actual solids. No hand/cable-flex or arbitrary-order assembly claim.')
    save_json(ROOT/'reports/layout_cleanup_validation.json',{'revision':P['revision'],'wire_passages':wirebad,'removal_cases':rows,'status':'FAIL' if wirebad or any(r['failures'] for r in rows) else 'PASS'})
