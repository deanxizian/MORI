"""MORI V1 Stage A. Run with Blender --background --python mechanical/scripts/build.py."""
import sys,math,json,hashlib,platform,time,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
CONTACTS=[]

def contact(a,b,reason): CONTACTS.append(dict(a=a,b=b,reason=reason))
def done(o,label,mat='frame',group='body',cat='PRINTABLE',export=True,ex=(0,0,0),note='Candidate trial geometry; vendor fasteners and fits pending Stage B',role='part'):
    return finish(o,cat,label,mat,group,export,ex,note,role)
def ref(o,label,mat='metal',group='body',ex=(0,0,0),note='ASSUMED maximum allocation; not a selected supplier part'):
    return done(o,label,mat,group,'PLACEHOLDER',False,ex,note)
def beam(name,a,b,r=2.5):
    a=Vector(a); b=Vector(b); o=cyl(name,(a+b)/2,r,(b-a).length)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); bpy.context.view_layer.update(); return o

def body_outer(name):
    o=sphere(name,(0,0,D['body_z']),D['body_radius'])
    intersect(o,box('clip',(0,0,D['body_top_z']-250),(2*P['body_side_cut_x_mm'],1000,500)))
    return o

def shells():
    t=P['shell_thickness_mm']; bz=D['body_z']; hz=D['head_z']; side=P['body_side_cut_x_mm']; gap=P['seam_gap_mm']/2
    outer=body_outer('body_outer_temp'); inner=sphere('inner',(0,0,bz),D['body_radius']-t)
    intersect(inner,box('innerclip',(0,0,D['body_top_z']-t-250),(2*(side-t),1000,500)))
    shell=clone(outer,'body_shell_temp'); boolean(shell,inner)
    boolean(shell,cyl('top_open',(0,0,D['body_top_z']),P['body_top_opening_diameter_mm']/2,25))
    boolean(shell,cyl('axle_bore',(0,0,D['wheel_z']),4.2,180,'X'))
    # Actual rear port cutouts; separate complete module and external plug allocations below.
    boolean(shell,box('usb_cut',(14,-71,108),(12,30,6)))
    boolean(shell,box('switch_cut',(-14,-70,103),(12,30,8)))
    boolean(shell,cyl('button_cut',(0,-55,149),4.4,40,'Y'))
    # Speaker holes, separate front microphone hole.
    for x in [-6,-3,0,3,6]:
        for z in [91,95,99]: boolean(shell,cyl('speaker_hole',(x,73,z),.8,20,'Y',16))
    boolean(shell,cyl('mic_hole',(-36,59,136),1,38,'Y',20))
    upper=clone(shell,'Body_Upper'); lower=clone(shell,'Body_Lower'); clip_z(upper,bz+gap,500); clip_z(lower,-500,bz-gap)
    # Four load-frame seats, connected to side walls. Trial M3 insert pilots.
    for i,(x,y) in enumerate([(55,28),(-55,28),(55,-28),(-55,-28)]):
        boss=cyl('boss',(x,y*18/28,123),5.7,6); intersect(boss,clone(outer,'limit')); union(upper,boss)
        boolean(upper,cyl('pilot',(x,y*18/28,122.5),2.05,5.2))
        # Lower-shell seams: horizontal radial tabs at the same side wall, accessible from below.
        boss=cyl('seam_boss',(x,y,103.5),5.7,6.4); intersect(boss,clone(outer,'limit')); union(upper,boss)
        boolean(upper,cyl('pilot',(x,y,103),2.05,5.6))
        sleeve=cyl('seam_sleeve',(x,y,92),5.7,15.4); intersect(sleeve,clone(outer,'limit')); union(lower,sleeve)
        boolean(lower,cyl('screw_bore',(x,y,91),1.7,20))
        boolean(lower,cyl('tool_counterbore',(x,y,42),3.3,94))
    done(upper,'身体上壳','shell',ex=(0,0,55)); done(lower,'身体下壳','shell',ex=(0,0,-48))
    # True spherical head with a real lower cap opening; front/rear split is Y=0.
    ho=sphere('head_outer',(0,0,hz),D['head_radius']); clip_z(ho,hz+P['head_lower_opening_z_from_center_mm'],500)
    hs=clone(ho,'head_shell_temp'); boolean(hs,sphere('cavity',(0,0,hz),D['head_radius']-t))
    dp=P['display']; cz=hz+dp['z_from_head_mm']
    boolean(hs,cyl('face_open',(0,55,cz),dp['aperture_diameter_mm']/2,70,'Y'))
    boolean(hs,cyl('camera_open',(0,50,hz+P['camera']['body_center_from_head_mm'][2]),P['camera']['aperture_diameter_mm']/2,40,'Y'))
    hf=clone(hs,'Head_Front'); hb=clone(hs,'Head_Rear'); clip_y(hf,gap,500); clip_y(hb,-500,-gap)
    for s in [-1,1]:
        lug=box('cradle_lug',(s*43,3.5,hz+24),(9,6,6)); intersect(lug,clone(ho,'limit')); union(hf,lug)
        boolean(hf,cyl('lug_pilot',(s*43,3,hz+23.5),1.6,5.5))
        # Two rear seam screw sleeves and front sockets, local and well above the moving guard.
        lug=cyl('seam_front',(s*37,3,hz+29),4.2,5.4,'Y'); intersect(lug,clone(ho,'limit')); union(hf,lug)
        boolean(hf,cyl('pilot',(s*37,2,hz+29),1.6,4,'Y'))
        lug=cyl('seam_rear',(s*37,-8,hz+29),4.2,15.4,'Y'); intersect(lug,clone(ho,'limit')); union(hb,lug)
        boolean(hb,cyl('bore',(s*37,-10,hz+29),1.2,30,'Y'))
        boolean(hb,cyl('counter',(s*37,-20,hz+29),2.4,15,'Y'))
    done(hf,'头前壳','shell','pitch',ex=(0,60,110)); done(hb,'头后壳','shell','pitch',ex=(0,-60,110))
    for o in [outer,shell,ho,hs]: bpy.data.objects.remove(o,do_unlink=True)

