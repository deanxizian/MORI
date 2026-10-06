"""M1.3: continuous equipment pods/cups/tub instead of a beam skeleton.

This is physical candidate mesh geometry, not a display cover hiding old rods.
Joint groups and vendor geometry stay unchanged. No strength qualification.
"""
from common import *
from purchased_geometry import remove_generated
from structural_simplification import printed,hardware,volume


def source_build():
    import sys
    mod=sys.modules.get('__main__')
    if hasattr(mod,'CONTACTS'):return mod
    import build
    return build


def obj(name):return bpy.data.objects[PREFIX+name]


def reserve(name,target,margin=.5):
    bb=bounds(target)
    return box(name,[(a+b)/2 for a,b in bb],[b-a+2*margin for a,b in bb])


def apply_monocoque_structure():
    if P.get('structure',{}).get('architecture')not in ['monocoque','simple_modules']:return
    b=source_build();hz=D['head_z'];wz=D['wheel_z'];dz=P['layout']['deck_z_mm'];s=P['structure']
    targets=['Pitch_Cradle','Display_Frame','Pitch_Yoke','Head_Lower_Guard','Yaw_Turntable',
             'Yaw_Carrier','Yaw_Servo_Mount','Load_Frame','Motor_Mount_L','Motor_Mount_R',
             'Battery_Tray','MCU_Mount_Motion','IMU_Mount','Power_Module_Mount','USB_Charge_Mount',
             'Yaw_Stop_-76','Yaw_Stop_76']
    before={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in targets}

    # Pitch equipment pod: broad continuous side/rear walls. Its open lower
    # centre admits the independent yaw gimbal; the front is a perforated bulkhead.
    remove_generated('Pitch_Cradle');wt=s['head_pod_wall_mm'];limit=s['head_pod_outer_radius_mm']
    pod=box('Pitch_Cradle',(0,1,hz+11),(94,70,42))
    boolean(pod,box('pod_open_cavity',(0,1,hz+15),(94-2*wt,70-2*wt,80)))
    front=box('pod_front_bulkhead',(0,35,hz+1),(94,3.2,76))
    boolean(front,cyl('lcd_rear_service',(0,35,hz+P['display']['z_from_head_mm']),24,14,'Y'))
    union(pod,front)
    # Short, local bearing shelves, carried by the full side walls.
    for sign in [-1,1]:
        union(pod,box('trunnion_local_land',(sign*45,0,hz),(5,20,18)))
        boolean(pod,cyl('trunnion_pass',(sign*44,0,hz),2.7,20,'X'))
        boolean(pod,cyl('fixed_bearing_clear',(sign*39,0,hz),9.3,5.4,'X'))
    union(pod,box('camera_local_seat',(0,37.4,hz+P['camera']['body_center_from_head_mm'][2]),(16,2,12)))
    # The retained microphone paths pass through real holes in the rear wall.
    for sign in [-1,1]:boolean(pod,cyl('mic_pass',(sign*18,-34,hz+27),2.9,12,'Y'))
    boolean(pod,box('cam_antenna_service',(0,-37,hz+34),(24,16,16)))
    boolean(pod,box('camera_fpc_pass',(10.5,35,hz+31),(9,12,8)))
    dp=P['display'];sz=hz+dp['z_from_head_mm'];fy=dp['vendor_mount_back_y_from_head_mm']-1.4
    for sign in [-1,1]:
        xx=sign*31.2
        union(pod,cyl('display_local_boss',(xx,34.4,sz),3.3,6.6,'Y'))
        boolean(pod,cyl('display_screw_clear',(xx,35,sz),1.2,14,'Y'))
        boolean(pod,cyl('display_nut_pocket',(xx,32.1,sz),2.9,2.6,'Y',6))
    intersect(pod,sphere('pod_limit',(0,0,hz),limit))
    for n in ['Head_Front','Head_Rear','Mic_Duct_L','Mic_Duct_R']:
        boolean(pod,clone(obj(n),'pod_local_relief'))
    printed(pod,'一体头部器件舱 / 连续围壁','pitch',
            'Continuous side/rear/front walls, no arch rods or cantilever optical braces. Open lower region admits yaw cup. CAM retention, clearances and FDM strength remain trial.')
    pod['integrated_functions']=['head_trunnions','CAM_back_support','camera_seat','front_bulkhead']

    # Thin front retainer with short radial lands to the 3 vendor posts; all
    # structural attachment is directly to the adjacent pod bulkhead.
    remove_generated('Display_Frame')
    for sign in [-1,1]:
        remove_generated('Display_Frame_Screw_'+str(sign));remove_generated('Display_Frame_Nut_'+str(sign))
    face=ring('Display_Frame',(0,fy,sz),33.8,27.1,2,'Y')
    for xx,zz in INTERFACES['components']['display']['vendor_dimensions']['cad_post_center_xz_from_screen_mm']:
        r=math.hypot(xx,zz);a=Vector((xx,fy,sz+zz));bb=Vector((xx/r*28.5,fy,sz+zz/r*28.5));dd=bb-a
        arm=box('short_post_land',(a+bb)/2,(5,2,dd.length));arm.rotation_euler=(0,math.atan2(dd.x,dd.z),0);bpy.context.view_layer.update()
        union(face,arm);union(face,cyl('post_pad',(xx,fy,sz+zz),3.4,2,'Y'))
        boolean(face,cyl('vendor_post_trial',(xx,fy,sz+zz),1.2,8,'Y'))
    for sign in [-1,1]:
        xx=sign*31.2;boolean(face,cyl('local_fixing_pass',(xx,fy,sz),1.2,8,'Y'))
        screw=cyl('Display_Frame_Screw_'+str(sign),(xx,35.7,sz),.95,8,'Y')
        union(screw,cyl('display_screw_head',(xx,40.5,sz),1.9,1.6,'Y'))
        hardware(screw,'屏幕前壁短M2螺钉（试配）','pitch')
        hardware(ring('Display_Frame_Nut_'+str(sign),(xx,32.1,sz),2.4,1.1,1.6,'Y',6),'屏幕前壁M2螺母（试配）','pitch')
    if not P['camera'].get('independent_forehead_window'):
        boolean(face,box('camera_seat_clear',(0,fy,hz+30),(18,12,14)))
    printed(face,'屏幕前壁压框 / 无悬伸支臂','pitch',
            'Directly adjacent to front bulkhead. Short2mm retainer, original3 vendor posts and2 local trial screws. No long overhead connections.')

    # Yaw gimbal cup: a continuous spherical bowl carries both pitch bearings.
    # Servo seat and bearing journal are integral, and the old guard spokes go.
    old_yoke=box('integral_servo_back',(-23,-8,hz),(28,3,24))
    union(old_yoke,box('integral_servo_floor',(-23,0,hz-12.5),(28,17,3)))
    journal=clone(obj('Yaw_Turntable'),'integral_yaw_journal')
    guard=clone(obj('Head_Lower_Guard'),'integral_lower_guard');clip_z(guard,hz-41.8,500)
    for n in ['Pitch_Yoke','Yaw_Turntable','Head_Lower_Guard']:remove_generated(n)
    r=s['gimbal_cup_radius_mm'];cup=sphere('Pitch_Yoke',(0,0,hz),r)
    boolean(cup,sphere('cup_hollow',(0,0,hz),r-s['gimbal_cup_wall_mm']))
    clip_z(cup,hz-r,hz+8.5);clip_y(cup,-100,20)
    boolean(cup,box('CAM_motion_rear_opening',(0,-41.5,hz+11),(60,47,80)))
    union(cup,cyl('cup_foot',(0,0,hz-43),18,7))
    floor=cyl('guard_continuous_floor',(0,0,hz-43.2),40,3)
    intersect(floor,sphere('guard_floor_limit',(0,0,hz),P['head_joint']['guard_outer_radius_mm']))
    union(cup,floor);union(cup,guard);union(cup,journal)
    boolean(cup,box('front_optical_motion_opening',(0,70,hz-39),(120,110,44)))
    for sign in [-1,1]:
        union(cup,ring('pitch_bearing_land',(sign*39,0,hz),8.5,6.25,4,'X'))
        boolean(cup,cyl('pitch_bearing_pass',(sign*39,0,hz),6.25,10,'X'))
    union(cup,old_yoke)
    for angle in [-28,33]:
        ca=math.cos(math.radians(angle));sa=math.sin(math.radians(angle))
        union(cup,box('pitch_stop',(39,-10*ca,hz-10*sa),(4,3,3)))
        union(cup,box('pitch_stop_land',(39,-8.5*ca,hz-8.5*sa),(4,5,3)))
    boolean(cup,reserve('pitch_servo_clear',obj('Pitch_Servo'),.25))
    for sign in [-1,1]:boolean(cup,cyl('pitch_bearing_final_bore',(sign*39,0,hz),6.25,10,'X'))
    boolean(cup,cyl('fixed_cable_throat',(0,0,hz-43),8,15))
    # Preserve the existing finite yaw lead as a real bored channel.
    if not P.get('head_routing',{}).get('defer_design'):
        for a,bb in zip(yaw_head_lead_points(),yaw_head_lead_points()[1:]):
            boolean(cup,b.beam('yaw_wire_channel',a,bb,2.5))
    printed(cup,'一体杯形双轴承座 / 含Yaw轴颈与下护罩','yaw',
            'Continuous bowl carries bilateral pitch bearings; journal and lower light guard integral. Relative yaw/pitch bodies remain separate. Servo seat and hard-stop angles/strength are trial.')
    cup.data.materials.append(MATS['dark'])
    for poly in cup.data.polygons:
        center=cup.matrix_world@poly.center
        if (center-Vector((0,0,hz))).length>54 and center.z<hz-25:poly.material_index=1

    # Chassis is an open-front tub, not a cover over the old slender struts.
    # Keep the deck, local motor seats and battery rails, replacing their spans.
    deck=clone(obj('Load_Frame'),'retained_deck');clip_z(deck,dz-2,500)
    motor_seats=[clone(obj('Motor_Mount_'+n),'motor_integral_'+n) for n in ['L','R']]
    for seat in motor_seats:clip_y(seat,-12.5,100)
    carrier=clone(obj('Yaw_Carrier'),'yaw_ring_integral');clip_z(carrier,156.65,500)
    mcu=clone(obj('MCU_Mount_Motion'),'mcu_integral');imu=clone(obj('IMU_Mount'),'imu_integral')
    for n in ['Load_Frame','Motor_Mount_L','Motor_Mount_R','Yaw_Carrier','Yaw_Servo_Mount',
              'MCU_Mount_Motion','IMU_Mount','Power_Module_Mount','USB_Charge_Mount']:remove_generated(n)
    for side in ['L','R']:
        for index in [0,1]:
            remove_generated('Motor_Mount_Screw_'+side+str(index));remove_generated('Motor_Mount_Nut_'+side+str(index))
    tub=box('Load_Frame',(0,-10,83.5),(104,100,97))
    boolean(tub,box('front_open_bay',(0,24,83.5),(104-2*s['body_tub_wall_mm'],160,130)))
    rear=box('upper_rear_bulkhead',(0,-58,143.5),(104,4,23));union(tub,rear)
    # Outer clearance follows the real body profile and wheel recesses.
    intersect(tub,b.body_outer('tub_skin_limit',P['shell_thickness_mm']+s['body_frame_skin_clearance_mm']))
    union(tub,deck)
    for sign in [-1,1]:
        bearing=ring('wheel_bearing_integral',(sign*41.5,0,wz),9,5.25,22,'X')
        intersect(bearing,b.body_outer('bearing_body_limit',P['shell_thickness_mm']+s['body_frame_skin_clearance_mm']))
        union(tub,bearing)
        union(tub,box('battery_local_ledge',(sign*44.5,0,79.8),(13,48,3)))
        union(tub,box('battery_retainer_land',(sign*47,20,88),(3,9,13)))
        boolean(tub,cyl('battery_retainer_pass',(sign*47,20,88),1.2,20,'X'))
        boolean(tub,cyl('retainer_head_counterbore',(sign*51,20,88),2.3,5,'X'))
    for seat in motor_seats:union(tub,seat)
    # The local motor cages meet one shared roof across their full width;
    # no former narrow mounting webs remain inside the continuous tub.
    union(tub,box('continuous_motor_roof',(0,-12.25,wz+27),(54,49.5,2.8)))
    union(tub,box('motor_saddle_crosswall',(0,-48,76),(46,26,8)))
    # Complete cylindrical yaw socket; side opening permits servo insertion.
    socket=ring('yaw_integral_socket',(0,0,144.4),25,21.5,20.8)
    boolean(socket,box('servo_service_port',(0,16,144),(36,24,20)))
    union(socket,ring('yaw_continuous_shoulder',(0,0,155.7),25,10.2,1.8))
    union(socket,ring('yaw_upper_socket',(0,0,161),25,16.3,10))
    union(tub,socket);union(tub,carrier)
    # Short shelf supporting the yaw servo, with no free upright posts.
    union(tub,box('yaw_servo_floor',(0,0,126.5),(30,19,2)))
    for sign in [-1,1]:union(tub,box('servo_floor_wall',(sign*14,0,130),(3,19,8)))
    union(tub,mcu);union(tub,imu)
    power=box('power_integral_shelf',(0,-40,153.5),(48,32,2))
    intersect(power,b.body_outer('power_shell_limit',P['shell_thickness_mm']+s['body_frame_skin_clearance_mm']))
    union(tub,power)
    usb=box('usb_integral_shelf',(14,-58,106),(32,22,2));union(tub,usb)
    for n in ['Yaw_Servo','MCU_Motion','Body_IMU','Power_Module','USB_Charge','Battery_Tray','Speaker_Mount','Speaker']:
        boolean(tub,reserve('component_service_clear',obj(n),.3))
    # The tray uses sliding clearance; remove only its reserved exterior, never
    # the purchased pack or motor geometry. Preserve actual shell seam/tool paths.
    for n in ['Body_Upper','Body_Lower']:boolean(tub,clone(obj(n),'shell_seat_clear'))
    boolean(tub,reserve('function_button_service',obj('Function_Button'),1.2))
    for sign in [-1,1]:
        boolean(tub,cyl('wheel_axis_bore',(sign*52.5,0,wz),5.25,45,'X'))
        for yy in [-30,30]:boolean(tub,cyl('shell_seam_tool_clear',(sign*b.seam_mount_x(),yy,92),3.3,46))
    for x,y in P['shell_service']['frame_mount_xy_mm']:
        boolean(tub,cyl('frame_screw_pass',(x,y,dz),1.7,12))
        boolean(tub,cyl('frame_tool_shaft',(x,y,111),2.7,38))
    boolean(tub,clone(obj('Yaw_Cable_Clip'),'fixed_wire_clip_clear'))
    for a,bb in zip([(-42,25,137),(-32,10,159)],[(-32,10,159),(-18,0,153)]):
        boolean(tub,b.beam('head_trunk_socket_pass',a,bb,2.5))
    for angle in range(-60,61,5):
        flag=clone(obj('Yaw_Stop_Flag'),'yaw_flag_clear')
        flag.matrix_world=Matrix.Rotation(math.radians(angle),4,'Z')@flag.matrix_world
        boolean(tub,flag)
    boolean(tub,cyl('yaw_loop_space',(0,0,153),19.7,3.4))
    for name in ['Yaw_Stop_-76','Yaw_Stop_76']:
        union(tub,clone(obj(name),'integral_yaw_stop'));remove_generated(name)
    # A short shared bottom cap retains both motors after insertion. It is a
    # maintenance closure, not a long member spanning to the upper deck.
    for yy in [-10.5,10.5]:
        union(tub,cyl('motor_retainer_boss',(0,yy,wz-7),3,6))
        boolean(tub,cyl('motor_retainer_bore',(0,yy,wz-7.5),1.2,12))
        boolean(tub,cyl('motor_retainer_insert_seat',(0,yy,wz-6),1.7,3.2))
    cap=box('Motor_Retainer',(0,0,wz-11.25),(54,26,2.5),.6)
    for index,yy in enumerate([-10.5,10.5]):
        boolean(cap,cyl('cap_pass',(0,yy,wz-11.25),1.2,8))
        screw=cyl('Motor_Retainer_Screw_'+str(index),(0,yy,wz-9),.95,7)
        union(screw,cyl('cap_screw_head',(0,yy,wz-13.3),1.9,1.6))
        hardware(screw,'电机舱短底盖M2螺钉（试配）')
        hardware(ring('Motor_Retainer_Insert_'+str(index),(0,yy,wz-6),1.6,1.1,3),'电机舱底盖M2嵌件（试配）')
    for sign in [-1,1]:
        pad=box('Motor_Retainer_Pad_'+str(sign),(sign*14,0,wz-9.75),(12,12,.5))
        hardware(pad,'电机底部0.5mm试配垫（材料与压缩量待定）')
        pad.data.materials.clear();pad.data.materials.append(MATS['tire']);pad['material_suggestion']='Trial compliant pad; material/compression and motor restraint unverified'
    printed(cap,'双电机共用短底盖 / 可拆装','body','Removable2.5mm local cap retained by2 trialM2 screws;0.5mm trial pads beneath motor cases; motor fasteners, thermal expansion and compression still unverified')
    cap['explode_offset_mm']=[0,0,-26]
    printed(tub,'一体承重舱体 / 电机座与Yaw轴承座集成','body',
            'Open-front continuous tub; integrated wheel-bearing and motor seats, yaw socket, provisional board shelves. Motors insert from below before axes. P1 power80x45 still unplaced; populated board, heat and antenna fit BLOCKED.')

    existing={o.name.removeprefix(PREFIX) for o in parts()}
    b.CONTACTS[:]=[c for c in b.CONTACTS if c['a'] in existing and c['b'] in existing and
                  {c['a'],c['b']}!={'Display_Frame','Pitch_Cradle'}]
    b.contact('Display_Frame','Pitch_Cradle','Short face-to-face attachment directly on pod bulkhead; no overhead cantilever brackets')
    b.contact('Pitch_Yoke','Yaw_Bearing','Integrated bearing journal and cup; radial/axial fits and retention remain provisional')
    b.contact('Load_Frame','Yaw_Bearing','Continuous chassis socket shoulder, no separate carrier or tall posts')
    b.contact('Load_Frame','Battery_Tray','Open-front sliding tray supported by short integral side ledges')
    b.contact('Load_Frame','Motor_Retainer','Short local bottom closure retained by2 trialM2 screws; real motor fastening and pad compression not qualified')
    after={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in targets+['Motor_Retainer'] if bpy.data.objects.get(PREFIX+n)}
    save_json(ROOT/'reports/structure_changes.json',{
        'revision':P['revision'],'before_revision':'V1.2-M1.2','architecture':'MONOCOQUE_PODS_AND_CUP',
        'before':before,'after':after,'support_printed_parts_before':len(before),'support_printed_parts_after':len(after),
        'removed_long_battery_hangers':0,'new_battery_retention_screws':2,
        'new_integral_bodies':['Load_Frame','Pitch_Yoke','Pitch_Cradle'],
        'remaining_service_parts':['Display_Frame','Battery_Tray','Motor_Retainer'],
        'joint_axes_unchanged':True,'vendor_geometry_rescaled':False,
        'geometry_status':'REQUIRES_CURRENT_VALIDATE_RUN','strength_status':'NOT_TESTED',
        'limits':'Continuous tub/cup/pod candidate, not thin beam skeleton. No FEA, fatigue or print strength claim. P1 power80x45 and populated electronics relayout remain BLOCKED.'})
