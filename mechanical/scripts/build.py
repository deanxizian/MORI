"""MORI V1.2 M1/M2 pre-study. Run with Blender --background --python mechanical/scripts/build.py."""
import sys,math,json,hashlib,platform,time,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from purchased_geometry import apply_purchased_geometry
from structural_simplification import apply_structural_simplification
from monocoque_structure import apply_monocoque_structure
from simple_modules import apply_simple_modules
from belly_relayout import apply_belly_relayout
from detail_fit import apply_detail_fit
from layout_cleanup import apply_layout_cleanup
from part_consolidation import apply_part_consolidation
from wheel_interfaces import apply_wheel_interfaces
from yaw_bridge_mount import apply_crossbolt_joint
from native_electronics import apply_native_electronics
from head_cleanup import apply_head_cleanup
from drive_cleanup import apply_drive_cleanup
from optics_mount import display_transform,camera_transform,camera_pupil,apply_mount
CONTACTS=[]

def contact(a,b,reason): CONTACTS.append(dict(a=a,b=b,reason=reason))
def done(o,label,mat='frame',group='body',cat='PRINTABLE',export=True,ex=(0,0,0),note='Candidate trial geometry; vendor fasteners and fits pending Stage B',role='part'):
    return finish(o,cat,label,mat,group,export,ex,note,role)
def ref(o,label,mat='metal',group='body',ex=(0,0,0),note='ASSUMED maximum allocation; not a selected supplier part'):
    return done(o,label,mat,group,'PLACEHOLDER',False,ex,note)
def beam(name,a,b,r=2.5):
    a=Vector(a); b=Vector(b); o=cyl(name,(a+b)/2,r,(b-a).length)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); bpy.context.view_layer.update(); return o

def button_axis():
    dz=P['user_interfaces']['button_surface_z_mm']-D['body_z']
    sh=P['shape']['variants'][P['shape']['selected']]; sy=math.sqrt(D['body_radius']**2-dz**2)*(1+sh['shoulder_bias']*dz/D['body_radius'])*sh['depth_scale']
    surface=Vector((0,-sy,D['body_z']+dz))
    return surface,(surface-Vector((0,0,D['body_z']))).normalized()

def radial_button_cylinder(name,r,depth,inset):
    surface,axis=button_axis();o=cyl(name,surface-axis*inset,r,depth)
    o.rotation_euler=axis.to_track_quat('Z','Y').to_euler();bpy.context.view_layer.update();return o

def seam_mount_x():
    # Preserve nominal material beyond the screwdriver counterbore when a wheel pocket moves in.
    f=P['shell_service'];return min(f['preferred_mount_abs_x_mm'],P['body_side_cut_x_mm']-P['shell_thickness_mm']-f['counterbore_radius_mm']-f['extra_wall_margin_mm'])

def wheel_relief(name,sign,offset=0):
    """Rounded-end axial cutter. Offset version preserves the local pocket wall."""
    x0=P['body_side_cut_x_mm']-offset
    fillet=P['body_wheel_relief']['corner_radius_mm']+offset
    radial=D['wheel_radius']+P['wheel_body_gap_mm']
    profile=[(x0,radial)]
    for i in range(1,17):
        a=math.pi/2*i/16
        profile.append((x0+fillet*(1-math.cos(a)),radial+fillet*math.sin(a)))
    profile.append((200,radial+fillet))
    n=128;verts=[];faces=[]
    for x,r in profile:
        for k in range(n):
            a=2*math.pi*k/n;verts.append((sign*x,r*math.cos(a),D['wheel_z']+r*math.sin(a)))
    for j in range(len(profile)-1):
        for k in range(n):
            q=(k+1)%n;faces.append((j*n+k,j*n+q,(j+1)*n+q,(j+1)*n+k))
    faces.append(tuple(reversed(range(n))));faces.append(tuple((len(profile)-1)*n+k for k in range(n)))
    o=mesh(name,verts,faces);recalc(o);return o

def body_profile(name, wall_offset=0):
    o=sphere(name,(0,0,D['body_z']),D['body_radius']-wall_offset)
    sh=P['shape']['variants'][P['shape']['selected']]
    for v in o.data.vertices:
        u=v.co.z/(D['body_radius']-wall_offset)
        v.co.x*=1+sh['shoulder_bias']*u
        v.co.y*=(1+sh['shoulder_bias']*u)*sh['depth_scale']
    return o

def body_outer(name,wall_offset=0):
    o=body_profile(name,wall_offset)
    clip_z(o,-500,D['body_top_z']-wall_offset)
    if P.get('body_wheel_relief',{}).get('mode')=='local_rounded_pocket':
        for s in [-1,1]: boolean(o,wheel_relief('wheel_pocket',s,wall_offset))
    else:
        intersect(o,box('clip',(0,0,100),(2*(P['body_side_cut_x_mm']-wall_offset),1000,1000)))
    return o