def optics():
    hz=D['head_z']; dp=P['display']; fy=D['face_y']; z=hz+dp['z_from_head_mm']
    # Flat optical assembly fitted to an aperture in a genuine spherical shell.
    frame=ring('Display_Frame',(0,32,z),33,29.3,4,'Y')
    intersect(frame,sphere('inner_limit',(0,0,hz),D['head_radius']-2.8))
    done(frame,'圆屏固定框','dark','pitch',ex=(0,40,100))
    screen=ref(cyl('Display_Module',(0,fy-2.5,z),29,3,'Y'),'圆屏显示层包络','dark','pitch',(0,80,100))
    pcb=ref(cyl('Display_PCB',(0,32.8,z),31,2,'Y'),'圆屏 PCB 包络','pcb','pitch',(0,52,100))
    # Remove the allocated PCB from its retaining frame, leaving a shoulder, not intersecting solids.
    cut=cyl('pcb_clear',(0,32.8,z),31.8,3.0,'Y'); boolean(frame,cut); boolean(frame,box('camera_clear',(0,32,hz+33),(16,10,12))); frame.data.materials.append(MATS['dark'])
    glass=done(cyl('Face_Protector',(0,fy-.45,z),29.7,.8,'Y'),'透明圆屏保护片','glass','pitch','PURCHASED_REFERENCE',False,(0,100,100),'Flat clear sheet trial; surface reflections/optical quality unverified')
    ref(box('Display_Connector',(0,27,z+8),(12,6,5)),'屏幕排线连接器包络','dark','pitch')
    for s,n in [(-1,'L'),(1,'R')]:
        # Rounded capsules are screen content, not additional hardware.
        eye=box('Eye_'+n,(s*11.5,fy-.92,z),(8,.12,7))
        for zz in [-3.5,3.5]: union(eye,cyl('cap',(s*11.5,fy-.92,z+zz),4,.12,'Y'))
        done(eye,'眼睛像素 '+n,'eye','pitch','PURCHASED_REFERENCE',False,(0,80,100),'Display pixels only',role='display_content')
    cam=P['camera']; cp=cam['body_center_from_head_mm']; cz=hz+cp[2]
    ref(box('Camera_PCB',(cp[0],cp[1],cz),cam['body_max_xyz_mm']),'摄像头模组最大包络','pcb','pitch',(0,35,110))
    ref(cyl('Camera_Lens',(0,34.45,cz),2.5,5.9,'Y'),'相机真实镜筒与入瞳','dark','pitch',(0,45,110))
    # Actual curved window follows the mother sphere; lens is in front of the opaque screen.
    win=sphere('Camera_Window',(0,0,hz),D['head_radius']); boolean(win,sphere('inside',(0,0,hz),D['head_radius']-.8))
    intersect(win,cyl('win_trim',(0,49,cz),4.7,25,'Y'))
    done(win,'摄像头独立保护窗','glass','pitch','PURCHASED_REFERENCE',False,(0,65,110),'Curved clear window allocation; material, refraction and coating require optical validation')
    mount=box('Camera_Mount',(0,22,cz),(19,3,15)); boolean(mount,box('board_relief',(0,29,cz),(14.6,8.6,10.6)))
    for sign in [-1,1]: union(mount,beam('camera_brace',(sign*8,3,hz+21),(sign*8,22,hz+28),1.5))
    done(mount,'摄像头支架','frame','pitch',ex=(0,20,110))

