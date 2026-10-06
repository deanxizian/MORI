"""M1.5: simple modules on a lowered flat deck with no yaw servo recess.

Broad short load paths, explicit trial M2 joints, no buried full-height tub.
Purchased geometry and motion axes are unchanged. No strength qualification.
"""
from common import *
from monocoque_structure import obj,reserve,source_build
from purchased_geometry import remove_generated
from structural_simplification import printed,hardware,volume,plate


def trim_box(o,lo,hi):
    return intersect(o,box('module_trim',[(a+b)/2 for a,b in zip(lo,hi)],[b-a for a,b in zip(lo,hi)]))


def module(o,label,group,orientation,purpose,explode):
    printed(o,label,group,purpose)
    o['simple_support_module']=True;o['print_orientation_candidate']=orientation
    o['functional_purpose']=purpose;o['explode_offset_mm']=list(explode)
    o['mass_effective_fill']=.95
    return o


def joint_z(name,upper,lower,x,y,head_base,nut_z,group='body',recess=False):
    for target in [upper,lower]:boolean(target,cyl('M2_clear',(x,y,head_base-4),P['structure']['simple_modules']['fastener_clearance_radius_mm'],20))
    if recess:boolean(upper,cyl('M2_head_recess',(x,y,head_base+1.2),2.1,2.5))
    boolean(lower,cyl('M2_nut_access',(x,y,nut_z),2.75,2.8,n=6))
    if name.startswith('Drive_'):
        boolean(lower,cyl('open_nut_channel',(x,y,(57+75)/2),2.75,75-57,n=6))
    if name.startswith('Gimbal_Base_'):
        boolean(lower,cyl('open_nut_channel',(x,y,(177+188.4)/2),2.75,188.4-177,n=6))
    screw=cyl(name+'_Screw',(x,y,head_base-6),.95,12)
    union(screw,cyl('M2_head',(x,y,head_base+.8),1.9,1.6))
    hardware(screw,'统一M2×12短螺钉 / '+name,group)
    hardware(ring(name+'_Nut',(x,y,nut_z),2.4,1.1,2.4,n=6),'外露M2螺母 / '+name,group)
    return {'id':name,'axis':'Z','xy_mm':[x,y],'head_base_mm':head_base,'access_direction':'+Z','group':group,
            'upper':upper.name.removeprefix(PREFIX),'lower':lower.name.removeprefix(PREFIX)}