def shells():
    t=P['shell_thickness_mm']; bz=D['body_z']; hz=D['head_z']; side=P['body_side_cut_x_mm']; gap=P['seam_gap_mm']/2
    outer=body_outer('body_outer_temp'); inner=body_outer('inner',t)
    shell=clone(outer,'body_shell_temp'); boolean(shell,inner)
    boolean(shell,cyl('top_open',(0,0,D['body_top_z']),P['body_top_opening_diameter_mm']/2,25))
    boolean(shell,cyl('axle_bore',(0,0,D['wheel_z']),4.2,180,'X'))
    # Actual rear port cutouts; separate complete module and external plug allocations below.
    if not P.get('native_electronics',{}).get('enabled'):
        boolean(shell,box('usb_cut',(P['detail_fit']['ports']['x_mm'],-71,P['detail_fit']['ports']['usb_z_mm']),(12,30,6)))
        boolean(shell,box('switch_cut',(P['detail_fit']['ports']['x_mm'],-70,P['detail_fit']['ports']['switch_z_mm']),(12,30,8)))
    if P.get('layout_cleanup',{}).get('function_button_enabled',True):boolean(shell,radial_button_cylinder('button_cut',4.4,40,3))
    # Existing speaker grille dimensions now share the mechanical JSON.
    grille=P['speaker_mount']['grille']
    for x in grille['x_mm']:
        for zz in grille['z_from_body_mm']:
            boolean(shell,cyl('speaker_hole',(x,grille['bore_center_y_mm'],body_z_mm(zz)),grille['bore_radius_mm'],grille['bore_length_mm'],'Y',16))
    # Board microphones now in the moving head; no independent body microphone.
    upper=clone(shell,'Body_Upper'); lower=clone(shell,'Body_Lower'); clip_z(upper,bz+gap,500); clip_z(lower,-500,bz-gap)
    # Four load-frame seats, connected to side walls. Trial M3 insert pilots.
    frame_top=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    for x,y in P['shell_service']['frame_mount_xy_mm']:
        boss=cyl('boss',(x,y,frame_top+3),5.7,6); intersect(boss,clone(outer,'limit')); union(upper,boss)
        rib=box('frame_seat_rib',(math.copysign((abs(x)+73)/2,x),y,frame_top+4.5),(73-abs(x),8,3));intersect(rib,clone(outer,'limit'));union(upper,rib)
        boolean(upper,cyl('pilot',(x,y,frame_top+2.5),2.05,5.2))
    # Lower-shell seams: radial tabs remain separately accessible from below.
    sx=seam_mount_x();sy=P['shell_service']['seam_mount_abs_y_mm']
    for x,y in [(sx,sy),(-sx,sy),(sx,-sy),(-sx,-sy)]:
        boss=cyl('seam_boss',(x,y,body_z_mm(3.5)),5.7,6.4); intersect(boss,clone(outer,'limit')); union(upper,boss)
        rib=box('upper_seam_rib',(math.copysign((abs(x)+73)/2,x),y,body_z_mm(4.5)),(73-abs(x),8,4));intersect(rib,clone(outer,'limit'));union(upper,rib)
        boolean(upper,cyl('pilot',(x,y,body_z_mm(3)),2.05,5.6))
        sleeve=cyl('seam_sleeve',(x,y,body_z_mm(-8)),5.7,15.4); intersect(sleeve,clone(outer,'limit')); union(lower,sleeve)
        rib=box('lower_seam_rib',(math.copysign((abs(x)+73)/2,x),y,body_z_mm(-6)),(73-abs(x),8,4));intersect(rib,clone(outer,'limit'));union(lower,rib)
        boolean(lower,cyl('screw_bore',(x,y,body_z_mm(-9)),1.7,20))
        boolean(lower,cyl('tool_counterbore',(x,y,body_z_mm(-58)),P['shell_service']['counterbore_radius_mm'],94))
    done(upper,'身体上壳','shell',ex=(0,0,55)); done(lower,'身体下壳','shell',ex=(0,0,-48))
    # True spherical head with a real lower cap opening; front/rear split is Y=0.
    ho=sphere('head_outer',(0,0,hz),D['head_radius']); clip_z(ho,hz+P['head_lower_opening_z_from_center_mm'],500)
    hs=clone(ho,'head_shell_temp'); boolean(hs,sphere('cavity',(0,0,hz),D['head_radius']-t))
    dp=P['display']; cz=hz+dp['z_from_head_mm']
    mask_z=hz+dp.get('mask_z_from_head_mm',0)
    boolean(hs,apply_mount(cyl('face_open',(0,60,mask_z),dp['aperture_diameter_mm']/2,50,'Y'),display_transform()))
    if P['camera'].get('independent_forehead_window'):
        cx,cy,cz=P['camera']['pupil_from_head_mm']
        opening=cyl('forehead_camera_open',(cx,cy,hz+cz),P['camera']['aperture_diameter_mm']/2,40,'Y')
        opening.scale.x=P['camera'].get('aperture_horizontal_diameter_mm',P['camera']['aperture_diameter_mm'])/P['camera']['aperture_diameter_mm']
        bpy.context.view_layer.update();boolean(hs,apply_mount(opening,camera_transform()))
    mq=P['microphone_acoustics']
    for sign in [-1,1]: boolean(hs,cyl('head_mic_port',(sign*mq['shell_port_abs_x_mm'],mq['shell_port_y_mm'],hz+mq['shell_port_z_from_head_mm']),mq['shell_port_radius_mm'],mq['shell_port_cut_length_mm'],'Y',24))
    hf=clone(hs,'Head_Front'); hb=clone(hs,'Head_Rear'); clip_y(hf,gap,500); clip_y(hb,-500,-gap)
    for s in [-1,1]:
        lug=box('cradle_lug',(s*48,3.5,hz+29),(10,6,8)); intersect(lug,clone(ho,'limit')); union(hf,lug)
        mx,my=head_shell_mount_xy_mm(s)
        boolean(hf,cyl('lug_pilot',(mx,my,hz+28.1),1.6,7.2))
        # Two rear seam screw sleeves and front sockets, local and well above the moving guard.
        lug=cyl('seam_front',(s*43,3,hz+37),4.2,5.4,'Y'); intersect(lug,clone(ho,'limit')); union(hf,lug)
        boolean(hf,cyl('pilot',(s*43,2,hz+37),1.6,4,'Y'))
        lug=cyl('seam_rear',(s*43,-8,hz+37),4.2,15.4,'Y'); intersect(lug,clone(ho,'limit')); union(hb,lug)
        boolean(hb,cyl('bore',(s*43,-10,hz+37),1.2,30,'Y'))
        boolean(hb,cyl('counter',(s*43,-20,hz+37),2.4,15,'Y'))
    done(hf,'头前壳','shell','pitch',ex=(0,60,110)); done(hb,'头后壳','shell','pitch',ex=(0,-60,110))
    for o in [outer,shell,ho,hs]: bpy.data.objects.remove(o,do_unlink=True)

def optics():
    hz=D['head_z'];dp=P['display'];z=hz+dp['z_from_head_mm'];fy=D['face_y'];cam=P['camera'];cz=cam['pupil_from_head_mm'][2];pcb_z=cam['body_center_from_head_mm'][2]
    mask=cyl('Face_Mask',(0,fy,hz+dp.get('mask_z_from_head_mm',0)),dp['mask_outer_diameter_mm']/2,1,'Y')
    boolean(mask,cyl('active_open',(0,fy,z),23.4,5,'Y'))
    if not cam.get('independent_forehead_window'):
        boolean(mask,cyl('camera_open',(0,fy,hz+cz),cam['aperture_diameter_mm']/2,5,'Y'))
    done(mask,'圆屏独立黑面罩（非全区域显示）','dark','pitch','PURCHASED_REFERENCE',False,(0,85,95),'Flat opaque sheet candidate around real LCD; separate camera window is in forehead shell. No curved glass.')
    frame=ring('Display_Frame',(0,40,z),30,27.9,3,'Y');union(frame,ring('screen_lip',(0,39,z),29.5,23.2,1,'Y'))
    done(frame,'1.85圆屏固定框','dark','pitch',ex=(0,40,90))
    ref(cyl('Display_PCB',(0,42,z),27.5,2,'Y'),'圆屏后部构造模板（非原厂PCB边界）','pcb','pitch',note='55mm vendor outline bound; circular boundary and thickness2 are provisional; full vendor outline/connector review pending')
    done(box('Display_Outline_Allocation',(0,42,z),(55,8,55)),'55x55全矩形显示模组限制包络','keepout','pitch','KEEP_OUT',False,role='keepout',note='Vendor only documents55x55;8mm thickness assumed. Do not infer a55mm circle. Full box collision result is a conditional M2 blocker pending exact outline; do not cut shell blindly.')
    ref(cyl('Display_Module',(0,48.4,z),22.84,2.8,'Y'),'45.68mm 有效显示层','dark','pitch',note='Active diameter45.68 vendor documented; thickness3 allocation assumed')
    done(cyl('Face_Protector',(0,50.55,z),23.25,.6,'Y'),'平面显示保护片','glass','pitch','PURCHASED_REFERENCE',False,(0,100,95))
    ref(box('Display_Connector',(0,37,z-17),(12,3,5)),'LCD 18PIN连接器预留','dark','pitch')
    for sign,n in [(-1,'L'),(1,'R')]:
        eye=box('Eye_'+n,(sign*9,49.86,z),(6,.10,6))
        for zz in [-3,3]:union(eye,cyl('eye_round',(sign*9,49.86,z+zz),3,.10,'Y'))
        done(eye,'双眼像素 '+n,'eye','pitch','PURCHASED_REFERENCE',False,role='display_content',note='Display pixels only, within45.68 active circle')
    pcb_loc=Vector(cam['body_center_from_head_mm'])+Vector((0,0,hz))
    ref(box('Camera_PCB',pcb_loc,cam.get('pcb_allocation_xyz_mm',[12,3,10])),'OV3660 镜头小板限制包络','pcb','pitch',note='ASSUMED; original FPC/sensor lens package must be measured')
    lens_depth=cam.get('lens_depth_mm',7)
    ref(cyl('Camera_Lens',(0,cam['pupil_from_head_mm'][1]-lens_depth/2,hz+cz),cam.get('lens_allocation_diameter_mm',5)/2,lens_depth,'Y'),'OV3660 镜筒包络','lens','pitch')
    done(cyl('Camera_Window',(0,cam.get('window_y_from_head_mm',50.6),hz+cz),3.85,.6,'Y'),'额头独立相机透光窗口','camera_glass','pitch','PURCHASED_REFERENCE',False,note='Separate flat optical sheet outside display mask; actual transmissivity/refraction untested')
    b=ring('Camera_Baffle',(0,cam.get('baffle_center_y_from_head_mm',48),hz+cz),3.85,3.1,3.7,'Y');done(b,'相机遮光框','dark','pitch')
    m=box('Camera_Mount',(0,pcb_loc.y-2.6,hz+pcb_z),(16,2,12))
    for s in [-1,1]:union(m,beam('camera_brace',(s*8,37.4,hz+pcb_z+1),(s*8,3,hz+35.5),1.5))
    done(m,'OV3660 支架','frame','pitch')
    l=P['layout'];loc=Vector(l['cam_board_center_from_head_mm'])+Vector((0,0,hz))
    cam=ref(box('CAM_Mainboard',loc,l['cam_board_allocation_xyz_mm']),'CAM33700整板限制包络 / 双麦音频','pcb','pitch',note='ASSUMED50x45 board and12mm thickness allocation, not vendor-confirmed; DVP/QSPI stay on pitch group')
    m=box('CAM_Mainboard_Mount',(0,-31,hz+13),(54,2,49))
    for s in [-1,1]:union(m,beam('cam_side_support',(s*27,-31,hz+32),(s*27,3,hz+34.5),1.7))
    done(m,'头内 CAM 整板支架','frame','pitch',ex=(0,-25,85))
    ref(box('CAM_USB_Connector',(0,-35,hz+16),(10,8,5)),'CAM USB调试口预留','metal','pitch')
    for n,loc,dim in [('CAM_Antenna_Clear',(0,-37,hz+33),(22,10,15)),('CAM_USB_Plug_Clear',(0,-58,hz+16),(16,30,10))]:
        done(box(n,loc,dim),n,'keepout','pitch','KEEP_OUT',False,role='keepout',note='ASSUMED placement; antenna component position/connector orientation require actual board drawing')
    for s,n in [(-1,'L'),(1,'R')]:
        done(ring('Mic_Duct_'+n,(s*18,-40.3,hz+27),2.4,1.2,19.5,'Y'),'板载麦克风独立短声道 '+n,'dark','pitch',note='Board microphone positions not yet verified; do not manufacture ducts until actual board registers are measured')