def head_joint():
    hz=D['head_z']; top=D['body_top_z']; hj=P['head_joint']; bz=top+hj['yaw_bearing_z_from_top_mm']
    carrier=ring('Yaw_Carrier',(0,0,bz),20,16.3,8)
    union(carrier,ring('ledge',(0,0,bz-4.5),20,10.2,2))
    for x,y in [(20,15),(-20,15),(20,-15),(-20,-15)]:
        union(carrier,cyl('post',(x,y,(120+bz-5.5)/2),3,(bz-5.5)-120))
        union(carrier,beam('bearing_flange',(x*19/25,y*19/25,bz-4.5),(x,y,bz-4.5),2.5))
        boolean(carrier,cyl('pilot',(x,y,122),1.6,4))
    done(carrier,'Yaw 承重轴承座及立柱','frame',ex=(0,0,50)); contact('Yaw_Carrier','Load_Frame','Four support-post bottom planes at deck top')
    ref(ring('Yaw_Bearing',(0,0,bz),16,10,7),'Yaw 承重环轴承包络','metal')
    contact('Yaw_Bearing','Yaw_Carrier','Axial bearing support ledge; supplier tolerances/retention TBD')
    rotor=ring('Yaw_Turntable',(0,0,(bz-6+top+2)/2),9.8,7.7,(top+2)-(bz-6))
    union(rotor,ring('top_plate',(0,0,top+2),19,7.7,3))
    union(rotor,ring('drive_web',(0,0,bz-6.5),9.8,2.5,2))
    for angle in range(-70,71,5):
        rad=math.radians(180+angle); boolean(rotor,cyl('limited_yaw_cable_slot',(6.4*math.cos(rad),6.4*math.sin(rad),141.5),1.7,4))
    done(rotor,'Yaw 转盘与空心轴','frame','yaw',ex=(0,0,75))
    servo=ref(box('Yaw_Servo',(0,0,125.5),INTERFACES['components']['yaw_servo']['max_xyz_mm']),'Yaw 舵机包络','blue'); servo['actuator_id']='head_yaw'
    mount=box('Yaw_Servo_Mount',(0,0,112.5),(30,19,2));
    for x in [-14,14]:
        union(mount,box('servo_side',(x,0,124),(3,19,21)))
        union(mount,box('frame_tab',(x*18/14,0,121),(12,19,2)))
    done(mount,'Yaw 舵机托座','frame'); contact('Yaw_Servo_Mount','Load_Frame','Mount base / deck top'); contact('Yaw_Servo','Yaw_Servo_Mount','Servo lower seat')
    ref(cyl('Yaw_Output',(0,0,141.5),2.5,8),'Yaw 输出轴占位','metal','yaw'); contact('Yaw_Output','Yaw_Servo','Output shaft end'); contact('Yaw_Output','Yaw_Turntable','Output drive web; actual spline/coupler TBD')
    ref(ring('Yaw_Horn',(0,0,140),5,2.5,1),'Yaw 舵盘/联轴器占位','metal','yaw')
    # Yoke: a yaw-fixed bridge, two rear struts, and paired load bearing housings.
    yoke=box('Pitch_Yoke',(0,-8,top+5.5),(24,12,4))
    for s in [-1,1]:
        pts=[(s*8,-10,top+5.5),(s*24,-10,hz-23),(s*39,-10,hz-8)]
        for a,b in zip(pts,pts[1:]): union(yoke,beam('yoke_arm',a,b,2.8))
        h=ring('trunnion_housing',(s*39,0,hz),8.5,6.25,4,'X'); union(h,beam('rear_brace',(s*39,-10,hz-8),(s*39,-6,hz-3),2.8)); union(yoke,h)
        ref(ring('Pitch_Bearing_'+('L' if s<0 else 'R'),(s*39,0,hz),6,2.5,4,'X'),'Pitch 两侧承重轴承','metal','yaw')
    boolean(yoke,cyl('body_fixed_wire_clear',(0,0,170),8,14))
    clip_z(yoke,top+3.5,500)
    done(yoke,'Pitch 双侧承重支架','frame','yaw',ex=(0,-20,95)); contact('Pitch_Yoke','Yaw_Turntable','Yoke base / rotor top face')
    ps=ref(box('Pitch_Servo',(-23,0,hz),INTERFACES['components']['pitch_servo']['max_xyz_mm']),'Pitch 舵机包络','blue','yaw'); ps['actuator_id']='head_pitch'
    # Separate removable saddle attached to yoke back rail; exact servo ears remain TBD.
    sm=box('Pitch_Servo_Mount',(-23,-8,hz),(28,3,24)); union(sm,box('shelf',(-23,0,hz-12.5),(28,17,3)))
    boolean(sm,clone(yoke,'yoke_relief'))
    done(sm,'Pitch 舵机安装托','frame','yaw',ex=(-20,-10,100)); contact('Pitch_Servo','Pitch_Servo_Mount','Servo lower seat and rear restraint')
    cradle=None
    for s,n in [(-1,'L'),(1,'R')]:
        cheek=ring('cheek',(s*44,0,hz),8,2.7,3,'X')
        union(cheek,cyl('upright',(s*44,3,hz+14),2.0,14))
        if cradle is None: cradle=cheek
        else: union(cradle,cheek)
        ref(cyl('Pitch_Trunnion_'+n,(s*40.5,0,hz),2.49,11,'X'),'Pitch 承重短轴 '+n,'metal','pitch')
        contact('Pitch_Trunnion_'+n,'Pitch_Bearing_'+n,'Nominal journal/bearing contact; fits unselected')
    # Upper crossbar links both cheeks, kept behind the camera and away from its PCB.
    union(cradle,beam('crossbar',(-44,3,hz+18),(44,3,hz+18),2.5))
    intersect(cradle,sphere('cradle_inner_limit',(0,0,hz),D['head_radius']-2.8))
    cradle.name=PREFIX+'Pitch_Cradle'; done(cradle,'Pitch 随头旋转承架','frame','pitch',ex=(0,0,110))
    # Match separate optical supports to the actual rotating crossbar seat.
    camera_mount=bpy.data.objects[PREFIX+'Camera_Mount']; boolean(camera_mount,clone(cradle,'camera_saddle')); camera_mount.data.materials.append(MATS['frame'])
    optical_frame=bpy.data.objects[PREFIX+'Display_Frame']
    for sign in [-1,1]: union(optical_frame,beam('display_support',(sign*28,32,hz+13),(sign*28,3,hz+20.5),2))
    boolean(optical_frame,clone(cradle,'display_saddle')); boolean(optical_frame,cyl('pcb_extra_relief',(0,32.8,hz-4),31.8,3,'Y')); optical_frame.data.materials.append(MATS['dark'])
    contact('Camera_Mount','Pitch_Cradle','Matching crossbar saddle; fastening details pending Stage B')
    contact('Display_Frame','Pitch_Cradle','Matching crossbar saddles; fastening details pending Stage B')
    contact('Pitch_Cradle','Head_Front','Two top lug seats, trial M2 inserts'); contact('Pitch_Cradle','Pitch_Trunnion_L','Bilateral shaft shoulder'); contact('Pitch_Cradle','Pitch_Trunnion_R','Bilateral shaft shoulder')
    ref(ring('Pitch_Horn',(-36,0,hz),5,2.5,1,'X'),'Pitch 舵盘 / 轴联接','metal','pitch')
    contact('Pitch_Horn','Pitch_Servo','Output end / torque coupling')
    # A concentric lower inner guard reduces exposed gimbal; relief cuts use the SAME swept optics.
    guard=sphere('Head_Lower_Guard',(0,0,hz),hj['guard_outer_radius_mm']); boolean(guard,sphere('inner',(0,0,hz),hj['guard_outer_radius_mm']-hj['guard_thickness_mm']))
    clip_z(guard,top+hj['guard_lower_z_from_body_top_mm'],hz+hj['guard_top_z_from_head_mm'])
    for pitch in range(-20,26,5):
        cutter=cyl('swept_display_clear',(0,35.2,hz-4),34,13,'Y')
        tr=Matrix.Translation((0,0,hz))@Matrix.Rotation(math.radians(pitch),4,'X')@Matrix.Translation((0,0,-hz))
        cutter.matrix_world=tr@cutter.matrix_world; boolean(guard,cutter)
    for angle in [210,270,330]:
        u=Vector((math.cos(math.radians(angle)),math.sin(math.radians(angle)),0)); q=beam('guard_support',u*18+Vector((0,0,168)),u*33+Vector((0,0,168)),1.6); clip_z(q,166.5,500); intersect(q,sphere('support_limit',(0,0,hz),hj['guard_outer_radius_mm'])); union(guard,q)
    done(guard,'同心下护罩（显示运动让位）','shell','yaw',ex=(0,-25,90),note='0.9 mm nominal radial shell clearance; opening exposure remains a visual/optical review item')
    # Small stop flag and fixed blocks lie below body top; hard limits outside commanded range.
    flag=box('Yaw_Stop_Flag',(11,0,140),(9,2,1)); done(flag,'Yaw 限位凸耳','frame','yaw')
    for a in [-76,76]:
        x=14*math.cos(math.radians(a)); y=14*math.sin(math.radians(a))
        q=box('Yaw_Stop_'+str(a),(x,y,140),(3,3,3)); done(q,'Yaw 固定限位块','frame')
    # Pitch stops are separate blocks on the yoke, flagged as trial stop geometry.
    for a,n in [(-28,'Down'),(33,'Up')]:
        q=box('Pitch_Stop_'+n,(39,-10*math.cos(math.radians(a)),hz-10*math.sin(math.radians(a))),(4,2,2)); union(q,beam('stop_anchor',(39,-7.5*math.cos(math.radians(a)),hz-7.5*math.sin(math.radians(a))),(39,-10*math.cos(math.radians(a)),hz-10*math.sin(math.radians(a))),1.1)); union(yoke,q); yoke.data.materials.append(MATS['frame'])
    # Flexible service loops are routing envelopes, not claimed cable mechanics.
    for name,loc,major,minor,axis,grp in [('Yaw_Service_Loop',(0,0,139),18,1.2,'Z','yaw'),('Pitch_Service_Loop',(29,0,hz),7,1.2,'X','pitch')]:
        bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=10,location=loc,major_radius=major,minor_radius=minor)
        o=raw(bpy.context.object,name)
        if axis=='X': o.rotation_euler.y=math.pi/2; bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        done(o,'头部线束服务环 '+name,'copper',grp,'PLACEHOLDER',False,note='Conservative routing allocation; dynamic cable deformation, bend fatigue and endpoints NOT_TESTED',role='routing')
    for name,loc in [('Yaw_Cable_Clip',(-18,0,139)),('Pitch_Cable_Clip',(29,-7,hz))]:
        o=ring(name,loc,3,1.8,4,'Y' if 'Yaw' in name else 'Z'); done(o,'线束应力释放夹','frame','yaw' if 'Pitch' in name else 'body')

