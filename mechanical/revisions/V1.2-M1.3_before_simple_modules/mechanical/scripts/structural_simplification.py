"""Replace slender support spans with plate webs and integral load paths.

Printed study geometry only: no stiffness, fatigue or FDM strength qualification.
Vendor bodies, joint axes and the external shell geometry are never rescaled.
"""
from common import *
from purchased_geometry import remove_generated


def plate(name, outline, center, thickness, normal='Y'):
    """Closed extruded planar polygon; outline in XZ for Y, YZ for X."""
    verts=[]
    for q in [center-thickness/2,center+thickness/2]:
        verts += [(u,q,v) if normal=='Y' else (q,u,v) for u,v in outline]
    n=len(outline)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh(name,verts,faces);recalc(o);return o


def printed(o,label,group='body',note=''):
    offsets={'Pitch_Cradle':(0,0,110),'Display_Frame':(0,95,105),'Pitch_Yoke':(0,-20,95),
             'Yaw_Carrier':(0,0,50),'Load_Frame':(0,0,20),'Battery_Tray':(0,65,-10),
             'Motor_Mount_L':(-40,0,0),'Motor_Mount_R':(40,0,0)}
    finish(o,'PRINTABLE',label,'frame',group,True,explode=offsets.get(o.name.removeprefix(PREFIX),(0,0,0)),note=note or
           'Integral plate/web candidate; source hardware unchanged. Printed strength, screws and fits require physical samples.')
    o['model_fidelity']='DESIGN_GEOMETRY';o['structural_revision']=P['revision']
    return o


def hardware(o,label,group='body'):
    finish(o,'PLACEHOLDER',label,'metal',group,False,note='Trial fastener envelope; supplier, thread/engagement and printing fits not released')
    o['model_fidelity']='ALLOCATION_ONLY';o['measured_unit']=False;o['mounting_release']=False
    name=o.name.removeprefix(PREFIX)
    if name.startswith('Display_Frame_'):o['explode_offset_mm']=[0,95,105]
    elif name.startswith('Battery_Retainer_'):o['explode_offset_mm']=[0,65,-10]
    elif name.startswith('Motor_Mount_'):o['explode_offset_mm']=[-40 if '_L' in name else 40,0,0]
    return o


def volume(o):
    o.data.calc_loop_triangles()
    v=np.array([tuple(p) for p in vertices_world(o)],dtype=np.float64)
    f=np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.uint64)
    m=manifold.Manifold(manifold.Mesh64(v,f))
    assert m.status()==manifold.Error.NoError,o.name
    return m.volume()