def head_joint():
    hz=D['head_z']; top=D['body_top_z']; hj=P['head_joint']; bz=D['yaw_bearing_construction_z']
    carrier=ring('Yaw_Carrier',(0,0,bz),20,16.3,8)
    union(carrier,ring('ledge',(0,0,bz-4.5),20,10.2,2))
    for x,y in [(20,15),(-20,15),(20,-15),(-20,-15)]:
        union(carrier,cyl('post',(x,y,(body_z_mm(29.0)+bz-5.5)/2),3,(bz-5.5)-body_z_mm(29.0)))
        union(carrier,beam('bearing_flange',(x*19/25,y*19/25,bz-4.5),(x,y,bz-4.5),2.5))
        boolean(carrier,cyl('pilot',(x,y,body_z_mm(31.0)),1.6,4))
    done(carrier,'Yaw 承重轴承座及立柱','frame',ex=(0,0,50)); contact('Yaw_Carrier','Load_Frame','Four support-post bottom planes at deck top')
    ref(ring('Yaw_Bearing',(0,0,bz),16,10,7),'Yaw 承重环轴承包络','metal')
    contact('Yaw_Bearing','Yaw_Carrier','Axial bearing support ledge; supplier tolerances/retention TBD')
    journal_bottom=min(bz-6,D['yaw_stop_construction_z']-1)
    rotor=ring('Yaw_Turntable',(0,0,(journal_bottom+top+2)/2),9.8,7.7,(top+2)-journal_bottom)
    union(rotor,ring('top_plate',(0,0,top+2),19,7.7,3))
    union(rotor,ring('drive_web',(0,0,yaw_servo_z_mm(28.5)),9.8,2.5,2))
    for angle in range(-70,71,5):
        rad=math.radians(180+angle); boolean(rotor,cyl('limited_yaw_cable_slot',(6.4*math.cos(rad),6.4*math.sin(rad),yaw_servo_z_mm(28.5)),1.7,4))
    done(rotor,'Yaw 转盘与空心轴','frame','yaw',ex=(0,0,75))
    servo=ref(box('Yaw_Servo',(0,0,body_z_mm(34.5)),INTERFACES['components']['yaw_servo']['body_xyz_mm']),'Yaw 舵机包络','blue'); servo['actuator_id']='head_yaw'
    mount=box('Yaw_Servo_Mount',(0,0,body_z_mm(21.5)),(30,19,2));
    for x in [-14,14]:
        union(mount,box('servo_side',(x,0,body_z_mm(33.0)),(3,19,21)))
        union(mount,box('frame_tab',(x*18/14,0,body_z_mm(30.0)),(12,19,2)))
    done(mount,'Yaw 舵机托座','frame'); contact('Yaw_Servo_Mount','Load_Frame','Mount base / deck top'); contact('Yaw_Servo','Yaw_Servo_Mount','Servo lower seat')
    ref(cyl('Yaw_Output',(0,0,yaw_servo_z_mm(28.5)),2.5,8),'Yaw 输出轴占位','metal','yaw'); contact('Yaw_Output','Yaw_Servo','Output shaft end'); contact('Yaw_Output','Yaw_Turntable','Output drive web; actual spline/coupler TBD')
    ref(ring('Yaw_Horn',(0,0,yaw_servo_z_mm(27.0)),5,2.5,1),'Yaw 舵盘/联轴器占位','metal','yaw')
    # Yoke: a yaw-fixed bridge, two rear struts, and paired load bearing housings.
    yoke=box('Pitch_Yoke',(0,-8,top+5.5),(24,12,4))
    for s in [-1,1]:
        pts=[(s*8,-10,top+5.5),(s*24,-10,hz-23),(s*39,-10,hz-8)]
        for a,b in zip(pts,pts[1:]): union(yoke,beam('yoke_arm',a,b,2.8))
        h=ring('trunnion_housing',(s*39,0,hz),8.5,6.25,4,'X'); union(h,beam('rear_brace',(s*39,-10,hz-8),(s*39,-6,hz-3),2.8)); union(yoke,h)
        ref(ring('Pitch_Bearing_'+('L' if s<0 else 'R'),(s*39,0,hz),6,2.5,4,'X'),'Pitch 两侧承重轴承','metal','yaw')
    boolean(yoke,cyl('body_fixed_wire_clear',(0,0,body_z_mm(79.0)),8,14))
    clip_z(yoke,top+3.5,500)
    done(yoke,'Pitch 双侧承重支架','frame','yaw',ex=(0,-20,95)); contact('Pitch_Yoke','Yaw_Turntable','Yoke base / rotor top face')
    ps=ref(box('Pitch_Servo',(-23,0,hz),INTERFACES['components']['pitch_servo']['body_xyz_mm']),'Pitch 舵机包络','blue','yaw'); ps['actuator_id']='head_pitch'
    # Separate removable saddle attached to yoke back rail; exact servo ears remain TBD.
    sm=box('Pitch_Servo_Mount',(-23,-8,hz),(28,3,24)); union(sm,box('shelf',(-23,0,hz-12.5),(28,17,3)))
    boolean(sm,clone(yoke,'yoke_relief'))
    done(sm,'Pitch 舵机安装托','frame','yaw',ex=(-20,-10,100)); contact('Pitch_Servo','Pitch_Servo_Mount','Servo lower seat and rear restraint')
    cradle=None
    for s,n in [(-1,'L'),(1,'R')]:
        cheek=ring('cheek',(s*44,0,hz),8,2.7,3,'X')
        union(cheek,beam('upright',(s*44,3,hz+6),(s*36,3,hz+35),2.0))
        if cradle is None: cradle=cheek
        else: union(cradle,cheek)
        ref(cyl('Pitch_Trunnion_'+n,(s*40.5,0,hz),2.49,11,'X'),'Pitch 承重短轴 '+n,'metal','pitch')
        contact('Pitch_Trunnion_'+n,'Pitch_Bearing_'+n,'Nominal journal/bearing contact; fits unselected')
    # Upper crossbar links both cheeks, kept behind the camera and away from its PCB.
    union(cradle,beam('crossbar',(-36,3,hz+35),(36,3,hz+35),2.5))
    intersect(cradle,sphere('cradle_inner_limit',(0,0,hz),D['head_radius']-2.8))
    cradle.name=PREFIX+'Pitch_Cradle'; done(cradle,'Pitch 随头旋转承架','frame','pitch',ex=(0,0,110))
    # Match separate optical supports to the actual rotating crossbar seat.
    camera_mount=bpy.data.objects[PREFIX+'Camera_Mount']; boolean(camera_mount,clone(cradle,'camera_saddle')); camera_mount.data.materials.append(MATS['frame'])
    optical_frame=bpy.data.objects[PREFIX+'Display_Frame']
    for sign in [-1,1]: union(optical_frame,beam('display_support',(sign*26,41,hz+4),(sign*26,3,hz+34.5),2))
    boolean(optical_frame,clone(cradle,'display_saddle')); boolean(optical_frame,cyl('pcb_extra_relief',(0,42,hz+P['display']['z_from_head_mm']),27.9,3.8,'Y')); optical_frame.data.materials.append(MATS['dark'])
    contact('Camera_Mount','Pitch_Cradle','Matching crossbar saddle; fastening details pending Stage B')
    contact('Display_Frame','Pitch_Cradle','Matching crossbar saddles; fastening details pending Stage B')
    contact('Pitch_Cradle','Head_Front','Two top lug seats, trial M2 inserts'); contact('Pitch_Cradle','Pitch_Trunnion_L','Bilateral shaft shoulder'); contact('Pitch_Cradle','Pitch_Trunnion_R','Bilateral shaft shoulder')
    ref(ring('Pitch_Horn',(-36,0,hz),5,2.5,1,'X'),'Pitch 舵盘 / 轴联接','metal','pitch')
    contact('Pitch_Horn','Pitch_Servo','Output end / torque coupling')
    # A concentric lower inner guard reduces exposed gimbal; relief cuts use the SAME swept optics.
    guard=sphere('Head_Lower_Guard',(0,0,hz),hj['guard_outer_radius_mm']); boolean(guard,sphere('inner',(0,0,hz),hj['guard_outer_radius_mm']-hj['guard_thickness_mm']))
    clip_z(guard,top+hj['guard_lower_z_from_body_top_mm'],hz+hj['guard_top_z_from_head_mm'])
    for pitch in range(-20,26,5):
        cutter=cyl('swept_display_clear',(0,45,hz+P['display']['z_from_head_mm']),31,15,'Y')
        tr=Matrix.Translation((0,0,hz))@Matrix.Rotation(math.radians(pitch),4,'X')@Matrix.Translation((0,0,-hz))
        cutter.matrix_world=tr@cutter.matrix_world; boolean(guard,cutter)
    for angle in [210,270,330]:
        u=Vector((math.cos(math.radians(angle)),math.sin(math.radians(angle)),0)); q=beam('guard_support',u*18+Vector((0,0,body_z_mm(77.0))),u*43+Vector((0,0,body_z_mm(77.0))),1.6); clip_z(q,body_z_mm(75.5),500); intersect(q,sphere('support_limit',(0,0,hz),hj['guard_outer_radius_mm'])); union(guard,q)
    done(guard,'同心下护罩（显示运动让位）',P['appearance']['head_guard_material'],'yaw',ex=(0,-25,90),note='Black light-control surface; 0.9 mm nominal radial shell clearance; extreme opening exposure still requires review')
    # Small stop flag and fixed blocks lie below body top; hard limits outside commanded range.
    flag=box('Yaw_Stop_Flag',(11,0,D['yaw_stop_construction_z']),(9,2,1)); done(flag,'Yaw 限位凸耳','frame','yaw')
    for a in [-76,76]:
        x=14*math.cos(math.radians(a)); y=14*math.sin(math.radians(a))
        q=box('Yaw_Stop_'+str(a),(x,y,D['yaw_stop_construction_z']),(3,3,3)); done(q,'Yaw 固定限位块','frame')
    # Pitch stops are separate blocks on the yoke, flagged as trial stop geometry.
    for a,n in [(-28,'Down'),(33,'Up')]:
        q=box('Pitch_Stop_'+n,(39,-10*math.cos(math.radians(a)),hz-10*math.sin(math.radians(a))),(4,2,2)); union(q,beam('stop_anchor',(39,-7.5*math.cos(math.radians(a)),hz-7.5*math.sin(math.radians(a))),(39,-10*math.cos(math.radians(a)),hz-10*math.sin(math.radians(a))),1.1)); union(yoke,q); yoke.data.materials.append(MATS['frame'])
    # Flexible service loops are routing envelopes, not claimed cable mechanics.
    for name,loc,major,minor,axis,grp in [('Yaw_Service_Loop',(0,0,yaw_servo_z_mm(26.0)),hj.get('yaw_service_loop_radius_mm',18),1.2,'Z','yaw'),('Pitch_Service_Loop',(29,0,hz),7,1.2,'X','pitch')]:
        bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=10,location=loc,major_radius=major,minor_radius=minor)
        o=raw(bpy.context.object,name)
        if axis=='X': o.rotation_euler.y=math.pi/2; bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        done(o,'头部线束服务环 '+name,'copper',grp,'PLACEHOLDER',False,note='Conservative routing allocation; dynamic cable deformation, bend fatigue and endpoints NOT_TESTED',role='routing')
    for name,loc in [('Yaw_Cable_Clip',(-hj.get('yaw_cable_clip_abs_x_mm',18),0,yaw_servo_z_mm(26.0))),('Pitch_Cable_Clip',(29,-7,hz))]:
        o=ring(name,loc,3,1.8,4,'Y' if 'Yaw' in name else 'Z'); done(o,'线束应力释放夹','frame','yaw' if 'Pitch' in name else 'body')