def wheel_and_drive():
    dr=P['drive']; wz=D['wheel_z']; wx=D['wheel_x']
    for s,n in [(-1,'L'),(1,'R')]:
        grp='wheel_'+n
        ref(ring('Tire_'+n,(s*wx,0,wz),D['wheel_radius'],D['wheel_radius']-11.5,P['wheel_width_mm'],'X'),'轮胎 '+n,'tire',grp,(s*50,0,0),note='Soft purchased rubber or separately qualified TPU; nominal Ø95 x 18, no product selected')
        hub=ring('Wheel_Hub_'+n,(s*wx,0,wz),D['wheel_radius']-11.5,3.2,P['wheel_width_mm']-3,'X')
        done(hub,'轮毂 '+n,'shell',grp,ex=(s*35,0,0),note='Trial hub; shaft clamping/key and tire retention pending')
        cap=cyl('Wheel_Cap_'+n,(s*(wx+P['wheel_width_mm']/2+.2),0,wz),D['wheel_radius']-11.7,1.2,'X'); done(cap,'轮毂盖 '+n,'shell',grp,ex=(s*75,0,0))
        ref(cyl('Wheel_Axle_'+n,(s*53,0,wz),3,60,'X'),'独立承重轮轴 '+n,'metal',grp,(s*20,0,0))
        for x in dr['bearing_abs_x_mm']:
            ref(ring('Wheel_Bearing_'+n+'_'+str(x),(s*x,0,wz),6.5,3,4,'X'),'轮轴承 '+n+' '+str(x),'metal')
            contact('Wheel_Axle_'+n,'Wheel_Bearing_'+n+'_'+str(x),'Bearing bore / independent axle; actual fits unselected')
        my=-s*dr['motor_offset_y_mm']; mz=dr['motor_z_mm']
        mot=ref(cyl('Drive_Motor_'+n,(0,my,mz),dr['motor_max_diameter_mm']/2,dr['motor_max_length_including_encoder_mm'],'X'),'含编码器减速电机包络 '+n,'metal',ex=(s*20,-s*30,0)); mot['actuator_id']='wheel_'+n
        ref(cyl('Motor_Output_'+n,(s*38.5,my,mz),2,12,'X'),'电机输出轴占位 '+n,'metal')
        contact('Motor_Output_'+n,'Drive_Motor_'+n,'Output starts at allocated motor face; shaft actual size TBD')
        mount=None
        for x in [-22,22]:
            c=ring('clamp',(x,my,mz),16,12.8,6,'X'); union(c,box('riser',(x,my,113),(6,8,6)))
            if mount is None: mount=c
            else: union(mount,c)
        union(mount,box('bridge',(0,my,114.5),(50,8,3)))
        for x in [-22,22]: boolean(mount,cyl('pilot',(x,my,114),2.05,6))
        boolean(mount,cyl('motor_body_clear',(0,my,mz),12.8,70,'X'))
        mount.name=PREFIX+'Motor_Mount_'+n; done(mount,'电机座 '+n,'frame',ex=(s*15,-s*35,10)); contact('Load_Frame','Motor_Mount_'+n,'Clamp top / deck underside')
        for y,z,tag,ri in [(my,mz,'Motor',2.2),(0,wz,'Axle',3.2)]:
            ref(ring('Pulley_'+n+'_'+tag,(s*40.5,y,z),5.5,ri,3,'X'),'带轮占位 '+n+' '+tag,'dark')
        # Belt is a closed capsule shell generated in the actual transmission plane.
        a=Vector((0,wz)); b=Vector((my,mz)); dv=(b-a).normalized(); pts=[]
        for center,direction in [(b,dv),(a,-dv)]:
            for k in range(33):
                ang=-math.pi/2+k*math.pi/32; v=direction*math.cos(ang)+Vector((-direction.y,direction.x))*math.sin(ang); pts.append((center,v))
        verts=[]; nn=len(pts)
        for x,r in [(s*40.5-1.5,5.55),(s*40.5+1.5,5.55),(s*40.5-1.5,6.3),(s*40.5+1.5,6.3)]:
            verts += [(x,c.x+v.x*r,c.y+v.y*r) for c,v in pts]
        faces=[]
        for k in range(nn):
            j=(k+1)%nn; faces += [(k,j,nn+j,nn+k),(2*nn+k,3*nn+k,3*nn+j,2*nn+j),(k,2*nn+k,2*nn+j,j),(nn+k,nn+j,3*nn+j,3*nn+k)]
        belt=mesh('Belt_'+n,verts,faces); recalc(belt); ref(belt,'带传动动态包络 '+n,'belt',note='Smooth pitch envelope only. Teeth, tension, ratio, backlash and torque response NOT designed/verified')
        for tag in ['Motor','Axle']: contact('Belt_'+n,'Pulley_'+n+'_'+tag,'Pitch-circle tangent envelope; not a meshing teeth model')