def apply_simple_modules():
    if P.get('structure',{}).get('architecture')!='simple_modules':return
    b=source_build();hz=D['head_z'];wz=D['wheel_z'];dz=P['layout']['deck_z_mm'];s=P['structure']['simple_modules']
    deck_top=dz+P['layout']['deck_thickness_mm']/2
    deck_bottom=dz-P['layout']['deck_thickness_mm']/2
    direct_seat=s.get('flat_servo_seat',False)
    ear_y=s['head_front_ear_y_mm'];ear_dy=ear_y-24;side_x=s['side_plate_abs_x_mm']
    oldnames=['Load_Frame','Pitch_Yoke','Pitch_Cradle','Display_Frame','Battery_Tray','Motor_Retainer']
    before={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in oldnames}
    baseline=P['structure'].get('comparison_baseline')
    if baseline:before=json.loads((PROJECT/baseline['report']).read_text())['after']
    joints=[]

    # Head: one open U, one shallow face retainer. Remove the former full-height
    # front bulkhead; the short local side ears are independently accessible.
    cradle=obj('Pitch_Cradle');clip_y(cradle,-100,28)
    face=obj('Display_Frame')
    for sign in [-1,1]:
        remove_generated('Display_Frame_Screw_'+str(sign));remove_generated('Display_Frame_Nut_'+str(sign))
        # Short wide diagonal ears fit the actual spherical head at the face edge.
        outline=[(31,37.7),(38.5,37.7),(43.8,28),(43.8,21),(40,21),(35,34),(31,34)]
        pts=[(sign*x,y+ear_dy) for x,y in outline]
        verts=[(x,y,hz-6.2+z) for z in [-s['head_front_ear_height_mm']/2,s['head_front_ear_height_mm']/2] for x,y in pts];n=len(pts)
        fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        ear=mesh('short_face_ear',verts,fs);recalc(ear);union(face,ear)
        for z in [hz-6.2,hz+.8]:
            for target in [cradle,face]:boolean(target,cyl('M2_side_clear',(sign*44,ear_y,z),1.2,16,'X'))
            boolean(face,cyl('M2_side_nut',(sign*41.8,ear_y,z),2.75,2.6,'X',6))
            name='Face_Joint_'+str(sign)+'_'+str(round(z-hz,1))
            bolt=cyl(name+'_Screw',(sign*41,ear_y,z),.95,12,'X')
            union(bolt,cyl('M2_head',(sign*47.8,ear_y,z),1.9,1.6,'X'));hardware(bolt,'侧面可达M2×12 / 屏幕框','pitch')
            hardware(ring(name+'_Nut',(sign*41.8,ear_y,z),2.4,1.1,2.4,'X',6),'屏幕短耳M2螺母','pitch')
    union(face,box('camera_short_land',(0,37.4,hz+22),(18,2,10)))
    union(face,box('camera_local_seat',(0,37.4,hz+30),(16,2,12)))
    intersect(face,sphere('face_limit',(0,0,hz),P['structure']['head_pod_outer_radius_mm']))
    for target in [cradle,face]:
        for n in ['Head_Front','Head_Rear','Mic_Duct_L','Mic_Duct_R']:boolean(target,clone(obj(n),'shell_local_relief'))
    module(cradle,'开口U形头托 / 无前围墙','pitch','Rear flat face down; inspect transverse shaft-hole bridges',
           'Two broad cheeks and one flat rear tie support bilateral trunnions and CAM. Front open for wiring and LCD removal.',(0,-45,100))
    cradle['integrated_functions']=['head_trunnions','CAM_back_support']
    module(face,'浅屏幕框 / 短侧耳与相机座','pitch','Face ring down; local ear support may be required',
           'Three original LCD posts; four accessible side M2 screws to open head U; short local camera seat. No suspended overhead frame.',(0,85,80))

    # Yaw: a plain extruded U on a separate rotary base. Only the low thin
    # light-control rim is retained; the deep spherical load-bearing cup goes.
    old=obj('Pitch_Yoke');turn=clone(old,'Yaw_Turntable')
    keep=box('low_turntable_region',(0,0,170),(160,160,35))
    guard=sphere('thin_guard_region',(0,0,hz),57)
    boolean(guard,sphere('no_deep_cup',(0,0,hz),53.5));clip_z(guard,185.2,198)
    union(keep,guard);intersect(turn,keep)
    union(turn,ring('short_turntable_neck',(0,0,187.5),12,8,5))
    union(turn,ring('turntable_flat_flange',(0,0,188.5),20,8,3))
    remove_generated('Pitch_Yoke')
    yd=s['yoke_depth_mm']
    yoke=plate('Pitch_Yoke',[(-36,190),(36,190),(42,196),(-42,196)],0,yd)
    for sign in [-1,1]:
        union(yoke,box('upright_cheek',(sign*39,0,(196+235.5)/2),(s['yoke_arm_thickness_mm'],yd,235.5-196)))
        union(yoke,ring('bearing_local_land',(sign*39,0,hz),8.5,6.25,s['yoke_arm_thickness_mm'],'X'))
    union(yoke,box('servo_back',(-23,-8,hz),(28,3,24)))
    union(yoke,box('servo_floor',(-23,0,hz-12.5),(28,17,3)))
    # Broad short side attachment from servo floor to left U wall.
    union(yoke,box('servo_side_land',(-37,-3,hz-12.5),(5,17,3)))
    boolean(yoke,reserve('servo_clear',obj('Pitch_Servo'),.25))
    for sign in [-1,1]:boolean(yoke,cyl('pitch_bore',(sign*39,0,hz),6.25,16,'X'))
    for angle in [-28,33]:
        ca=math.cos(math.radians(angle));sa=math.sin(math.radians(angle))
        union(yoke,box('pitch_stop',(39,-10*ca,hz-10*sa),(4,3,3)))
    for target in [turn,yoke]:
        for a,bb in zip([(0,0,182),(31,-5,204)],[(31,-5,204),(32,0,hz-4)]):boolean(target,b.beam('wire_bore',a,bb,2.5))
    for x in [-13,13]:joints.append(joint_z('Gimbal_Base_'+str(x),yoke,turn,x,yd/2-2,196,187,'yaw'))
    module(turn,'Yaw短转台 / 薄遮光边','yaw','Rotary axis vertical; check thin rim support',
           'Bearing journal, short top flange and thin lower light-control rim. Deep structural bowl removed.',(0,-15,55))
    module(yoke,'平面U形俯仰托 / 双侧轴承','yaw','Broad Y face down; local servo shelf may need support',
           'Plain wide U with bilateral bearings, short servo saddle and two downward M2 joints to rotary base.',(0,-35,80))

    # Body: top deck, two flat cheeks, shallow drive bridge, removable yaw socket.
    former=obj('Load_Frame');drive=clone(former,'Drive_Bridge');trim_box(drive,(-100,-13,0),(100,13,78))
    yawbase=ring('Yaw_Base',(0,0,(deck_top+154.8)/2),25,21.5,154.8-deck_top)
    access_top=154
    boolean(yawbase,box('servo_front_access',(0,16,(deck_top+access_top)/2),(36,24,access_top-deck_top+.2)))
    union(yawbase,ring('bearing_lower_step',(0,0,155.7),25,10.2,1.8))
    union(yawbase,ring('bearing_wall',(0,0,161),25,16.3,10))
    union(yawbase,ring('bearing_seat',(0,0,157.5),20,10.2,2))
    clip_y(yawbase,-19.2,100)
    for n in ['Yaw_Servo','Yaw_Cable_Clip']:boolean(yawbase,reserve('socket_local_clear',obj(n),.3))
    boolean(yawbase,cyl('yaw_loop_space',(0,0,153),19.7,3.4))
    for a,bb in zip([(-42,25,137),(-32,10,159)],[(-32,10,159),(-18,0,153)]):boolean(yawbase,b.beam('trunk_pass',a,bb,2.5))
    for angle in [-76,76]:
        xx=14*math.cos(math.radians(angle));yy=14*math.sin(math.radians(angle))
        union(yawbase,box('fixed_yaw_stop',(xx,yy,154),(3,3,3)))
    remove_generated('Load_Frame')
    deck=cyl('Load_Frame',(0,0,dz),70,P['layout']['deck_thickness_mm']);intersect(deck,box('deck_plan',(0,0,dz),(116,100,8)))
    union(deck,box('mcu_flat_seat',(0,-37.75,deck_top+1.25),(74,35.5,2.5)))
    union(deck,box('imu_flat_seat',(42,20,deck_top+.5),(24,20,1)))
    if not direct_seat:
        union(deck,box('servo_floor',(0,0,126.5),(30,19,2)))
        for sign in [-1,1]:union(deck,box('servo_side',(sign*14,0,130),(3,19,8)))
    for n in ['Yaw_Servo','MCU_Motion','Body_IMU','Speaker_Mount','Speaker']:
        if n=='Yaw_Servo' and direct_seat:continue
        boolean(deck,reserve('local_module_clear',obj(n),.3))
    boolean(deck,box('front_service_notch',(0,50,dz),(44,28,8)))
    for x,y in P['shell_service']['frame_mount_xy_mm']:boolean(deck,cyl('shell_bolt_pass',(x,y,dz),1.7,14))
    for n in ['Body_Upper','Body_Lower']:boolean(deck,clone(obj(n),'deck_shell_clear'))
    union(drive,box('short_drive_roof',(0,0,78-s['drive_roof_thickness_mm']/2),(s['drive_roof_width_mm'],s['drive_roof_depth_mm'],s['drive_roof_thickness_mm'])))
    for sign in [-1,1]:
        union(drive,box('short_bearing_web',(sign*30.5,0,60),(9,24,36)))
        boolean(drive,cyl('axle_bore',(sign*43,0,wz),5.25,29,'X'))
        boolean(drive,cyl('output_bore',(sign*26.5,0,wz),7.3,5.6,'X'))
        boolean(drive,box('output_install_slot',(sign*26.5,0,20),(5.6,14.6,55)))
    intersect(drive,b.body_outer('drive_body_limit',P['shell_thickness_mm']+.6))
    cheeks=[]
    for sign,n in [(-1,'L'),(1,'R')]:
        cheek=box('Body_Cheek_'+n,(sign*side_x,0,(78+deck_bottom)/2),(s['side_plate_thickness_mm'],s['side_plate_y_span_mm'],deck_bottom-78))
        union(cheek,box('lower_flat_foot',(sign*(side_x-5),0,79.75),(12,s['side_plate_y_span_mm'],3.5)))
        union(cheek,box('upper_flat_foot',(sign*(side_x-5),0,deck_bottom-1.75),(12,28,3.5)))
        # Existing tray's short retaining screw remains externally accessible.
        union(cheek,box('tray_retainer_land',(sign*47,20,88),(3,9,13)))
        boolean(cheek,cyl('tray_retainer_clear',(sign*47,20,88),1.2,18,'X'))
        boolean(cheek,cyl('tray_screw_head_clear',(sign*51,20,88),2.3,5,'X'))
        boolean(cheek,reserve('tray_slide_clear',obj('Battery_Tray'),.3))
        for y in [-8,8]:
            joints.append(joint_z('Deck_'+n+'_'+str(y),deck,cheek,sign*(side_x-5),y,deck_top,deck_bottom-4.9))
            joints.append(joint_z('Drive_'+n+'_'+str(y),cheek,drive,sign*(side_x-5),y,79.9,73.6,recess=True))
        for shell in ['Body_Upper','Body_Lower']:boolean(cheek,clone(obj(shell),'shell_clear'))
        module(cheek,'平侧板与短折边 '+n,'body','Broad X face down; local foot orientation test',
               'One flat cheek connects deck to drive bridge; short lower ledge carries sliding battery tray. Four M2 joints from above.',(sign*65,0,0))
        cheeks.append(cheek)
    for sign in [-1,1]:
        union(yawbase,box('socket_short_ear',(sign*28,0,deck_top+2),(10,10,4)))
        joints.append(joint_z('Yaw_Base_'+str(sign),yawbase,deck,sign*29,0,deck_top+4,deck_bottom-1.4))
    module(deck,'降低平板 / 舵机平放与板卡安装面','body','Uninterrupted lower plane on bed; no servo recess or underside shelf',
           'Lowered flat deck directly supports yaw servo bottom; no central hole, recessed shelf or side cradle. MCU and rigid IMU seats follow the deck. Final servo-ear restraint remains Stage B.',(0,0,35))
    module(drive,'浅双电机底托 / 短轴承座','body','Motor opening upward; verify bearing-bore bridges',
           'Short motor cages and local wheel-bearing webs under a shallow shared roof. Motors enter from below; cap stays removable.',(0,0,-35))
    module(yawbase,'可拆圆筒Yaw轴承座','body','Flat flange down; bearing fit coupon before full print',
           'Same bearing height, continuous socket extends to lowered deck with two accessible M2 ears; no separate spacer or posts. Servo rests directly on flat deck.',(0,-45,50))
    for n in ['Battery_Tray','Motor_Retainer']:
        obj(n)['simple_support_module']=True;obj(n)['mass_effective_fill']=.95
        obj(n)['print_orientation_candidate']='Largest flat face down'
    # Keep only extant declared interfaces. Nominal contact never waives overlaps.
    existing={o.name.removeprefix(PREFIX) for o in parts()}
    b.CONTACTS[:]=[c for c in b.CONTACTS if c['a'] in existing and c['b'] in existing and not ({c['a'],c['b']} & {'Load_Frame','Pitch_Yoke'})]
    for j in joints:b.contact(j['upper'],j['lower'],'Flat mating faces with accessible trial M2 through-joint; thread engagement and print strength pending')
    b.contact('Pitch_Yoke','Pitch_Bearing_L','Bilateral bearing seats, provisional fit');b.contact('Pitch_Yoke','Pitch_Bearing_R','Bilateral bearing seats, provisional fit')
    b.contact('Yaw_Turntable','Yaw_Bearing','Journal carries rotating load; axial retention pending vendor selection')
    b.contact('Yaw_Servo','Load_Frame','Servo bottom directly on uninterrupted flat deck; anti-rotation/ear fastening awaits purchased revision')
    after_names=['Load_Frame','Drive_Bridge','Body_Cheek_L','Body_Cheek_R','Yaw_Base','Pitch_Cradle','Display_Frame','Pitch_Yoke','Yaw_Turntable','Battery_Tray','Motor_Retainer']
    after={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in after_names}
    save_json(ROOT/'reports/module_assembly.json',{'revision':P['revision'],'joints':joints,
        'flat_deck':{'top_z_mm':deck_top,'bottom_z_mm':deck_bottom,'servo_base_z_mm':bounds(obj('Yaw_Servo'))[2][0],
                     'servo_center_pocket':False if direct_seat else True,'yaw_bearing_height_preserved':True,
                     'servo_retention':'Final anti-rotation and installation-ear fastening remain blocked pending purchased revision; bottom seating alone is not fastening approval'},
        'side_face_joints':{'count':4,'axis':'X','y_mm':ear_y,'z_relative_head_mm':[-6.2,.8],'direction':'outward left/right','prerequisite':'Head front/rear shells removed; LCD seated on removable face bracket on bench'},
        'removed_material_functions':['full chassis rear wall','full body tub side enclosure','old provisional power and USB scaffold','tall head front bulkhead','deep structural gimbal bowl'],
        'limits':'M2 thread envelopes and access shafts are trial geometry, not supplier threads or full tool-handle proof. Unknown P1 power/USB final mounting remains BLOCKED.'})
    save_json(ROOT/'reports/structure_changes.json',{'revision':P['revision'],'before_revision':baseline['revision'] if baseline else 'V1.2-M1.3','architecture':'SIMPLE_OPEN_MODULES','before':before,'after':after,
        'support_printed_parts_before':len(before),'support_printed_parts_after':len(after),
        'new_integral_bodies':after_names,'remaining_service_parts':['Display_Frame','Battery_Tray','Motor_Retainer'],
        'joint_axes_unchanged':True,'vendor_geometry_rescaled':False,'geometry_status':'REQUIRES_CURRENT_VALIDATE_RUN','strength_status':'NOT_TESTED',
        'limits':'Eleven simple modules retained; lower deck removes servo recess with no extra spacer or support parts. Weight estimated with95% effective fill; no print/strength/actual assembly claim. P1 electronics remain unplaced.'})