def wheel_and_drive():
    dr=P['drive'];wz=D['wheel_z'];wx=D['wheel_x']
    for sign,n in [(-1,'L'),(1,'R')]:
        grp='wheel_'+n
        t=ring('Tire_'+n,(sign*wx,0,wz),D['wheel_radius'],D['wheel_radius']-10.5,P['wheel_width_mm'],'X')
        mod=t.modifiers.new('Soft tire edge','BEVEL');mod.width=1.6;mod.segments=4;mod.limit_method='ANGLE';mod.angle_limit=.5;apply(t,mod)
        ref(t,'软轮胎 '+n,'tire',grp,(sign*45,0,0),note=f'{P["wheel_diameter_mm"]:g}x{P["wheel_width_mm"]:g} soft tire requirement; no selected supplier/TPU traction certification')
        hub=ring('Wheel_Hub_'+n,(sign*wx,0,wz),D['wheel_radius']-10.5,2.2,15,'X');done(hub,'轮毂 '+n,'frame',grp,ex=(sign*33,0,0))
        cap=cyl('Wheel_Cap_'+n,(sign*(wx+9.5),0,wz),D['wheel_radius']-10.7,1.4,'X');done(cap,'纯色轮盖 '+n,'shell',grp,ex=(sign*55,0,0))
        axle=ref(cyl('Wheel_Axle_'+n,(sign*50,0,wz),1.99,42,'X'),'独立4mm短轴 '+n,'metal',grp)
        for x in dr['bearing_abs_x_mm']:
            ref(ring('Wheel_Bearing_'+n+'_'+str(x),(sign*x,0,wz),5,2,4,'X'),'独立承重轴承 '+n,'metal')
            contact('Wheel_Axle_'+n,'Wheel_Bearing_'+n+'_'+str(x),'4mm trial shaft journal, exact fit/retention unqualified')
        cx=sign*dr['motor_center_abs_x_mm'];zc=wz+dr['body_center_z_from_axle_mm']
        motor=box('Drive_Motor_'+n,(cx,0,zc),(20,20,34),.4)
        # The actual S288 drawing has a lower output axis and six 1.7mm self-tapping pilot holes.
        for yy in [-8,8]:
            for zz in [wz-7.5,wz+22.5]:boolean(motor,cyl('vendor_pilot',(sign*23.4,yy,zz),.85,1.2,'X',16))
        mot=ref(motor,'S288 本体 '+n,'metal',ex=(sign*20,-25,0),note='VENDOR_DOCUMENTED body20x20x34, outputaxis9.5 from end; cutouts conservative. Variant/holes still require hardware review');mot['actuator_id']='wheel_'+n;mot['documented_mass_g']=19.5
        for xx,tag in [(25.5,'Outer'),(2.5,'Inner')]:ref(cyl('S288_Output_'+n+'_'+tag,(sign*xx,0,wz),7,3,'X'),'S288输出端 '+n+tag,'metal',grp,note='Vendor14 diameter x3 projection; 6x1.7 self-tap pilot pattern on10.5 circle documented, not modeled; adapter/thread engagement and purchased revision pending')
        cp=ring('Wheel_Coupler_'+n,(sign*28,0,wz),7,2.2,2,'X');done(cp,'S288转接盘 '+n,'frame',grp,note='Trial blank; output pilot circle documented, but do not freeze adapter holes/clocking/fasteners before revision and thread engagement review.')
        contact('Wheel_Coupler_'+n,'S288_Output_'+n+'_Outer','Flat output-face interface; adapter fasteners/thread engagement pending; independent axle bearings carry wheel load')
        mount=box('Motor_Mount_'+n,(cx,0,wz+27),(25,24,2.8))
        for yy in [-11.5,11.5]:union(mount,box('motor_side',(cx,yy,wz+8),(25,2,36)))
        # Carry into the rear chassis spine rather than a cosmetic shell wall.
        union(mount,beam('motor_rear_link',(cx,-12,wz+27),(cx,-42,wz+27),2.2));union(mount,beam('motor_frame_link',(cx,-42,wz+27),(cx,-42,130),2.2))
        done(mount,'S288 可拆鞍座 '+n,'frame',ex=(sign*15,-25,0))