def frame_and_electronics():
    dr=P['drive']; l=P['layout']; dz=l['deck_z_mm']; hz=D['head_z']
    frame=cyl('Load_Frame',(0,0,dz),69,4); intersect(frame,box('clip',(0,0,dz),(116,100,10)))
    for s in [-1,1]:
        for x in dr['bearing_abs_x_mm']:
            p=ring('bearing_carrier',(s*x,0,D['wheel_z']),8.8,6.75,5,'X')
            union(p,box('pylon',(s*x,0,85),(5,8,62)))
            boolean(p,cyl('bearing_clear',(s*x,0,D['wheel_z']),6.75,8,'X')); union(frame,p)
    for x,y in [(55,18),(-55,18),(55,-18),(-55,-18),(-22,-20),(22,-20),(-22,20),(22,20)]:
        boolean(frame,cyl('screw',(x,y,dz),1.7,12))
    for x,y in [(-47,22),(33,-36)]: boolean(frame,cyl('wire_channel',(x,y,dz),4,12))
    boolean(frame,box('yaw_servo_pass',(0,0,dz),(32,21,12)))
    done(frame,'内部承重框架与双轮轴承座','frame',ex=(0,0,15)); contact('Load_Frame','Body_Upper','Four chassis bosses, screw heads accessed after lower-shell removal')
    # Battery tray: adjustable +/-4 mm in Y with slots, removable downward after disconnect.
    bc=l['battery_center_mm']; ref(box('Battery',bc,l['battery_max_xyz_mm']),'电池最大包络（容量未定）','battery')
    tray=box('Battery_Tray',(0,0,58.5),(45,83,3))
    for s in [-1,1]: union(tray,box('side',(s*21.6,0,66),(2,83,15)))
    for s in [-1,1]: union(tray,box('end',(0,s*40.5,62),(45,2,7)))
    for y in [-38,38]:
        boolean(tray,box('strap_slot',(0,y,58.5),(17,2,7)))
    # Four hanger tabs carry tray load into the frame, not the cosmetic lower shell.
    for i,(x,y) in enumerate([(18,45),(-18,45),(18,-45),(-18,-45)]):
        tab=box('tab',(x,y,58.5),(9,13,3)); union(tray,tab)
        slot=cyl('slot_end',(x,y-4,58.5),1.7,8); union(slot,cyl('slot_end',(x,y+4,58.5),1.7,8)); union(slot,box('slot_mid',(x,y,58.5),(3.4,8,8))); boolean(tray,slot)
        ref(cyl('Battery_Hanger_'+str(i),(x,y,88),1.5,55),'电池托架吊杆 '+str(i),'metal')
        contact('Battery_Hanger_'+str(i),'Battery_Tray','Slot screw/nut interface; battery module removable after hanger release')
    done(tray,'可调电池托架','frame',ex=(0,-35,-25)); contact('Battery_Tray','Battery','Bottom seat; 0.6 mm side reserve')
    for i,loc in enumerate(l['mcu_centers_mm']):
        label='交互 MCU' if i==0 else '运动 MCU'; name='Interaction' if i==0 else 'Motion'
        ref(box('MCU_'+name,loc,l['mcu_max_xyz_mm']),label+' 最大包络','pcb')
        m=box('MCU_Mount_'+name,(loc[0],loc[1],121.5),(52,28,3)); done(m,label+' 支架','frame')
        contact('MCU_Mount_'+name,'Load_Frame','PCB baseplate to deck'); contact('MCU_Mount_'+name,'MCU_'+name,'Board underside allocation seat')
        k=box('Antenna_Clear_'+name,(32,loc[1],131),(15,28,18)); done(k,'天线净空 '+name,'keepout','body','KEEP_OUT',False,note='No metal/wire keepout; RF performance unverified',role='keepout')
        k=box('USB_Debug_Clear_'+name,(0,loc[1]+(23 if loc[1]>0 else -23),130),(14,22,12)); done(k,'MCU USB 调试插头空间 '+name,'keepout','body','KEEP_OUT',False,role='keepout')
    imu=ref(box('Body_IMU',l['imu_center_mm'],l['imu_max_xyz_mm']),'身体刚性 IMU 包络','pcb')
    im=box('IMU_Mount',(39,0,121),(30,22,2)); done(im,'IMU 刚性安装座','frame'); contact('IMU_Mount','Load_Frame','Rigid frame seat'); contact('IMU_Mount','Body_IMU','Rigid mount seat')
    for ax,col,delta in [('X','red',(12,0,0)),('Y','green',(0,12,0)),('Z','blue',(0,0,12))]:
        o=beam('IMU_Axis_'+ax,(39,0,126),(Vector((39,0,126))+Vector(delta)),.45); done(o,'IMU '+ax,'metal','body','ANNOTATIONS',False,role='annotation')
    for name,loc,dim,label in [('Audio_Amp',(-37,-7,126),(22,18,6),'功放'),('Motor_Driver',(0,-52,92),(30,22,8),'轮驱模块'),('Power_Module',(34,-44,87),(24,16,8),'保护/稳压模块'),('USB_Charge',(14,-56,108),(24,18,8),'USB-C 充电模块')]:
        dim=INTERFACES['components'][{'Audio_Amp':'audio_amp','Motor_Driver':'motor_driver','Power_Module':'power_module','USB_Charge':'usb_power'}[name]]['max_xyz_mm']
        ref(box(name,loc,dim),label+' 包络','pcb')
        mo=box(name+'_Mount',(loc[0],loc[1],loc[2]-dim[2]/2-1),(dim[0]+(2 if name in ['Motor_Driver','Audio_Amp'] else 4),dim[1]+4,2)); intersect(mo,sphere('module_mount_inner',(0,0,D['body_z']),72.1))
        if name=='USB_Charge': boolean(mo,cyl('hanger_relief',(18,-45,103),2.1,10))
        if name=='Audio_Amp': union(mo,box('frame_seat',(-37,-7,120.5),(24,22,1)))
        posts={'Motor_Driver':[(-11,-38.8),(11,-38.8)],'Power_Module':[(49.5,-42),(49.5,-36)],'USB_Charge':[(4,-44),(26,-44)]}.get(name,[])
        for xx,yy in posts:
            z0=loc[2]-dim[2]/2-1
            union(mo,box('hanger_tab',(xx,yy,z0),(6,6,2)))
            union(mo,cyl('frame_hanger',(xx,yy,(z0+116)/2),1.8,116-z0))
        done(mo,label+' 固定件','frame')
        contact(name,name+'_Mount','Module bottom seat; mounting holes pending supplier selection')
    ref(cyl('Speaker',(0,61,95),15,6,'Y'),'扬声器包络','dark')
    cup=ring('Speaker_Mount',(0,62,95),17.4,15.4,14,'Y'); union(cup,cyl('back',(0,55.5,95),17.4,1,'Y'))
    for sign in [-1,1]:
        q=beam('speaker_brace',(sign*17,58,95),(sign*27,46,114),2.2); clip_z(q,-500,116); union(cup,q)
    done(cup,'独立扬声器声腔固定件','frame',note='Separate rear cup; acoustic sealing, volume and frequency response NOT_TESTED')
    ref(box('Microphone',(-36,38,136),(12,8,4)),'独立麦克风模块','pcb')
    mic=box('Microphone_Mount',(-36,35,132.5),(16,12,3)); 
    for xx in [-41,-31]: union(mic,cyl('mic_post',(xx,35,125.5),1.8,11))
    done(mic,'独立麦克风固定件','frame')
    duct=ring('Mic_Duct',(-36,49,136),2.6,1,14,'Y'); intersect(duct,sphere('inner_limit',(0,0,D['body_z']),72.3)); done(duct,'麦克风独立声道','dark')
    usb=box('USB_Receptacle',(14,-70,108),(10,8,4),.5); boolean(usb,box('usb_socket_open',(14,-73,108),(8.4,6,2.6),.5)); ref(usb,'USB-C 插座（开口与壳体包络）','metal',note='Generic hollow connector allocation; contacts/retention and vendor dimensions unverified')
    ref(box('Power_Switch',(-14,-68,103),(10,8,6)),'低调电源开关 / 硬件断电接口候选','dark')
    ref(cyl('Function_Button',(0,-58,149),4,10,'Y'),'实体功能按钮','dark')
    # Explicit finger and plug approach allocations, hidden in normal render.
    for name,loc,dim in [('USB_Plug_Clear',(14,-93,108),(16,35,10)),('Button_Finger_Clear',(0,-82,149),(20,30,20)),('Switch_Finger_Clear',(-14,-86,103),(22,30,18))]:
        done(box(name,loc,dim),'操作空间 '+name,'keepout','body','KEEP_OUT',False,role='keepout')
    # Routing shows body paths away from tyres, with physical clamps. Cables are not solid rigid parts.
    paths=[('Head_Trunk',[(-47,22,110),(-47,22,141),(-18,6,138)],'body'),('Yaw_Bore_Fixed',[(-17.55,4,139),(-6.4,4,139),(-6.4,0,139),(-6.4,0,168),(0,0,174)],'body'),('Yaw_Head_Lead',[(0,0,174),(25,-17,185),(29,-5,hz-5)],'yaw'),('Battery_Lead',[(0,-37.3,79),(0,-40,82),(0,-34.5,85),(34,-34.5,85),(34,-34.5,87)],'body'),('Screen_Lead',[(0,27,hz+4),(18,17,hz-5),(29,0,hz)],'pitch'),('Camera_Lead',[(8.3,27,hz+33),(17,18,hz+26),(29,5,hz+5)],'pitch')]
    for name,pts,grp in paths:
        path=None
        for a,b in zip(pts,pts[1:]):
            q=beam('wire',a,b,1.2)
            if path is None: path=q
            else: union(path,q)
        path.name=PREFIX+name; done(path,'线束路径 '+name,'copper',grp,'PLACEHOLDER',False,note='Routing reservation; actual wire count/connector radii and flexible sweep pending',role='routing')
    for name,loc in [('Body_Cable_Clip',(-47,22,135))]: done(ring(name,loc,3.3,1.7,3),'线束固定夹','frame')

