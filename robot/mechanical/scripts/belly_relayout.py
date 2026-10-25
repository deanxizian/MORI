"""M1.9: horizontal wheel drives and head-carried yaw case with a fixed reaction link.

Only parameterized mechanical geometry is generated here. Unselected electronics
remain capacity allocations. Trial hardware and horn clamping are not load-qualified.
"""
from common import *
from monocoque_structure import obj,reserve,source_build
from purchased_geometry import remove_generated
from simple_modules import module,joint_z
from structural_simplification import hardware,volume
import yaw_bridge_mount

def relocate(o,tr,group=None):
    o.matrix_world=tr@o.matrix_world
    if group:o['group']=group
    SOLIDS.pop(o.name,None);bpy.context.view_layer.update()

def erase_prefix(prefix):
    for o in list(bpy.context.scene.objects):
        if o.get('mori_owner')==OWNER and o.name.startswith(PREFIX+prefix):remove_generated(o.name.removeprefix(PREFIX))

def keyed_cylinder(name,z0,z1,r,flat_x):
    o=cyl(name,(0,0,(z0+z1)/2),r,z1-z0)
    intersect(o,box('D_flat_limit',(-20+flat_x/2,0,(z0+z1)/2),(40+flat_x,40,z1-z0+2)))
    return o