def frame_and_electronics():
    hz=D['head_z'];l=P['layout'];dz=l['deck_z_mm'];dr=P['drive'];wz=D['wheel_z']
    frame=cyl('Load_Frame',(0,0,dz),70,4);intersect(frame,box('deck_clip',(0,0,dz),(116,100,8)))
    boolean(frame,box('yaw_servo_pass',(4,0,dz),(38,22,12)))
    for sign in [-1,1]:
        for x in dr['bearing_abs_x_mm']:
            a=ring('carrier',(sign*x,0,wz),7,5.25,4.8,'X')
            union(a,beam('rear_axle_arm',(sign*x,0,wz+5),(sign*x,-42,77),2.4))
            union(a,beam('rear_spine',(sign*x,-42,77),(sign*x,-42,dz-2),2.4))
            boolean(a,cyl('bearing_clear',(sign*x,0,wz),5.25,8,'X'));union(frame,a)
    for x,y in P['shell_service']['frame_mount_xy_mm']:boolean(frame,cyl('frame_screw',(x,y,dz),1.7,10))
    done(frame,'承重框架 / 双轮轴承座 / 后脊柱','frame',ex=(0,0,25))
    bc=l['battery_center_mm'];ref(box('Battery',bc,l['battery_max_xyz_mm']),'3S电池限制包络80x65x30','battery',note='ASSUMED pack allocation; no real product or chemistry/thickness verified')
    tray=box('Battery_Tray',(0,0,83),(85,70,3))
    for s in [-1,1]:union(tray,box('battery_rail',(s*41.5,0,88),(2,70,10)))
    for yy in [-29,29]:boolean(tray,box('strap',(0,yy,83),(20,2.4,8)))
    for i,(xx,yy) in enumerate([(-25,-36),(25,-36),(-25,36),(25,36)]):
        union(tray,box('battery_tab',(xx,yy,83),(10,8,3)));boolean(tray,cyl('slot',(xx,yy,83),1.7,8))
        ref(cyl('Battery_Hanger_'+str(i),(xx,yy,106.5),1.5,44),'电池吊杆 '+str(i),'metal')
    done(tray,'中置可调电池托架','frame',ex=(0,0,-30));contact('Battery_Tray','Battery','0.5mm bottom padding reserve; strap/connector keepout needs real pack')
    loc=l['mcu_centers_mm'][0];ref(box('MCU_Motion',loc,l['mcu_max_xyz_mm']),'STM32F413载板限制框70x50','pcb')
    m=box('MCU_Mount_Motion',(loc[0],loc[1],135.5),(74,37,2))
    for x,y in [(-32,-42),(32,-42),(-32,-22),(32,-22)]:union(m,cyl('board_post',(x,y,134.25),1.8,.5))
    done(m,'运动主板支架','frame')
    il=l['imu_center_mm'];imu=ref(box('Body_IMU',il,l['imu_max_xyz_mm']),'ICM42688P SPI模块包络','pcb')
    imu=bpy.data.objects[PREFIX+'Body_IMU'];imu.rotation_euler.z=math.radians(l.get('imu_rotation_z_deg',0));bpy.context.view_layer.update();SOLIDS.pop(imu.name,None)
    im=box('IMU_Mount',(il[0],il[1],134.5),(24,20,1));done(im,'刚性IMU座 +XYZ','frame')
    for ax,vec in [('X',(12,0,0)),('Y',(0,12,0)),('Z',(0,0,12))]:done(beam('IMU_Axis_'+ax,Vector(il)+Vector((0,0,4)),Vector(il)+Vector((0,0,4))+Matrix.Rotation(math.radians(l.get('imu_rotation_z_deg',0)),3,'Z')@Vector(vec),.5),'IMU '+ax,'metal','body','ANNOTATIONS',False,role='annotation')
    ref(box('Power_Module',(0,-34,body_z_mm(54.5)),l['power_allocation_xyz_mm']),'3S保护/6V/5V电源限制包络','pcb')
    pm=box('Power_Module_Mount',(0,-34,153.5),(48,20,2))
    for sign in [-1,1]:
        union(pm,beam('power_side',(sign*23,-34,153.5),(sign*39,-34,153.5),1.8));union(pm,cyl('power_post',(sign*39,-34,143.75),1.8,19.5))
    done(pm,'后侧电源板架','frame')
    ref(box('USB_Charge',(0,-58,P['detail_fit']['ports']['module_z_mm']),(28,20,10)),'USB-C 3S充电模块限制包络','pcb')
    mount=box('USB_Charge_Mount',(0,-58,P['detail_fit']['ports']['module_z_mm']-7),(32,22,2));union(mount,beam('usb_support',(31,-49,body_z_mm(1)),(31,-49,130),1.8));done(mount,'USB充电模块支架','frame')
    sp=Vector(l['speaker_center_mm'])
    ref(cyl('Speaker',sp,18,8,'Y'),'4ohm3W扬声器限制包络','dark')
    cup=ring('Speaker_Mount',sp,20.4,18.4,14,'Y');union(cup,cyl('cup_back',sp+Vector((0,-7.6,0)),20.4,1.2,'Y'))
    for side in [-1,1]:union(cup,beam('cup_anchor',sp+Vector((side*18,-6,-4.3)),sp+Vector((side*23,-5,-4.3)),2.2))
    done(cup,'前置独立可拆声腔','frame',note='Rear cup separated from head microphones; acoustic seal/volume/tuning untested')
    usb=box('USB_Receptacle',(0,-76.5,P['detail_fit']['ports']['usb_z_mm']),(10,6,4),.5);boolean(usb,box('usb_open',(0,-79,P['detail_fit']['ports']['usb_z_mm']),(8.4,5,2.6),.4));ref(usb,'USB-C插座','metal')
    ref(box('Power_Switch',(0,-74.5,P['detail_fit']['ports']['switch_z_mm']),(10,6,6)),'物理电源/禁驱开关包络','dark')
    ref(radial_button_cylinder('Function_Button',3.7,10,6),'实体功能按钮内置模块','dark');done(radial_button_cylinder('Button_Cap',3.9,1,.1),'功能按钮帽','shell')
    for n,loc,dim in [('USB_Plug_Clear',(0,-100,P['detail_fit']['ports']['usb_z_mm']),(16,34,10)),('Switch_Finger_Clear',(0,-94,P['detail_fit']['ports']['switch_z_mm']),(22,30,18))]:done(box(n,loc,dim),n,'keepout','body','KEEP_OUT',False,role='keepout')
    camera_loc=P['camera']['body_center_from_head_mm']
    paths=[('Head_Trunk',[(-42,25,137),(-32,10,159),(-P['head_joint'].get('yaw_cable_clip_abs_x_mm',18),0,153)],'body'),('Yaw_Head_Lead',yaw_head_lead_points(),'yaw'),('Screen_Lead',[(0,35,hz-24),(15,22,hz-15),(15,-10,hz-11),(22,-15,hz-9)],'pitch'),('Camera_Lead',[(6,camera_loc[1]-2,hz+camera_loc[2]+1),(23,23,hz+31),(24,-16,hz+24)],'pitch'),('Speaker_Lead',[tuple(sp+Vector((0,5,5))),(-24,36,body_z_mm(48)),(-36,24,body_z_mm(45))],'body')]
    for n,pts,g in paths:
        q=None
        for a,b in zip(pts,pts[1:]):
            t=beam('wire',a,b,1.2)
            if q is None:q=t
            else:union(q,t)
        q.name=PREFIX+n;done(q,'线束预留 '+n,'copper',g,'PLACEHOLDER',False,note='Finite routing allocation, connector orientations/radii unverified; physical cable sweep NOT_TESTED',role='routing')