def fasteners_and_coupons():
    for family,coords,z0,z1,r in [('Shell',[(55,28),(-55,28),(55,-28),(-55,-28)],89,105,1.5),('Frame',[(55,18),(-55,18),(55,-18),(-55,-18)],114,124,1.5)]:
        for i,(x,y) in enumerate(coords):
            screw=cyl(f'{family}_Screw_{i}',(x,y,(z0+z1)/2),r,z1-z0); union(screw,cyl('head',(x,y,z0-1),2.7,2))
            ref(screw,'试配螺丝 '+family+str(i),'metal'); ref(ring(f'{family}_Insert_{i}',(x,y,z1-2),1.98,1.5,4),'热熔嵌件包络 '+family+str(i),'metal')
            contact(f'{family}_Screw_{i}',f'{family}_Insert_{i}','Smooth thread envelopes; real threads and insertion process TBD')
    # Coupons deliberately use an array of gaps and pilots, not a universal 0.3 mm rule.
    coupon=box('Coupon_Insert',(0,0,0),(48,18,8))
    for x,d in zip([-18,-9,0,9,18],[3.7,3.9,4.1,4.3,4.5]): boolean(coupon,cyl('pilot',(x,0,1),d/2,6))
    done(coupon,'嵌件孔径阶梯试样','coupon','coupon','COUPONS',True,note='Pilot diameters 3.7/3.9/4.1/4.3/4.5; use selected insert vendor data and same print process',role='coupon')
    coupon=box('Coupon_Plane_Fit',(0,0,0),(52,20,6))
    for x,g in zip([-20,-10,0,10,20],[.15,.25,.35,.45,.6]): boolean(coupon,box('slot',(x,0,0),(4+2*g,12,10)))
    done(coupon,'平面装配间隙试样','coupon','coupon','COUPONS',True,note='Per-side gaps 0.15/0.25/0.35/0.45/0.60 mm against 4 mm mating tab',role='coupon')
    done(box('Coupon_Mating_Tab',(0,0,0),(4,11.5,12)),'间隙试样配合片','coupon','coupon','COUPONS',True,role='coupon')