def apply_structural_simplification():
    if not P.get('structure',{}).get('enabled'):return
    hz=D['head_z'];wz=D['wheel_z'];dz=P['layout']['deck_z_mm'];t=P['structure']['main_web_thickness_mm']
    targets=['Pitch_Cradle','Camera_Mount','CAM_Mainboard_Mount','Display_Frame',
             'Pitch_Yoke','Pitch_Servo_Mount','Yaw_Carrier','Load_Frame','Motor_Mount_L','Motor_Mount_R','Battery_Tray']
    before={n:{'volume_mm3':volume(bpy.data.objects[PREFIX+n]),'bounds_xyz_mm':bounds(bpy.data.objects[PREFIX+n])} for n in targets}

    # One moving head frame: arch, rear CAM tray and front camera shelf share
    # continuous material. The LCD frame remains separately removable.
    for name in ['Pitch_Cradle','Camera_Mount','CAM_Mainboard_Mount']:remove_generated(name)
    arch=[(-47,-5),(-47,7),(-39,37),(-34,39),(34,39),(39,37),(47,7),(47,-5),
          (41,-5),(41,5),(33,32),(-33,32),(-41,5),(-41,-5)]
    core=plate('Pitch_Cradle',[(x,hz+z) for x,z in arch],2.5,t)
    for sign in [-1,1]:
        union(core,ring('pivot_cheek',(sign*44,0,hz),8,2.7,3,'X'))
        web=[(sign*39,hz+14),(sign*42,hz+25),(sign*49,hz+26),(sign*49,hz+22)]
        union(core,plate('shell_lug_web',web,3,4))
        boolean(core,cyl('trunnion_pass',(sign*44,0,hz),2.7,16,'X'))
        boolean(core,cyl('bearing_housing_clear',(sign*39,0,hz),9.2,5.2,'X'))
    cam_center=P['layout']['cam_board_center_from_head_mm'];cam_z=hz+cam_center[2]
    rear=box('cam_back_frame',(0,-31,cam_z),(43,2.4,43))
    boolean(rear,box('cam_window',(0,-31,cam_z),(29,6,29)))
    for sign in [-1,1]:
        web=[(-31,hz+26),(-31,hz+34.5),(4.5,hz+38.2),(4.5,hz+32),(-27,hz+28)]
        union(rear,plate('cam_side_web',web,sign*20.5,3,'X'))
    union(core,rear)
    # Broad camera shelf replaces its two 3mm round struts.
    pcb_z=P['camera']['body_center_from_head_mm'][2]
    camera_plate=box('camera_seat',(0,37.4,hz+pcb_z),(16,2,12))
    union(camera_plate,box('camera_shelf',(0,20.4,hz+34.5),(16,33.6,2.6)))
    union(core,camera_plate)
    for sign in [-1,1]:
        union(core,box('screen_screw_boss',(sign*26.5,1.25,hz+35),(8,7.5,8)))
        boolean(core,cyl('M2_pass',(sign*26.5,2,hz+35),1.2,16,'Y'))
        boolean(core,cyl('M2_nut_pocket',(sign*26.5,-1.7,hz+35),2.9,2.4,'Y',6))
    intersect(core,sphere('head_inner_limit',(0,0,hz),D['head_radius']-2.8))
    boolean(core,clone(bpy.data.objects[PREFIX+'Head_Front'],'shell_lug_seat'))
    for name in ['Mic_Duct_L','Mic_Duct_R']:
        boolean(core,clone(bpy.data.objects[PREFIX+name],'mic_seat'))
    printed(core,'一体头骨架 / CAM与相机安装座','pitch',
            'Replaces three separate supports. Open CAM frame and camera shelf integral; LCD bracket removable by two trialM2 screws. CAM final hole diameter/straps still pending.')
    core['integrated_functions']=['Pitch_Cradle','Camera_Mount','CAM_Mainboard_Mount']

    # Same vendor-post spider, now supported by two broad flat gussets and
    # accessible bolted flanges instead of rods meeting a round crossbar.
    remove_generated('Display_Frame');dp=P['display'];sz=hz+dp['z_from_head_mm'];fy=dp['vendor_mount_back_y_from_head_mm']-1.4
    frame=ring('Display_Frame',(0,fy,sz),29.6,27.1,2,'Y')
    for x,z in INTERFACES['components']['display']['vendor_dimensions']['cad_post_center_xz_from_screen_mm']:
        n=math.hypot(x,z);a=Vector((x,fy,sz+z));b=Vector((x/n*28.3,fy,sz+z/n*28.3));delta=b-a
        arm=box('spider_arm',(a+b)/2,(4.8,2,delta.length));arm.rotation_euler=(0,math.atan2(delta.x,delta.z),0);bpy.context.view_layer.update()
        union(frame,arm);union(frame,cyl('post_pad',(x,fy,sz+z),3.4,2,'Y'))
        boolean(frame,cyl('post_trial_clearance',(x,fy,sz+z),1.2,8,'Y'))
    for sign in [-1,1]:
        web=[(fy,sz+10),(fy,sz+19),(8,hz+39),(5,hz+38),(5,hz+32),(fy-3,sz+10)]
        union(frame,plate('display_side_gusset',web,sign*25.8,3,'X'))
        union(frame,box('display_flange',(sign*26.5,6.5,hz+35),(8,3,8)))
        boolean(frame,cyl('M2_pass',(sign*26.5,6.5,hz+35),1.2,10,'Y'))
        screw=cyl('Display_Frame_Screw_'+str(sign),(sign*26.5,3,hz+35),.95,10,'Y')
        union(screw,cyl('M2_head',(sign*26.5,8.8,hz+35),1.9,1.6,'Y'))
        boolean(frame,cyl('screw_head_access',(sign*26.5,22,hz+35),2.4,28,'Y'))
        hardware(screw,'屏幕架可拆M2螺钉（试配）','pitch')
        nut=ring('Display_Frame_Nut_'+str(sign),(sign*26.5,-1.55,hz+35),2.4,1.1,1.6,'Y',6)
        hardware(nut,'屏幕架防转M2螺母（试配）','pitch')
    printed(frame,'可拆屏幕架 / 宽肋与双螺钉法兰','pitch',
            'Vendor LCD unchanged.3 vendor posts plus2 accessible frame screws;2.4mm clearances and nut pockets are trial FDM dimensions.')

    # Yaw carrier: two integral cheek plates replace four tall posts. Keep the
    # original bearing shoulder and drive/cable aperture.
    remove_generated('Yaw_Carrier');bz=D['body_top_z']+P['head_joint']['yaw_bearing_z_from_top_mm']
    yc=ring('Yaw_Carrier',(0,0,bz),20,16.3,8)
    union(yc,ring('bearing_ledge',(0,0,bz-4.5),20,10.2,2))
    for sign in [-1,1]:
        union(yc,plate('bearing_side_wall',[(-17,134),(-17,155),(17,155),(17,134)],sign*21,4,'X'))
        union(yc,box('bearing_upper_flange',(sign*18.5,0,155),(9,28,3)))
        # Clearance for the actual body-side servo and its removable mount.
    for name in ['Yaw_Servo','Yaw_Servo_Mount']:
        boolean(yc,clone(bpy.data.objects[PREFIX+name],'servo_seat'))
    # Fixed cable clamp and rotating stop flag keep their original clearance.
    boolean(yc,clone(bpy.data.objects[PREFIX+'Yaw_Cable_Clip'],'fixed_clip_seat'))
    for angle in range(-60,61,5):
        for name in ['Yaw_Stop_Flag']:
            cutter=clone(bpy.data.objects[PREFIX+name],'yaw_sweep_clear')
            cutter.matrix_world=Matrix.Rotation(math.radians(angle),4,'Z')@cutter.matrix_world
            boolean(yc,cutter)
    boolean(yc,cyl('yaw_service_ring_clear',(0,0,body_z_mm(48)),19.7,3.4))
    printed(yc,'Yaw承重座 / 双侧整体板壁')

    # A wide-web yoke with integrated servo saddle, preserving both bearings.
    old_mount=bpy.data.objects[PREFIX+'Pitch_Servo_Mount'];mountcopy=clone(old_mount,'integrated_servo_seat')
    remove_generated('Pitch_Yoke');remove_generated('Pitch_Servo_Mount')
    top=D['body_top_z'];yoke=box('Pitch_Yoke',(0,-8,top+5.5),(24,12,4))
    for sign in [-1,1]:
        outline=[(sign*4,top+5.5),(sign*18,hz-21),(sign*35,hz-3),
                 (sign*43,hz-8),(sign*29,hz-27),(sign*12,top+5.5)]
        union(yoke,plate('yoke_web',outline,-10,4))
        union(yoke,plate('housing_web',[(-12,hz-12),(-12,hz-3),(-6,hz+2),(0,hz-7)],sign*39,4,'X'))
        union(yoke,ring('bearing_housing',(sign*39,0,hz),8.5,6.25,4,'X'))
        boolean(yoke,cyl('bearing_bore',(sign*39,0,hz),6.25,8,'X'))
    union(yoke,mountcopy)
    for angle in [-28,33]:
        ca=math.cos(math.radians(angle));sa=math.sin(math.radians(angle))
        union(yoke,box('pitch_stop',(39,-10*ca,hz-10*sa),(4,2,2)))
        union(yoke,plate('pitch_stop_web',[(-7*ca,hz-7*sa-1.2),(-10*ca,hz-10*sa-1.2),(-10*ca,hz-10*sa+1.2),(-7*ca,hz-7*sa+1.2)],39,4,'X'))
    boolean(yoke,cyl('body_fixed_wire_clear',(0,0,body_z_mm(79)),8,14))
    boolean(yoke,clone(bpy.data.objects[PREFIX+'Pitch_Servo'],'servo_cavity'))
    clip_z(yoke,top+3.5,500)
    printed(yoke,'一体Pitch叉架 / 宽肋与舵机安装托','yaw',
            'Bilateral bearings retained; servo saddle integrated. Hard-stop contact angles and final servo screws still NOT_TESTED.')
    yoke['integrated_functions']=['Pitch_Yoke','Pitch_Servo_Mount']

    # Two broad chassis webs connect paired wheel bearings to the deck. Battery
    # channels transfer vertical load directly into the same frame.
    remove_generated('Load_Frame')
    frame=cyl('Load_Frame',(0,0,dz),70,4);intersect(frame,box('deck_clip',(0,0,dz),(116,100,8)))
    boolean(frame,box('yaw_servo_pass',(4,0,dz),(38,22,12)))
    for sign in [-1,1]:
        cx=sign*36
        union(frame,ring('paired_bearing_housing',(cx,0,wz),7,5.25,10.8,'X'))
        web=[(-4,wz-2),(-49,72),(-49,dz-1),(-36,dz-1),(-36,80),(3,wz+7)]
        union(frame,plate('chassis_side_web',web,cx,t,'X'))
        boolean(frame,cyl('through_bearing_bore',(cx,0,wz),5.25,16,'X'))
        union(frame,box('battery_sidewall',(sign*47,0,(78.3+dz-1)/2),(3,48,dz-1-78.3)))
        union(frame,box('battery_load_ledge',(sign*43.25,0,79.8),(10.5,48,3)))
    union(frame,box('rear_motor_crossmember',(0,-44,78.5),(78,13,3)))
    for sign in [-1,1]:
        for xx in [sign*14-4,sign*14+4]:boolean(frame,cyl('M3_motor_pass',(xx,-43,78.5),1.7,10))
        boolean(frame,cyl('battery_retention_pass',(sign*47,20,88),1.2,10,'X'))
    for x,y in P['shell_service']['frame_mount_xy_mm']:boolean(frame,cyl('frame_screw',(x,y,dz),1.7,10))
    for name in ['Speaker_Mount','Speaker']:boolean(frame,clone(bpy.data.objects[PREFIX+name],'speaker_service_cut'))
    boolean(frame,box('front_service_notch',(0,50,132),(44,28,8)))
    printed(frame,'一体底盘 / 双侧承重板与电池滑轨')

    for sign,n in [(-1,'L'),(1,'R')]:
        remove_generated('Motor_Mount_'+n);cx=sign*P['drive']['motor_center_abs_x_mm']
        mount=box('Motor_Mount_'+n,(cx,0,wz+27),(25,24,2.8))
        for yy in [-11.5,11.5]:union(mount,box('motor_side',(cx,yy,wz+8),(25,2,36)))
        union(mount,plate('motor_flat_web',[(-12,72),(-44,72),(-44,77),(-12,77)],cx,8,'X'))
        union(mount,box('motor_rear_flange',(cx,-43,74.5),(18,12,5)))
        for i,xx in enumerate([cx-4,cx+4]):
            boolean(mount,cyl('motor_bolt_pass',(xx,-43,74.5),1.7,10))
            screw=cyl('Motor_Mount_Screw_'+n+str(i),(xx,-43,77),1.45,10)
            union(screw,cyl('motor_bolt_head',(xx,-43,71),2.7,2))
            hardware(screw,'电机鞍座M3短螺钉 '+n+str(i))
            nut=ring('Motor_Mount_Nut_'+n+str(i),(xx,-43,81.2),3,1.8,2.4,'Z',6)
            hardware(nut,'电机鞍座M3螺母 '+n+str(i))
        printed(mount,'可拆电机鞍座 / 短平板连接 '+n)

    remove_generated('Battery_Tray')
    for i in range(4):remove_generated('Battery_Hanger_'+str(i))
    tray=box('Battery_Tray',(0,0,83),(90,70,3))
    for sign in [-1,1]:
        union(tray,box('battery_side_rail',(sign*42.75,0,88),(4.5,70,10)))
        boolean(tray,cyl('retention_hole',(sign*43,20,88),1.2,9,'X'))
        boolean(tray,cyl('insert_trial',(sign*43.5,20,88),1.7,3.2,'X'))
        screw=cyl('Battery_Retainer_Screw_'+str(sign),(sign*45.5,20,88),.95,6,'X')
        union(screw,cyl('retainer_head',(sign*49.3,20,88),1.9,1.6,'X'))
        hardware(screw,'电池滑轨M2短限位螺钉')
        hardware(ring('Battery_Retainer_Insert_'+str(sign),(sign*43.5,20,88),1.6,1.1,3,'X'),'电池托盘M2嵌件（试配）')
    for yy in [-29,29]:boolean(tray,box('strap',(0,yy,83),(20,2.4,8)))
    # Local lower-shell wheel recesses leave less width at these tray corners.
    boolean(tray,clone(bpy.data.objects[PREFIX+'Body_Lower'],'tray_shell_relief'))
    printed(tray,'滑轨电池托盘 / 两侧短螺钉限位',note='Vertical load carried by integral side channels; two side screws retain extraction. Same unselected80x65x30 battery allocation. No four44mm suspension rods.')

    # Obsolete recorded contacts are removed; the remaining contacts are not
    # allowed to waive solid penetrations in validation.
    import sys
    build=sys.modules.get('__main__')
    if not hasattr(build,'CONTACTS'):
        import build
    existing={o.name.removeprefix(PREFIX) for o in parts()}
    updated_pairs=[{'Display_Frame','Pitch_Cradle'},{'Yaw_Carrier','Load_Frame'}]
    build.CONTACTS[:]=[c for c in build.CONTACTS if c['a'] in existing and c['b'] in existing and {c['a'],c['b']} not in updated_pairs]
    build.contact('Yaw_Carrier','Load_Frame','Two integral side walls bear on deck top; fastening and retention pending')
    build.contact('Display_Frame','Pitch_Cradle','Two trialM2 bolted flat flanges with nominal face contact; vendor mounting hardware and FDM fits pending')
    build.contact('Pitch_Yoke','Pitch_Servo','Integrated saddle; vendor servo ears and screws remain a trial interface')
    build.contact('Load_Frame','Battery_Tray','Side channels carry tray; nominal0.2mm vertical clearance, two removable short retention screws')
    for n in ['L','R']:build.contact('Load_Frame','Motor_Mount_'+n,'Flat flange on rear crossmember with two trialM3 through bolts')
    after={n:{'volume_mm3':volume(bpy.data.objects[PREFIX+n]),'bounds_xyz_mm':bounds(bpy.data.objects[PREFIX+n])} for n in targets if bpy.data.objects.get(PREFIX+n)}
    save_json(ROOT/'reports/structure_changes.json',{
        'revision':P['revision'],'before_revision':'V1.2-M1.1','before':before,'after':after,
        'support_printed_parts_before':len(before),'support_printed_parts_after':len(after),
        'removed_long_battery_hangers':4,'new_battery_retention_screws':2,
        'joint_axes_unchanged':True,'vendor_geometry_rescaled':False,
        'geometry_status':'REQUIRES_CURRENT_VALIDATE_RUN',
        'strength_status':'NOT_TESTED','limits':'Fewer separately assembled supports and wider continuous webs are design changes, not measured reliability/FEA proof. P1 power80x45 and populated modules remain unplaced; legacy electrical allocations are not final mounting surfaces.'})