def fasteners_and_coupons():
    sx=seam_mount_x();sy=P['shell_service']['seam_mount_abs_y_mm']
    frame_bottom=P['layout']['deck_z_mm']-P['layout']['deck_thickness_mm']/2
    frame_top=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    for family,coords,z0,z1,r in [('Shell',[(sx,sy),(-sx,sy),(sx,-sy),(-sx,-sy)],body_z_mm(-11),body_z_mm(5),1.5),('Frame',P['shell_service']['frame_mount_xy_mm'],frame_bottom,frame_top+4,1.5)]:
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
    relief=body_profile('body_relief',-1.8); relief.location.z+=lift; boolean(base,relief)
    done(base,'独立停放 / 刷机 / 有线充电托架','frame','dock','DOCK',True,ex=(0,-150,0),note='Separate maintenance-only accessory. Lift robot 8 mm, disable wheel drive. No motors/charging contacts; does not prove free-standing stability')
    for i,(x,y) in enumerate(d['contact_xy_mm']):
        seat=bz-math.sqrt(ro*ro-x*x-y*y); pad=box('Dock_Pad_'+str(i),(x,y,seat-.5),(13,13,5))
        q=body_profile('body_surface');q.location.z+=lift;boolean(pad,q);q=body_profile('padouter',-1.8);q.location.z+=lift;intersect(pad,q)
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
    for name,loc,dim in [('Body_Top_Plane',(0,0,D['body_top_z']),(170,170,.1)),('Left_Cut_Plane',(-P['body_side_cut_x_mm'],0,D['body_z']),(.1,170,160)),('Right_Cut_Plane',(P['body_side_cut_x_mm'],0,D['body_z']),(.1,170,160)),('Ground_Plane',(0,0,0),(230,230,.1))]:
        o=box(name,loc,dim); move_collection(o,'DATUMS'); o['role']='construction'
    for name,loc,axis in [('Yaw_Axis',(0,0,D['head_z']),'Z'),('Pitch_Axis',(0,0,D['head_z']),'X')]:
        o=cyl(name,loc,.3,110,axis); move_collection(o,'DATUMS'); o['role']='construction'
    yaw['allowed_yaw_deg']=[-60,60]; pitch['allowed_pitch_deg']=[-20,25]
    yaw['hint']=f'Edit rotation Z in degrees. Physical bearing z={D["yaw_bearing_z"]} mm; geometric axis passes through head center.'
    pitch['hint']='Edit local rotation X in degrees; positive lifts head. Camera and display parented here.'

def studio():
    sc=bpy.context.scene; sc.world=bpy.data.worlds.get(PREFIX+'World') or bpy.data.worlds.new(PREFIX+'World'); mark(sc.world); sc.world.use_nodes=True; next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.18,.2,.24,1)
    next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.45
    for name,loc,power,size in [('Key',(-350,250,380),1900000,220),('Fill',(300,180,340),900000,250),('Rim',(80,-320,440),1500000,230)]:
        data=mark(bpy.data.lights.new(PREFIX+name,'AREA')); data.energy=power; data.shape='DISK'; data.size=size
        o=mark(bpy.data.objects.new(PREFIX+name,data)); COLS['CAMERAS_LIGHTS'].objects.link(o); o.location=loc; o.rotation_euler=(Vector((0,0,130))-o.location).to_track_quat('-Z','Y').to_euler()
    ground=box('Studio_Ground',(0,0,-1.6),(3000,3000,3)); done(ground,'渲染地面','ground','studio','CAMERAS_LIGHTS',False,role='studio')
    sc.view_settings.view_transform='AgX'; sc.render.image_settings.file_format='PNG'; sc.render.film_transparent=False