def dock():
    d=P['dock']; lift=d['robot_lift_mm']; bz=D['body_z']+lift; ro=D['body_radius']
    base=box('Parking_Cradle',(0,0,4),d['base_xyz_mm'],3)
    for x,y in d['contact_xy_mm']:
        seat=bz-math.sqrt(ro*ro-x*x-y*y); arm=box('support',(x,y,(8+seat-1)/2),(15,15,seat-1-8))
        union(base,arm)
    # Spherical seating relief at the actual docked body position.
    boolean(base,sphere('body_relief',(0,0,bz),ro+1.8))
    done(base,'独立停放 / 刷机 / 有线充电托架','frame','dock','DOCK',True,ex=(0,-150,0),note='Separate maintenance-only accessory. Lift robot 8 mm, disable wheel drive. No motors/charging contacts; does not prove free-standing stability')
    for i,(x,y) in enumerate(d['contact_xy_mm']):
        seat=bz-math.sqrt(ro*ro-x*x-y*y); pad=box('Dock_Pad_'+str(i),(x,y,seat-.5),(13,13,5))
        boolean(pad,sphere('body_surface',(0,0,bz),ro)); intersect(pad,sphere('padouter',(0,0,bz),ro+1.8))
        done(pad,'托架软接触垫 '+str(i),'tire','dock','DOCK',False,note='Separate soft pad / TPU or rubber; nominal spherical contact, compliance and friction unmeasured')

def controls_datums():
    root=empty('CTRL_Root',(0,0,D['wheel_z'])); yaw=empty('CTRL_Yaw',(0,0,D['head_z'])); pitch=empty('CTRL_Pitch',(0,0,D['head_z']))
    def parent_keep(o,p):
        bpy.context.view_layer.update(); mw=o.matrix_world.copy(); o.parent=p; o.matrix_world=mw
    parent_keep(yaw,root); parent_keep(pitch,yaw)
    wheels={}
    for s,n in [(-1,'L'),(1,'R')]:
        w=empty('CTRL_Wheel_'+n,(s*D['wheel_x'],0,D['wheel_z'])); parent_keep(w,root); wheels['wheel_'+n]=w
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH' or not o.get('group') or o.get('group') in ['coupon','dock']: continue
        group=o.get('group'); p=pitch if group=='pitch' else yaw if group=='yaw' else wheels.get(group,root)
        parent_keep(o,p); o['assembled_local_location_mm']=list(o.location)
    for n,r,z in [('Body_Mother',D['body_radius'],D['body_z']),('Head_Mother',D['head_radius'],D['head_z'])]:
        o=sphere(n,(0,0,z),r); move_collection(o,'DATUMS'); o['role']='construction'; o['mother_radius_mm']=r
    for name,loc,dim in [('Body_Top_Plane',(0,0,D['body_top_z']),(170,170,.1)),('Left_Cut_Plane',(-62,0,100),(.1,170,160)),('Right_Cut_Plane',(62,0,100),(.1,170,160)),('Ground_Plane',(0,0,0),(230,230,.1))]:
        o=box(name,loc,dim); move_collection(o,'DATUMS'); o['role']='construction'
    for name,loc,axis in [('Yaw_Axis',(0,0,D['head_z']),'Z'),('Pitch_Axis',(0,0,D['head_z']),'X')]:
        o=cyl(name,loc,.3,110,axis); move_collection(o,'DATUMS'); o['role']='construction'
    yaw['allowed_yaw_deg']=[-60,60]; pitch['allowed_pitch_deg']=[-20,25]
    yaw['hint']='Edit rotation Z in degrees. Physical bearing at z=158, axis passes through head center.'
    pitch['hint']='Edit local rotation X in degrees; positive lifts head. Camera and display parented here.'