def apply_belly_relayout():
    s=P.get('belly_relayout',{})
    if not s.get('enabled'):return
    b=source_build();hz=D['head_z'];wz=D['wheel_z'];deck_top=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text())
    plan['joints']=[j for j in plan['joints'] if not j['id'].startswith('Yaw_Base_')]
    old_coords={n:bounds(obj(n)) for n in ['Drive_Motor_L','Drive_Motor_R','Yaw_Servo','Battery','Load_Frame','Power_Module']}

    # Each S288 keeps its output centre; opposite clocking balances the fore-aft
    # offset. Both output faces are transformed with the body, never rescaled.
    for side,sign in [('L',-1),('R',1)]:
        c=Vector((sign*P['drive']['motor_center_abs_x_mm'],0,wz))
        tr=Matrix.Translation(c)@Matrix.Rotation(math.radians(s['wheel_servo_rotation_deg'][side]),4,'X')@Matrix.Translation(-c)
        for n in ['Drive_Motor_'+side,'S288_Output_'+side+'_Inner','S288_Output_'+side+'_Outer']:
            relocate(obj(n),tr)
        obj('Drive_Motor_'+side)['mount_orientation']='Horizontal90deg about grounded X output axis; original body/output dimensions'
    drive=obj('Drive_Bridge');roof=wz+P['structure']['simple_modules']['drive_roof_top_from_axle_mm']
    boolean(drive,box('remove_old_vertical_motor_seats',(0,0,(roof-3-100)/2),(56,110,roof-3+100)))
    union(drive,box('horizontal_motor_roof',(0,0,roof-1.5),(56,56.6,3)))
    floor=wz-10.5
    for sign in [-1,1]:
        union(drive,box('horizontal_case_side',(sign*26,0,(floor+roof-2)/2),(3,56.6,roof-2-floor)))
        union(drive,box('horizontal_case_end',(0,sign*26.3,(floor+roof-2)/2),(54,3,roof-2-floor)))
        boolean(drive,cyl('S288_output_pass',(sign*26.5,0,wz),7.3,5.6,'X'))
        boolean(drive,box('output_insertion_slot',(sign*26.5,0,wz-30),(5.6,14.6,60)))
    erase_prefix('Motor_Retainer')
    cap=box('Motor_Retainer',(0,0,floor-1.25),(55,56.6,2.5),.5)
    for index,y in enumerate([-20,20]):
        union(drive,cyl('motor_bottom_screw_boss',(0,y,(floor+roof-2)/2),3.2,roof-2-floor))
        boolean(drive,cyl('motor_bottom_screw_clear',(0,y,floor+4),1.2,14))
        boolean(drive,cyl('motor_bottom_insert_pocket',(0,y,floor+3.5),1.7,3.4))
        boolean(cap,cyl('motor_bottom_clear',(0,y,floor-1),1.2,8))
        screw=cyl('Motor_Retainer_Screw_'+str(index),(0,y,floor+1.5),.95,8)
        union(screw,cyl('M2_head',(0,y,floor-3.3),1.9,1.6));hardware(screw,'底盖M2×8试配螺钉')
        hardware(ring('Motor_Retainer_Insert_'+str(index),(0,y,floor+3.5),1.6,1.1,3),'底盖M2试配嵌件')
    for side,sign in [('L',-1),('R',1)]:
        o=obj('Drive_Motor_'+side);bb=bounds(o);ym=(bb[1][0]+bb[1][1])/2
        pad=box('Motor_Retainer_Pad_'+str(sign),(sign*14,ym,floor+.25),(12,12,.5));hardware(pad,'轮驱底部软垫，压缩量待测')
        pad.data.materials.clear();pad.data.materials.append(MATS['tire'])
        boolean(drive,reserve('motor_assembly_clear',o,P.get('wheel_interface',{}).get('motor_seat_clearance_per_side_mm',.3)))
    module(drive,'横躺双轮驱浅座 / 独立轮轴承','body','Roof flat on bed, cavity up; local bearing openings require trials',
           'Opposed90deg S288 seats, shallow shared roof and independent wheel-bearing webs. Motors enter from below; output/shaft locations unchanged.',(0,0,-35))
    module(cap,'横躺轮驱共用底盖','body','Broad lower plane down','Two accessible trial M2 screws and local compliant pads. Real cable outlet, retention preload and thermal clearance pending.',(0,0,-50))

    # Inverted yaw: the servo CASE moves with yaw, while its spline/horn is held
    # by a removable keyed reaction stem belonging to the stationary body.
    tip_old=Vector((0,0,bounds(obj('Yaw_Output'))[2][1]));tip_z=hz+s['yaw_output_tip_from_head_mm']
    tr=Matrix.Translation((0,0,tip_z))@Matrix.Rotation(math.radians(s['yaw_case_clock_deg']),4,'Z')@Matrix.Rotation(math.pi,4,'X')@Matrix.Translation(-tip_old)
    for n in ['Yaw_Servo','Yaw_Output','Yaw_Horn','Yaw_Lock_Screw']:
        relocate(obj(n),tr,'yaw' if n=='Yaw_Servo' else 'body')
    obj('Yaw_Servo')['mount_orientation']='Inverted in head; yaw-only case. Body-fixed horn makes head yaw opposite shaft angle relative to case.'
    obj('Yaw_Horn')['interface_status']='Unselected20T mating horn envelope; clamped to body reaction link. Exact purchased horn and clamp torque remain BLOCKED.'
    yoke=obj('Pitch_Yoke');turn=obj('Yaw_Turntable')
    union(yoke,box('wider_reaction_opening_land',(0,0,hz-34),(40,32,6)))
    union(yoke,box('front_servo_mount_foot',(0,17,hz-34),(12,12,6)))
    boolean(yoke,cyl('fixed_collar_sweep_clear',(0,0,hz-33),12,24))
    boolean(turn,cyl('stationary_reaction_stem_clear',(0,0,175),s['reaction_stem_clearance_radius_mm'],70))
    ear_bottom=tip_z+(28.45-19.15)-.75;floor_top=hz-31
    # Short broad shelves under documented servo ears; the rear shelf bridges
    # over the fixed collar instead of occupying its yaw sweep.
    union(yoke,box('rear_servo_shelf',(0,-11.5,ear_bottom-1),(12,10,2)))
    union(yoke,box('rear_servo_short_wall',(0,-15,(floor_top+ear_bottom-1)/2),(12,3,ear_bottom-1-floor_top)))
    union(yoke,box('front_servo_short_wall',(0,20,(floor_top+ear_bottom)/2),(12,5.0,ear_bottom-floor_top)))
    for index,y in enumerate([-8.55,19.95]):
        top=ear_bottom+1.5;nut_z=ear_bottom-3.2
        boolean(yoke,cyl('servo_ear_screw_clear',(0,y,ear_bottom-1),1.2,12))
        boolean(yoke,cyl('servo_ear_nut_pocket',(0,y,nut_z),2.75,2.6,n=6))
        # Open pocket toward the accessible side, allowing nut insertion.
        boolean(yoke,box('servo_nut_side_access',(0,y+(4 if y>0 else -4),nut_z),(5.5,8,2.6)))
        screw=cyl('Head_Yaw_Ear_'+str(index)+'_Screw',(0,y,top-2.5),.95,5)
        union(screw,cyl('M2_head',(0,y,top+.8),1.9,1.6));hardware(screw,'头内Yaw安装耳M2×5试配','yaw')
        hardware(ring('Head_Yaw_Ear_'+str(index)+'_Nut',(0,y,nut_z),2.4,1.1,2.4,n=6),'头内Yaw安装耳M2螺母','yaw')
    # Reapply holes after adding the broad mounting lands.
    boolean(yoke,cyl('fixed_clamp_sweep_clear',(0,0,tip_z-3),13.5,11))
    boolean(yoke,clone(obj('Yaw_Servo'),'yaw_case_seat_clear'))
    for x in [-13,13]:boolean(yoke,cyl('restored_gimbal_hole',(x,P['structure']['simple_modules']['yoke_depth_mm']/2-2,hz-35),1.2,20))
    if not P.get('head_routing',{}).get('defer_design'):
        for a,bb in zip(yaw_head_lead_points(),yaw_head_lead_points()[1:]):boolean(yoke,b.beam('restored_wire_bore',a,bb,2.5))
        # Keep a shallow open channel clear through every sampled pitch cable pose.
        for angle in range(-20,26,5):
            route=clone(obj('Screen_Lead'),'screen_route_sweep')
            route.matrix_world=Matrix.Translation((0,0,hz))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation((0,0,-hz))@route.matrix_world
            SOLIDS.pop(route.name,None);bpy.context.view_layer.update();boolean(yoke,route)
    module(yoke,'双侧俯仰U托 / 头内倒装Yaw短耳座','yaw','Broad Y face down; inspect short shelf supports',
           'Bilateral pitch bearings plus two short broad shelves under vendor-documented yaw-servo ears. Central opening passes a separate stationary reaction link.',(0,-35,80))

    # Open body bridge: two broad plate legs leave a continuous PCB bay below.
    erase_prefix('Yaw_Base_');remove_generated('Yaw_Base')
    roof_z=s['yaw_bridge_roof_z_mm'];th=s['yaw_bridge_roof_thickness_mm'];half=s['yaw_bridge_half_width_mm'];dep=s['yaw_bridge_depth_mm'];leg=s['yaw_bridge_leg_thickness_mm']
    base=box('Yaw_Base',(0,0,roof_z),(2*half,dep,th))
    for sign in [-1,1]:
        union(base,box('yaw_bridge_side_plate',(sign*(half-leg/2),0,(deck_top+roof_z)/2),(leg,dep,roof_z-deck_top)))
        if not yaw_bridge_mount.S.get('enabled'):
            union(base,box('yaw_bridge_foot',(sign*(half+1),0,deck_top+2),(12,12,4)))
    bz=D['yaw_bearing_construction_z']
    union(base,ring('bearing_lower_wall',(0,0,(roof_z+bz-1)/2),27,16.3,bz-1-roof_z))
    union(base,ring('bearing_wall',(0,0,bz-1),27,16.3,10))
    union(base,ring('bearing_seat',(0,0,bz-4.5),20,10.2,2))
    loop_r=P['head_joint']['yaw_service_loop_radius_mm'];loop_z=yaw_servo_z_mm(26)
    boolean(base,ring('yaw_service_ring_space',(0,0,loop_z),loop_r+1.7,loop_r-1.7,3.4))
    for angle in [-76,76]:
        x=14*math.cos(math.radians(angle));y=14*math.sin(math.radians(angle))
        union(base,box('yaw_fixed_stop',(x,y,D['yaw_stop_construction_z']),(3,3,3)))
    socket_bottom=s['reaction_socket_bottom_z_mm'];seat=s['reaction_stem_seat_z_mm']
    union(base,cyl('reaction_key_socket',(0,0,(socket_bottom+roof_z+1.5)/2),9,roof_z+1.5-socket_bottom))
    boolean(base,cyl('reaction_axial_driver_access',(0,0,roof_z-5),1.8,24))
    boolean(base,keyed_cylinder('D_key_socket',seat,roof_z+3,6.2,4.7))
    rz=s['reaction_retainer_z_mm']
    boolean(base,cyl('reaction_cross_screw',(0,0,rz),1.2,26,'Y'))
    boolean(base,cyl('reaction_cross_nut',(0,-7.4,rz),2.75,3.2,'Y',6))
    if yaw_bridge_mount.S.get('enabled'):
        plan['joints']+=yaw_bridge_mount.bridge_joints(base)
    else:
        for sign in [-1,1]:
            plan['joints'].append(joint_z('Yaw_Base_'+str(sign),base,obj('Load_Frame'),sign*(half+1),0,deck_top+4,deck_top-5.4))
    # Clear deck screw heads; deck is installed before this removable bridge.
    for n in ['Deck_L_-8_Screw','Deck_L_8_Screw','Deck_R_-8_Screw','Deck_R_8_Screw']:
        if not P.get('layout_cleanup',{}).get('merge_deck_and_cheeks'):
            boolean(base,reserve('deck_head_pocket',obj(n),.25))
    for sign,side in [(-1,'L'),(1,'R')]:
        if yaw_bridge_mount.S.get('enabled'):continue
        xx=sign*(half+1)
        boolean(base,cyl('bridge_screw_head_access',(xx,0,deck_top+22),2.2,36))
        cheek=obj('Body_Cheek_'+side)
        boolean(cheek,cyl('bridge_bolt_clear',(xx,0,deck_top-4),1.2,18))
        boolean(cheek,cyl('bridge_nut_access',(xx,0,deck_top-5.4),2.75,3.2,n=6))
    # Local cable passage through the bridge; retain a tangible guide on the ring.
    union(base,ring('fixed_tangent_guide',(-22,0,loop_z),3,1.8,4,'Y'))
    boolean(base,cyl('fixed_tangent_pass',(-22,0,loop_z),1.8,8,'Y'))
    for a,bb in zip([(-42,25,137),(-32,10,159)],[(-32,10,159),(-22,0,153)]):boolean(base,b.beam('body_trunk_bridge_clear',a,bb,2.5))
    module(base,'开口Yaw承重桥 / 板卡上方跨接','body','Bridge roof down; inspect bearing and keyed socket local support',
           'Two broad short side plates carry a bearing ring above the board bay. Removable keyed reaction stem retained separately; shell is not the primary load path.',(0,-45,50))

    # Removable, hollow, D-keyed reaction link. The split upper socket clamps an
    # unselected horn; preload and torque transfer require a real horn/print test.
    collar_z=tip_z+1.0
    tidy=P.get('fastener_cleanup',{});rc=tidy.get('reaction_clamp') if tidy.get('enabled') else None
    link=cyl('Yaw_Reaction_Link',(0,0,(seat+collar_z)/2),s['reaction_stem_radius_mm'],collar_z-seat)
    boolean(link,box('stem_bottom_D_flat',(10,0,seat+6),(11,20,12)))
    union(link,cyl('split_horn_socket',(0,0,tip_z+.5),rc['collar_outer_radius_mm'] if rc else 10,7))
    horn_bottom=bounds(obj('Yaw_Horn'))[2][0]
    boolean(link,cyl('horn_radial_seat',(0,0,horn_bottom+3),5.2,6))
    boolean(link,cyl('servo_cap_radial_clear',(0,0,tip_z+5),6.4,5))
    boolean(link,cyl('axial_tool_bore',(0,0,(seat+tip_z+5)/2),1.6,tip_z+5-seat+2))
    boolean(link,cyl('spline_tip_clear',(0,0,tip_z+2),2.1,8))
    boolean(link,box('clamp_split',(8,0,tip_z+1),(12,.8,8)))
    if rc:
        cx=rc['screw_x_mm'];hy=rc['screw_head_base_y_mm'];ny=rc['nut_center_y_mm']
        boolean(link,cyl('clamp_M2_cross',(cx,0,tip_z-.5),1.2,30,'Y'))
        boolean(link,cyl('clamp_nut_in_body',(cx,(-20+ny+1.4)/2,tip_z-.5),2.75,20+ny+1.4,'Y',6))
        boolean(link,cyl('clamp_recessed_head',(cx,(hy+20)/2,tip_z-.5),rc['head_counterbore_radius_mm'],20-hy,'Y'))
    else:
        for yy in [-4.8,4.8]:union(link,box('clamp_local_ear',(8,yy,tip_z-.5),(5,4,3)))
        boolean(link,cyl('clamp_M2_cross',(8,0,tip_z-.5),1.2,20,'Y'))
        boolean(link,cyl('clamp_nut_pocket',(8,-5,tip_z-.5),2.75,2.6,'Y',6))
        boolean(link,cyl('clamp_head_access',(8,6.8,tip_z-.5),2.1,3.4,'Y'))
    boolean(link,cyl('reaction_cross_clear',(0,0,rz),1.2,20,'Y'))
    module(link,'可拆固定反力轴 / D形定位与舵盘夹口','body','Axis vertical; keyed fit and split-clamp coupon required',
           'Carries reaction torque, not head weight. D-key socket and cross screw prevent rotation/lift; split horn socket requires real-horn preload/torque testing. Axial bore gives locking-screw tool access before cross screw insertion.',(0,0,65))
    for name,x,z,ylen,head_y,nut_y in [('Yaw_Reaction_Clamp',8,tip_z-.5,12,6.8,-5),('Yaw_Reaction_Retainer',0,rz,18,9.8,-7.4)]:
        mid=0
        if rc and name=='Yaw_Reaction_Clamp':
            x=rc['screw_x_mm'];ylen=rc['screw_length_mm'];head_y=rc['screw_head_base_y_mm']+.8;nut_y=rc['nut_center_y_mm'];mid=rc['screw_head_base_y_mm']-ylen/2
        screw=cyl(name+'_Screw',(x,mid,z),.95,ylen,'Y');union(screw,cyl('M2_head',(x,head_y,z),1.9,1.6,'Y'));hardware(screw,'固定反力连接M2试配螺钉')
        hardware(ring(name+'_Nut',(x,nut_y,z),2.4,1.1,2.4,'Y',6),'固定反力连接M2螺母')

    # Real mechanical carrier, clearly separate from unknown populated PCB.
    power=obj('Power_Module');center=P['layout']['power_allocation_center_mm'];old=Vector([(a+bb)/2 for a,bb in bounds(power)])
    relocate(power,Matrix.Translation(Vector(center)-old))
    power['label_zh']='电源板可用包络80×40×18 / 非实板';power['interface_status']='Mechanical capacity target only; S3 board outline, populated height, connectors and mounting holes still unknown.'
    power['model_fidelity']='ALLOCATION_ONLY';power['unknown_dimensions']='All actual S3 populated PCB dimensions/holes. This box is a proposed capacity, not supplier geometry.'
    carrier=box('Power_Board_Carrier',s['power_carrier_center_mm'],s['power_carrier_xyz_mm'])
    top=s['power_carrier_center_mm'][2]+s['power_carrier_xyz_mm'][2]/2
    for index,(x,y) in enumerate(s['power_carrier_mount_xy_mm']):
        plan['joints'].append(joint_z('Power_Carrier_'+str(index),carrier,obj('Load_Frame'),x,y,top,deck_top-5.4,length=8))
    # Keep the raised, rigid IMU seat independent of the removable carrier.
    boolean(carrier,box('IMU_carrier_notch',(-32,43,116),(20.4,33,10)))
    # Slots are design attachment options, not a guessed PCB hole pattern.
    for x in [-32,32]:
        slot=box('carrier_adjust_slot',(x,6,top),(3,22,6),.9);boolean(carrier,slot)
    module(carrier,'电源板可拆平托板 / 安装孔待实板','body','Flat lower face down','Four carrier-to-frame screws plus adjustment slots. PCB-specific supports/clamps and thermal clearance remain Stage B; no fabricated vendor hole pattern.',(0,45,35))

    # The lowered deck needs local service cutouts for existing full modules.
    deck=obj('Load_Frame');deck['label_zh']='降低平板 / 电池上方与板卡安装面'
    obj('MCU_Motion')['label_zh']='运动/轮驱接口载板70×35×12预留 / 实板装件待核'
    intersect(deck,box('lower_deck_side_trim',(0,0,113),(110,180,30)))
    boolean(deck,reserve('USB_module_clear',obj('USB_Charge'),.5))
    for n in [o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(PREFIX+'Frame_Insert_')]:boolean(deck,reserve('frame_insert_clear',obj(n),.1))
    # Complete the lower yaw cable branch from the annular service-loop volume.
    lower_points=[(22,0,loop_z),(22,0,164),(14,0,hz-45)]
    q=None
    for a,bb in zip(lower_points,lower_points[1:]):
        seg=b.beam('lower_yaw_wire',a,bb,1.2)
        if q is None:q=seg
        else:union(q,seg)
        if not P.get('head_routing',{}).get('defer_design'):
            boolean(turn,b.beam('lower_yaw_wire_channel',a,bb,2.3))
    q.name=PREFIX+'Yaw_Lower_Lead';finish(q,'PLACEHOLDER','Yaw下段走线预留 / 服务环至头部','copper','yaw',False,role='routing',note='Tube allocation only, no flexible-cable fatigue or actual connector release')
    boolean(base,ring('service_loop_vertical_exit',(0,0,157),23.7,20.3,12))
    existing={o.name.removeprefix(PREFIX) for o in parts()}
    changed={'Yaw_Servo','Yaw_Output','Yaw_Horn','Yaw_Base','Yaw_Turntable','Drive_Bridge','Motor_Retainer','Power_Module'}
    b.CONTACTS[:]=[c for c in b.CONTACTS if c['a'] in existing and c['b'] in existing and not ({c['a'],c['b']} & changed)]
    for a,bb,reason in [('Yaw_Base','Yaw_Bearing','Axial shoulder below bearing; fit/retention pending supplier'),('Yaw_Bearing','Yaw_Turntable','Bearing supports head gravity; journal fit pending'),('Yaw_Base','Yaw_Reaction_Link','Removable D-key with cross-screw retention; nominal print clearance'),('Yaw_Horn','Yaw_Reaction_Link','Split-clamp interface; horn diameter/preload/torque NOT_TESTED'),('Yaw_Servo','Pitch_Yoke','Two short ear shelves with documented-hole-pattern trial bolts'),('Power_Module','Power_Board_Carrier','Allocation bottom on carrier; not a PCB mounting qualification')]:b.contact(a,bb,reason)
    for j in plan['joints']:b.contact(j['upper'],j['lower'],'Trial printed M2 joint; thread/fit and tool handle not certified')
    plan['flat_deck']={'top_z_mm':deck_top,'bottom_z_mm':deck_top-P['layout']['deck_thickness_mm'],'yaw_servo_on_deck':False,'battery_to_deck_nominal_gap_mm':5,'servo_retention':'Head yaw ear shelves + M2 trial fasteners; final unit/horn clamping unverified'}
    plan['additional_assembly']='Install body bridge/bearing, rotating journal, removable keyed reaction link/horn, THEN lower the yaw U support over the link, and finally fit the inverted yaw servo. Assemble centre horn lock through axial bore before inserting reaction cross screw. Real bought horn and tools still require bench check.'
    save_json(ROOT/'reports/module_assembly.json',plan)
    change=json.loads((ROOT/'reports/structure_changes.json').read_text())
    names=['Load_Frame','Drive_Bridge','Body_Cheek_L','Body_Cheek_R','Yaw_Base','Yaw_Reaction_Link','Pitch_Cradle','Display_Frame','Pitch_Yoke','Yaw_Turntable','Battery_Tray','Motor_Retainer','Power_Board_Carrier']
    change.update(after={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in names},support_printed_parts_after=len(names),new_integral_bodies=names,remaining_service_parts=['Display_Frame','Battery_Tray','Motor_Retainer','Yaw_Reaction_Link','Power_Board_Carrier'],limits='M1.9 actual combined relayout: horizontal wheel motors, inverted head yaw case, independent bearing and removable body reaction link. Lowered battery/deck and a supported power-board capacity allocation. Hardware fit/strength/dynamics remain unqualified.')
    save_json(ROOT/'reports/structure_changes.json',change)
    save_json(ROOT/'reports/belly_relayout_geometry.json',{'revision':P['revision'],'prior_intermediate_coordinates':old_coords,'source':'config/geometry.json#/belly_relayout','final_parts':{n:bounds(obj(n)) for n in names+['Drive_Motor_L','Drive_Motor_R','Yaw_Servo','Yaw_Output','Battery','MCU_Motion','Body_IMU','Power_Module']},'power_board_state':'ALLOCATION_ONLY_NOT_ACTUAL_PCB','yaw_drive_relation':'yaw case rotates; output/horn/reaction link body-fixed; head_yaw=-shaft_relative_angle after calibration','strength':'NOT_TESTED','geometry_status':'REQUIRES_VALIDATE'})
    print('BELLY_RELAYOUT_COMPLETE',flush=True)