def materials():
    for name,col in [('shell',(.83,.81,.75)),('frame',(.20,.27,.30)),('tire',(.042,.046,.052)),('metal',(.48,.52,.56)),('pcb',(.025,.19,.13)),('battery',(.11,.13,.16)),('dark',(.003,.004,.006)),('blue',(.055,.16,.35)),('copper',(.6,.22,.055)),('belt',(.07,.07,.07)),('coupon',(.48,.64,.67)),('ground',(.20,.23,.28)),('keepout',(.7,.22,.1))]: material(name,col,metallic=.7 if name=='metal' else 0,roughness=.72 if name in ['shell','tire'] else .45)
    material('glass',(.96,.98,1),roughness=.045,transmission=1); material('eye',(.07,.83,.92),roughness=.4,emission=2)
    material('unknown',(.7,.25,.035),roughness=.7)
    material('lens',(.004,.012,.019),metallic=.15,roughness=.12)
    camera_glass=material('camera_glass',(.13,.16,.18),roughness=.12,transmission=1)
    next(n for n in camera_glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Specular IOR Level'].default_value=.15

def v12_joint_details():
    hz=D['head_z']
    # SCS0009 drawing separates body, ears and raised output; current bought variant remains unconfirmed.
    for name,group in [('Yaw_Servo','body'),('Pitch_Servo','yaw')]:
        old=bpy.data.objects[PREFIX+name];bpy.data.objects.remove(old,do_unlink=True);SOLIDS.pop(PREFIX+name,None)
        isyaw=name=='Yaw_Servo';base=P['head_joint'].get('yaw_servo_base_z_mm',127.0)
        def trans(pt):
            x,y,z=pt
            return (x,y,base+z) if isyaw else (-10.375-z,y,hz+x)
        o=box(name,trans((5.95,0,10.725)),(23.3,12.1,21.45) if isyaw else (21.45,12.1,23.3))
        union(o,cyl('scs_top',trans((0,0,23.35)),6.05,3.8,'Z' if isyaw else 'X'))
        for xx in [-8.55,19.95]:
            ear=box('ear',trans((xx,0,19.15)),(4,12.1,1.5) if isyaw else (1.5,12.1,4));boolean(ear,cyl('ear_hole',trans((xx,0,19.15)),1,4,'Z' if isyaw else 'X',24));union(o,ear)
        m=ref(o,'SCS0009 '+('Yaw' if isyaw else 'Pitch')+' 本体/安装耳','blue',group,note='2020 A/0 manufacturer drawing.23.3 drawing vs23.2 table; actual revision and mounting screws must be confirmed');m['actuator_id']='head_yaw' if isyaw else 'head_pitch';m['documented_mass_g']=13.2
        if not isyaw:
            sm=bpy.data.objects[PREFIX+'Pitch_Servo_Mount'];boolean(sm,clone(o,'scs_clear'));sm.data.materials.append(MATS['frame'])
    # Remove obsolete generic yaw output, replace with the actual documented3.95 diameter spline allocation.
    old=bpy.data.objects[PREFIX+'Yaw_Output'];bpy.data.objects.remove(old,do_unlink=True);SOLIDS.pop(PREFIX+'Yaw_Output',None)
    ref(cyl('Yaw_Output',(0,0,yaw_servo_z_mm(26.85)),1.975,3.2),'SCS0009 20T 输出端包络','metal','yaw',note='20T OD3.95; teeth not modeled, actual mating horn not released')
    h=bpy.data.objects[PREFIX+'Yaw_Horn'];h.location.z-=1.5
    # Declare unknown fastener routes as envelopes; these are not finalized manufacturer holes.
    for name,loc,axis in [('Yaw_Lock_Screw',(0,0,yaw_servo_z_mm(27.1)),'Z'),('Pitch_Lock_Screw',(-37,0,hz),'X')]:ref(cyl(name,loc,1,4,axis),'舵盘M2中心锁紧螺丝包络','metal','yaw' if axis=='Z' else 'pitch')
    # Printed saddles relieved against the declared part, never shrink vendor envelopes.
    for target,cutter in [('CAM_Mainboard_Mount','CAM_USB_Connector'),('CAM_Mainboard_Mount','Mic_Duct_L'),('CAM_Mainboard_Mount','Mic_Duct_R'),('CAM_Mainboard_Mount','Pitch_Cradle'),('Display_Frame','Camera_PCB')]:
        a=bpy.data.objects[PREFIX+target];boolean(a,clone(bpy.data.objects[PREFIX+cutter],'fit_relief'))
    for n in ['Mic_Duct_L','Mic_Duct_R']:
        a=bpy.data.objects[PREFIX+n];intersect(a,sphere('inner_mic_limit',(0,0,hz),57.2))
    rotor=bpy.data.objects[PREFIX+'Yaw_Turntable'];g=bpy.data.objects[PREFIX+'Head_Lower_Guard'];boolean(g,clone(rotor,'rotor_clearance'))
    old=bpy.data.objects[PREFIX+'Yaw_Servo_Mount'];bpy.data.objects.remove(old,do_unlink=True);SOLIDS.pop(PREFIX+'Yaw_Servo_Mount',None)
    mount=box('Yaw_Servo_Mount',(6,0,125.5),(29,18,2))
    for yy in [-8,8]:
        union(mount,box('yaw_side',(6,yy,134),(29,2,15)))
        union(mount,box('yaw_frame_foot',(3,yy*1.5,135),(22,8,2)))
    done(mount,'SCS0009 Yaw托座','frame')
    # Smooth representations of threaded holes are used only for interference checking.
    for n in ['Yaw_Servo','Yaw_Output']:
        boolean(bpy.data.objects[PREFIX+n],cyl('lock_hole',(0,0,yaw_servo_z_mm(27)),1.05,7))
    h=bpy.data.objects[PREFIX+'Yaw_Horn'];h.location.z+=yaw_servo_z_mm(27)-sum(bounds(h)[2])/2;SOLIDS.pop(h.name,None)
    tr=bpy.data.objects[PREFIX+'Pitch_Trunnion_L'];clip=box('shorten',(-14.45,0,hz),(48.9,12,12));boolean(tr,clip)
    horn=bpy.data.objects[PREFIX+'Pitch_Horn'];horn.location.x+=-36.2-sum(bounds(horn)[0])/2;SOLIDS.pop(horn.name,None)
    out=ref(cyl('Pitch_Output',(-37.225,0,hz),1.975,3.2,'X'),'SCS0009 Pitch输出20T包络','metal','pitch')
    for n in ['Pitch_Servo','Pitch_Output','Pitch_Trunnion_L']:
        boolean(bpy.data.objects[PREFIX+n],cyl('lock_hole',(-37,0,hz),1.05,7,'X'))
    for n in ['Speaker_Mount','Speaker']:
        frame=bpy.data.objects[PREFIX+'Load_Frame'];boolean(frame,clone(bpy.data.objects[PREFIX+n],'sound_service_cut'))
    collar=ring('Body_Top_Shroud',(0,0,D['yaw_bearing_construction_z']+6),35.8,P.get('belly_relayout',{}).get('shroud_cable_clear_radius_mm',20.5),1.6)
    done(collar,'隐藏关节下方遮光环','dark',note='Fixed annulus below the full head sphere; no third support, motion sampled')
    # Rear head mounts connect to the same pitch cradle, leaving CAM board clear.
    c=bpy.data.objects[PREFIX+'Pitch_Cradle']
    for s in [-1,1]:union(c,beam('head_lug_rise',(s*41,3,hz+17),(s*48,3,hz+24),2))
    boolean(c,clone(bpy.data.objects[PREFIX+'Head_Front'],'lug_seat'));c.data.materials.append(MATS['frame'])
    frame=bpy.data.objects[PREFIX+'Load_Frame'];boolean(frame,box('front_service_notch',(0,50,132),(44,28,8)))

from head_servo_detail import apply_head_servo_detail
from waveshare_detail import apply_waveshare_detail
from assembly_completion import apply_assembly_completion
from readiness_completion import apply_readiness_completion
from prearrival_completion import apply_prearrival_completion,apply_print_material
from display_frame_simplification import apply_display_frame_simplification
from interface_completion import apply_interface_completion

def main():
    CONTACTS.clear(); start=time.time(); timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(); scene=setup_scene();materials()
    for fn in [shells,optics,head_joint,wheel_and_drive,frame_and_electronics,fasteners_and_coupons,v12_joint_details,apply_purchased_geometry,apply_structural_simplification,apply_monocoque_structure,apply_simple_modules,apply_belly_relayout,apply_detail_fit,apply_layout_cleanup,apply_part_consolidation,apply_head_cleanup,apply_wheel_interfaces,apply_crossbolt_joint,apply_native_electronics,apply_drive_cleanup,apply_head_servo_detail,apply_waveshare_detail,apply_assembly_completion,apply_readiness_completion,apply_prearrival_completion,dock,controls_datums,studio]:
        print('BUILD '+fn.__name__,flush=True); fn()
    
    # Approved late-stage local revision. Earlier phases remain reproducible;
    # the current assembly always derives from the one geometry configuration.
    apply_print_material()
    for o in parts(True):
        clean(o)
        if o.name.removeprefix(PREFIX) in ['Body_Upper','Body_Lower']:
            for f in o.data.polygons:
                if abs(f.normal.x)>.999: f.use_smooth=False
    # Rebuild the accepted connections from the cleaned historical source.
    # Its closed manifold triangles must not be subjected to a second
    # proximity weld, which can collapse nearby bore/plane intersections.
    apply_display_frame_simplification()
    apply_interface_completion()
    from assembly_issue_fixes import apply_assembly_issue_fixes
    apply_assembly_issue_fixes()
    from head_axial_retention import apply_head_axial_retention
    apply_head_axial_retention()
    from p5r7_adoption import apply_p5r7_adoption
    apply_p5r7_adoption()
    from camera_cam_completion import apply_camera_cam_completion
    apply_camera_cam_completion()
    from neck_capacity import apply_neck_capacity
    apply_neck_capacity()
    from body_shell_split import apply_body_shell_split
    apply_body_shell_split()
    from reaction_nut_alignment import apply_reaction_nut_alignment
    apply_reaction_nut_alignment()
    for o in parts():
        if o.get('actuator_id'):
            move_collection(o,'PURCHASED_REFERENCE');o['category']='PURCHASED_REFERENCE';o['data_status']='ASSUMED';o['documented_fields']=o.get('documented_fields','Manufacturer nominal body/output dimensions and mass; full simplified assembly geometry still assumed, no manufacturing qualification')
    from head_surface_display import apply_head_surface_display
    apply_head_surface_display()
    assembled(); write_bom(); save_json(ROOT/'reports/derived.json',D); save_json(ROOT/'reports/intended_contacts.json',CONTACTS)
    # Derived instance coordinates are a build result, never an independently editable dimension source.
    instances={o.name.removeprefix(PREFIX):{'frame_id':'assembly_ground','timestamp_utc':timestamp,'category':o.get('category'),'data_status':o.get('data_status'),'model_fidelity':o.get('model_fidelity','DESIGN_GEOMETRY'),'measured_unit':False,'group':o.get('group'),'bounds_xyz_mm':bounds(o),'origin_world_mm':list(o.matrix_world.translation)} for o in parts()}
    save_json(ROOT/'reports/assembly_instances.json',instances)
    save_json(ROOT/'reports/build_manifest.json',{'blender':bpy.app.version_string,'blender_hash':bpy.app.build_hash.decode(),'python':platform.python_version(),'manifold3d':'3.5.3','owner':OWNER,'objects':len([o for o in scene.objects if o.get('mori_owner')==OWNER]),'parts':len(parts()),'actuators':[o.name for o in parts() if o.get('actuator_id')],'elapsed_s':round(time.time()-start,1),'input_sha256':{str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [PROJECT/'config/geometry.json',PROJECT/'contracts/mechanical_interfaces.json',PROJECT/'MORI_SPEC_V1_2.md',PROJECT/'01_CODEX_MECHANICAL.md',ROOT/'scripts/build.py',ROOT/'scripts/common.py',ROOT/'scripts/purchased_geometry.py',ROOT/'scripts/structural_simplification.py',ROOT/'scripts/monocoque_structure.py',ROOT/'scripts/simple_modules.py',ROOT/'scripts/belly_relayout.py',ROOT/'scripts/detail_fit.py',ROOT/'scripts/layout_cleanup.py',ROOT/'scripts/part_consolidation.py',ROOT/'scripts/head_cleanup.py',ROOT/'scripts/head_surface_display.py',ROOT/'scripts/head_servo_detail.py',PROJECT/P['head_servo_detail']['source'],ROOT/'scripts/drive_cleanup.py',ROOT/'scripts/wheel_interfaces.py',ROOT/'scripts/yaw_bridge_mount.py',ROOT/'scripts/native_electronics.py',ROOT/'scripts/waveshare_detail.py',ROOT/'scripts/cam_fpc_entries.py',PROJECT/P['waveshare_detail']['entry_correction']['direction_receipt'],ROOT/'scripts/assembly_completion.py',ROOT/'scripts/readiness_completion.py',ROOT/'scripts/prearrival_completion.py',ROOT/'scripts/display_frame_simplification.py',ROOT/'scripts/interface_completion.py',ROOT/'scripts/assembly_issue_fixes.py',ROOT/'scripts/head_axial_retention.py',ROOT/'scripts/p5r7_adoption.py',ROOT/'scripts/camera_cam_completion.py',ROOT/'scripts/neck_capacity.py',ROOT/'scripts/body_shell_split.py',ROOT/'scripts/reaction_nut_alignment.py',ROOT/'scripts/neck_profile_geometry.py',ROOT/'scripts/neck_curve_geometry.py',PROJECT/P['p5r7_adoption']['handoff'],PROJECT/P['p5r7_adoption']['addendum'],PROJECT/P['readiness_completion']['lcd']['thread_validation']['source_file'],PROJECT/P['readiness_completion']['lcd']['thread_validation']['source_manifest'],PROJECT/P['waveshare_detail']['source_manifest'],ROOT/'scripts/supplement_populated_pcbs.py',PROJECT/P['native_electronics']['inventory'],*[PROJECT/v['mesh'] for v in P['native_electronics']['boards'].values()],*[PROJECT/v['mesh'] for v in P['native_electronics']['modules'].values()],ROOT/'scripts/power_board_mount.py',ROOT/'scripts/battery_tray_geometry.py',ROOT/'scripts/microphone_geometry.py',ROOT/'scripts/speaker_geometry.py',ROOT/'scripts/yaw_stops.py',PROJECT/P['layout_cleanup']['power_bay']['local_mount']['native_handoff'],ROOT/'scripts/optics_mount.py',PROJECT/P['detail_fit']['speaker']['source'],PROJECT/P['detail_fit']['speaker'].get('spec_source',P['detail_fit']['speaker']['source']),PROJECT/P['detail_fit']['weact_mesh'],PROJECT/P['display']['vendor_mesh_source'],PROJECT/P['layout_cleanup']['imu']['native_mesh'],PROJECT/P['layout_cleanup']['motion_carrier']['native_mesh']]+([PROJECT/P['structure']['comparison_baseline']['report']] if P.get('structure',{}).get('comparison_baseline') else [])+([PROJECT/'contracts/components.json'] if (PROJECT/'contracts/components.json').exists() else [])}})
    # Explicit position / extrinsic convention for later calibration.
    save_json(ROOT/'reports/camera_kinematics.json',{'status':'ASSUMED','units':'mm','frame_id':'body_axle','timestamp_utc':timestamp,'head_center_in_body_axle_mm':[0,0,D['head_z']-D['wheel_z']],'head_center_in_assembly_ground_mm':[0,0,D['head_z']],'nominal_T_body_axle_camera_mm':[[1,0,0,0],[0,0,1,P['camera']['pupil_from_head_mm'][1]],[0,-1,0,D['head_z']-D['wheel_z']+P['camera']['pupil_from_head_mm'][2]],[0,0,0,1]],'yaw_axis_body':[0,0,1],'pitch_axis_yaw':[1,0,0],'pupil_in_pitch':P['camera']['pupil_from_head_mm'],'camera_CV_axes_in_pitch':{'x_right':[1,0,0],'y_image_down':[0,0,-1],'z_optical':[0,1,0]},'transform':'T_body_axle_camera = T(0,0,head_z-wheel_radius) Rz(yaw_rad) Rx(pitch_rad) T(pupil) R_CV; T_world_camera = T_world_body_axle * T_body_axle_camera','angle_feedback':'estimated unless measured joint feedback is added','timestamp_requirement':'Frame and monotonic capture timestamp required for observations and joint estimates','calibration':'Intrinsics, distortion, window refraction, servo zero/backlash and actual extrinsics NOT_TESTED'})
    kpath=ROOT/'reports/camera_kinematics.json';kin=json.loads(kpath.read_text());ang=P['head_joint'].get('default_pitch_deg',0)
    cv=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
    extr=Matrix.Translation((0,0,D['head_z']-D['wheel_z']))@Matrix.Rotation(math.radians(ang),4,'X')@Matrix.Translation(camera_pupil()-Vector((0,0,D['head_z'])))@cv
    extr=Matrix.Translation((0,0,D['head_z']-D['wheel_z']))@Matrix.Rotation(math.radians(ang),4,'X')@Matrix.Translation(camera_pupil()-Vector((0,0,D['head_z'])))@camera_transform().to_3x3().to_4x4()@cv
    kin['pupil_in_pitch']=list(camera_pupil()-Vector((0,0,D['head_z'])));kin['nominal_T_body_axle_camera_mm']=[list(row) for row in extr];kin['camera_CV_axes_in_pitch']={k:list(camera_transform().to_3x3()@Vector(v)) for k,v in kin['camera_CV_axes_in_pitch'].items()};kin['transform']='T(0,0,head_z-wheel_radius) Rz(yaw) Rx(pitch) T(pupil) Rx(camera_mount_pitch) R_CV';kin['camera_mount_pitch_deg']=P.get('layout_cleanup',{}).get('camera_mount_pitch_deg',0)
    kin.update(default_head_pitch_deg=ang,default_T_body_axle_camera_mm=[list(row) for row in extr],angle_limits_convention='Absolute mechanical zero limits; default pitch is not an added offset');save_json(kpath,kin)
    for n in ['Face_Protector','Camera_Window']:
        if bpy.data.objects.get(PREFIX+n):bpy.data.objects[PREFIX+n].display_type='WIRE'
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.overlay.show_relationship_lines=False; area.spaces.active.overlay.show_extras=False; area.spaces.active.shading.color_type='MATERIAL'; area.spaces.active.region_3d.view_distance=420; area.spaces.active.region_3d.view_location=(0,0,130); area.spaces.active.clip_end=10000; area.spaces.active.region_3d.view_rotation=Vector((380,500,200)).to_track_quat('Z','Y'); area.spaces.active.region_3d.view_perspective='ORTHO'
    pose(0,P['head_joint'].get('default_pitch_deg',0)); bpy.context.view_layer.update(); bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'mori_v1_2.blend'))
    print('BUILD_COMPLETE',flush=True)
if __name__=='__main__': main()