def studio():
    sc=bpy.context.scene; sc.world=bpy.data.worlds.new('MORI_V1_World'); mark(sc.world); sc.world.use_nodes=True; next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.18,.2,.24,1)
    next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.45
    for name,loc,power,size in [('Key',(-300,350,520),1900000,300),('Fill',(300,180,340),900000,250),('Rim',(80,-320,440),1500000,230)]:
        data=mark(bpy.data.lights.new(PREFIX+name,'AREA')); data.energy=power; data.shape='DISK'; data.size=size
        o=mark(bpy.data.objects.new(PREFIX+name,data)); COLS['CAMERAS_LIGHTS'].objects.link(o); o.location=loc; o.rotation_euler=(Vector((0,0,130))-o.location).to_track_quat('-Z','Y').to_euler()
    ground=box('Studio_Ground',(0,0,-1.6),(3000,3000,3)); done(ground,'渲染地面','ground','studio','CAMERAS_LIGHTS',False,role='studio')
    sc.view_settings.view_transform='AgX'; sc.render.image_settings.file_format='PNG'; sc.render.film_transparent=False

def main():
    start=time.time(); timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(); scene=setup_scene()
    for name,col in [('shell',(.83,.81,.75)),('frame',(.20,.27,.30)),('tire',(.042,.046,.052)),('metal',(.48,.52,.56)),('pcb',(.025,.19,.13)),('battery',(.11,.13,.16)),('dark',(.003,.004,.006)),('blue',(.055,.16,.35)),('copper',(.6,.22,.055)),('belt',(.07,.07,.07)),('coupon',(.48,.64,.67)),('ground',(.20,.23,.28)),('keepout',(.7,.22,.1))]: material(name,col,metallic=.7 if name=='metal' else 0,roughness=.72 if name in ['shell','tire'] else .45)
    material('glass',(.9,.97,1),roughness=.12,transmission=1); material('eye',(.07,.83,.92),roughness=.4,emission=2)
    for fn in [shells,optics,head_joint,wheel_and_drive,frame_and_electronics,fasteners_and_coupons,dock,controls_datums,studio]:
        print('BUILD '+fn.__name__,flush=True); fn()
    
    for o in parts(True):
        clean(o)
        if o.name.removeprefix(PREFIX) in ['Body_Upper','Body_Lower']:
            for f in o.data.polygons:
                if abs(f.normal.x)>.999: f.use_smooth=False
    assembled(); write_bom(); save_json(ROOT/'reports/derived.json',D); save_json(ROOT/'reports/intended_contacts.json',CONTACTS)
    # Derived instance coordinates are a build result, never an independently editable dimension source.
    instances={o.name.removeprefix(PREFIX):{'frame_id':'assembly_ground','timestamp_utc':timestamp,'category':o.get('category'),'data_status':o.get('data_status'),'group':o.get('group'),'bounds_xyz_mm':bounds(o),'origin_world_mm':list(o.matrix_world.translation)} for o in parts()}
    save_json(ROOT/'reports/assembly_instances.json',instances)
    save_json(ROOT/'reports/build_manifest.json',{'blender':bpy.app.version_string,'blender_hash':bpy.app.build_hash.decode(),'python':platform.python_version(),'manifold3d':'3.5.3','owner':OWNER,'objects':len([o for o in scene.objects if o.get('mori_owner')==OWNER]),'parts':len(parts()),'actuators':[o.name for o in parts() if o.get('actuator_id')],'elapsed_s':round(time.time()-start,1),'input_sha256':{str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [PROJECT/'config/geometry.json',PROJECT/'contracts/mechanical_interfaces.json',PROJECT/'MORI_SPEC_V1.md']}})
    # Explicit position / extrinsic convention for later calibration.
    save_json(ROOT/'reports/camera_kinematics.json',{'status':'ASSUMED','units':'mm','frame_id':'body_axle','timestamp_utc':timestamp,'head_center_in_body_axle_mm':[0,0,D['head_z']-D['wheel_z']],'head_center_in_assembly_ground_mm':[0,0,D['head_z']],'nominal_T_body_axle_camera_mm':[[1,0,0,0],[0,0,1,P['camera']['pupil_from_head_mm'][1]],[0,-1,0,D['head_z']-D['wheel_z']+P['camera']['pupil_from_head_mm'][2]],[0,0,0,1]],'yaw_axis_body':[0,0,1],'pitch_axis_yaw':[1,0,0],'pupil_in_pitch':P['camera']['pupil_from_head_mm'],'camera_CV_axes_in_pitch':{'x_right':[1,0,0],'y_image_down':[0,0,-1],'z_optical':[0,1,0]},'transform':'T_body_axle_camera = T(0,0,head_z-wheel_radius) Rz(yaw_rad) Rx(pitch_rad) T(pupil) R_CV; T_world_camera = T_world_body_axle * T_body_axle_camera','angle_feedback':'estimated unless measured joint feedback is added','timestamp_requirement':'Frame and monotonic capture timestamp required for observations and joint estimates','calibration':'Intrinsics, distortion, window refraction, servo zero/backlash and actual extrinsics NOT_TESTED'})
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=420; area.spaces.active.region_3d.view_location=(0,0,130); area.spaces.active.clip_end=10000; area.spaces.active.region_3d.view_rotation=Vector((380,500,200)).to_track_quat('Z','Y'); area.spaces.active.region_3d.view_perspective='ORTHO'
    bpy.context.view_layer.update(); bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/MORI_V1_A.blend'))
    print('BUILD_COMPLETE',flush=True)
if __name__=='__main__': main()
