"""Run: Blender --background --python scripts/build.py
Regenerates only tagged MORI objects; editable solids, datums, pivots, animation.
"""
import sys, math, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
C=P['details_mm']

def body_outer(name):
    o=sphere(name,(0,0,D['body_z']),D['body_radius'])
    intersect(o,box('body_clip',(0,0,D['body_top_z']-250),(2*P['body_side_cut_x_mm'],1000,500)))
    return o

def head_outer(name):
    o=sphere(name,(0,0,D['head_z']),D['head_radius']); clip_z(o,D['head_bottom_z'],500); return o

def holes(o,coords,r,z0,z1):
    for x,y in coords: boolean(o,cyl('hole',(x,y,(z0+z1)/2),r,z1-z0))

def make_body():
    t=P['shell_thickness_mm']; st=P['structure']; f=P['fasteners_assumed']
    outer=body_outer('Body_mother_clipped')
    inner=sphere('cavity',(0,0,D['body_z']),D['body_radius']-t)
    intersect(inner,box('inner_clip',(0,0,D['body_top_z']-t-250),(2*(P['body_side_cut_x_mm']-t),1000,500)))
    shell=clone(outer,'Body_shell'); boolean(shell,inner)
    # Caps remain real 2.4 mm solids. Top opening and axle relief are actual holes.
    boolean(shell,cyl('head_open',(0,0,D['body_top_z']),P['body_top_opening_diameter_mm']/2,22))
    boolean(shell,cyl('axle_open',(0,0,D['wheel_z']),P['drive']['shaft_shell_hole_diameter_mm']/2,180,'X'))
    for loc,dim in [(P['electronics']['usb_center_mm'],(12,24,6)),(P['electronics']['switch_center_mm'],(10,24,7))]:
        boolean(shell,box('port_open',loc,dim))
    seam=D['body_z']+P['body_split_height_from_center_mm']; gap=P['seam_gap_mm']/2
    upper=clone(shell,'Body_Upper_Shell'); lower=clone(shell,'Body_Lower_Shell')
    clip_z(upper,seam+gap,500); clip_z(lower,-500,seam-gap)
    for x,y in st['deck_mount_xy_mm']:
        boss=cyl('deck_boss',(x,y,st['deck_center_z_mm']+st['deck_thickness_mm']/2+st['deck_boss_height_mm']/2),st['deck_boss_radius_mm'],st['deck_boss_height_mm'])
        intersect(boss,clone(outer,'outer_limit')); union(upper,boss)
        boolean(upper,cyl('insert_pilot',(x,y,st['deck_center_z_mm']+st['deck_thickness_mm']/2+C['body']['insert_depth']/2-1),f['body_insert_pilot_diameter_mm']/2,C['body']['insert_depth']))
    for x,y in st['body_seam_mount_xy_mm']:
        boss=cyl('seam_upper_boss',(x,y,(seam+gap+C['body']['seam_boss_top_z'])/2),st['body_upper_seam_boss_radius_mm'],C['body']['seam_boss_top_z']-(seam+gap))
        intersect(boss,clone(outer,'outer_limit')); union(upper,boss)
        boolean(upper,cyl('upper_insert',(x,y,seam+C['body']['seam_insert_center_offset']),f['body_insert_pilot_diameter_mm']/2,C['body']['seam_insert_depth']))
        boss=cyl('seam_lower_sleeve',(x,y,(C['body']['lower_sleeve_start_z']+seam-gap)/2),st['body_lower_seam_boss_radius_mm'],seam-gap-C['body']['lower_sleeve_start_z'])
        intersect(boss,clone(outer,'outer_limit')); union(lower,boss)
        boolean(lower,cyl('screw_shank',(x,y,55),f['body_screw_clearance_diameter_mm']/2,80))
        seat=st['body_lower_screw_seat_z_mm']
        boolean(lower,cyl('screw_recess',(x,y,seat/2),f['body_head_counterbore_diameter_mm']/2,seat))
    finish(upper,'PRINTABLE','身体上壳','shell',candidate=True,explode=(0,0,50),note='Trial shell; provisional M3/insert holes; no strength claim')
    finish(lower,'PRINTABLE','身体下壳','shell',candidate=True,explode=(0,0,-48),note='Trial shell; 0.6 mm assembly seam and recessed underside screws')
    for o in [outer,shell]: bpy.data.objects.remove(o,do_unlink=True)

def make_head():
    t=P['shell_thickness_mm']; disp=P['display']; hj=P['head_joint']; f=P['fasteners_assumed']; st=P['structure']
    hz=D['head_z']; fy=D['face_y']; gap=P['seam_gap_mm']/2
    outer=head_outer('Head_mother_clipped'); shell=clone(outer,'Head_shell')
    boolean(shell,sphere('head_cavity',(0,0,hz),D['head_radius']-t))
    boolean(shell,cyl('round_face_window',(0,-55,hz),disp['window_diameter_mm']/2,50,'Y'))
    front=clone(shell,'Head_Front_Shell'); rear=clone(shell,'Head_Rear_Shell')
    clip_y(front,-500,-gap); clip_y(rear,gap,500)
    plate_top=D['body_top_z']+hj['rotor_plate_bottom_from_body_top_mm']+hj['rotor_plate_thickness_mm']
    for x,y in hj['head_mount_xy_mm']:
        target=front if y<0 else rear
        boss=cyl('head_base_boss',(x,y,plate_top+hj['head_boss_height_mm']/2),hj['head_boss_radius_mm'],hj['head_boss_height_mm'])
        intersect(boss,clone(outer,'outer_limit')); union(target,boss)
        boolean(target,cyl('head_base_insert',(x,y,plate_top+2.8),f['head_insert_pilot_diameter_mm']/2,6))
    # Real rear tool access bores and sleeves: all nominal screw interfaces remain provisional.
    for sx in [-1,1]:
        x=sx*st['head_seam_screw_x_mm']
        boss=box('head_front_lug',(sx*C['head']['seam_front_lug_center_abs_x'],C['head']['seam_front_lug_y'],hz),C['head']['seam_front_lug_size'])
        intersect(boss,clone(outer,'outer_limit')); union(front,boss)
        boolean(front,cyl('head_seam_insert',(x,C['head']['seam_insert_y'],hz),f['head_insert_pilot_diameter_mm']/2,C['head']['seam_insert_depth'],'Y'))
        sleeve=cyl('head_rear_sleeve',(x,C['head']['seam_rear_sleeve_y'],hz),st['head_seam_sleeve_radius_mm'],C['head']['seam_rear_sleeve_length'],'Y')
        intersect(sleeve,clone(outer,'outer_limit')); union(rear,sleeve)
        boolean(rear,cyl('head_seam_screw',(x,20,hz),f['head_screw_clearance_diameter_mm']/2,42,'Y'))
        boolean(rear,cyl('head_seam_recess',(x,C['head']['seam_recess_y'],hz),f['head_head_counterbore_diameter_mm']/2,C['head']['seam_recess_depth'],'Y'))
    # Display rear-retaining ring; four tabs relieved against the true spherical cavity.
    frame_front=fy+C['head']['frame_front_offset']; frame_depth=disp['mount_frame_depth_mm']
    frame=ring('Display_Mount_Frame',(0,frame_front+frame_depth/2,hz),disp['mount_frame_outer_diameter_mm']/2,disp['mount_frame_inner_diameter_mm']/2,frame_depth,'Y')
    for a in [0,90,180]:
        x=C['head']['display_tab_radial_position']*math.cos(math.radians(a)); z=hz+C['head']['display_tab_radial_position']*math.sin(math.radians(a))
        union(frame,cyl('display_tab',(x,frame_front+frame_depth/2,z),C['head']['display_tab_radius'],frame_depth,'Y'))
        boss=cyl('display_boss',(x,(fy+C['head']['display_boss_front_offset']+frame_front)/2,z),C['head']['display_boss_radius'],frame_front-(fy+C['head']['display_boss_front_offset']),'Y')
        intersect(boss,clone(outer,'outer_limit')); union(front,boss)
        boolean(front,cyl('display_insert',(x,frame_front-C['head']['display_blind_hole_depth']/2,z),f['head_insert_pilot_diameter_mm']/2,C['head']['display_blind_hole_depth']+.02,'Y'))
    intersect(frame,sphere('frame_inner_limit',(0,0,hz),D['head_radius']-t-P['assembly_clearance_per_side_mm']))
    clip_z(frame,hz-disp['pcb_diameter_mm']/2-P['assembly_clearance_per_side_mm'],500)
    for a in [0,90,180]:
        x=C['head']['display_tab_radial_position']*math.cos(math.radians(a)); z=hz+C['head']['display_tab_radial_position']*math.sin(math.radians(a))
        boolean(frame,cyl('frame_bolt',(x,frame_front+2,z),f['head_screw_clearance_diameter_mm']/2,10,'Y'))
    # Recut window after bosses so no boss enters the round face aperture.
    boolean(front,cyl('round_face_window',(0,-55,hz),disp['window_diameter_mm']/2,50,'Y'))
    boolean(front,cyl('display_pcb_edge_relief',(0,fy+C['head']['pcb_center_offset'],hz),disp['pcb_diameter_mm']/2+P['assembly_clearance_per_side_mm'],disp['pcb_thickness_mm']+2*P['assembly_clearance_per_side_mm'],'Y'))
    finish(front,'PRINTABLE','头部前壳','shell','head',True,(0,-55,100),'True sphere shell; local circular opening and internal bosses')
    finish(rear,'PRINTABLE','头部后壳','shell','head',True,(0,55,100),'True sphere shell; rear service screw bores')
    finish(frame,'PRINTABLE','屏幕固定框','frame','head',True,(0,-36,100),'Envelope-specific prototype; hole pattern not supplier-confirmed')
    # Every layer has real thickness and a separate object.
    finish(cyl('Face_Protector',(0,fy+C['head']['protector_center_offset'],hz),disp['window_diameter_mm']/2-disp['protector_edge_clearance_mm'],disp['protector_thickness_mm'],'Y'),
           'PURCHASED_REFERENCE','圆形透明保护片','glass','head',False,(0,-100,100),'Reference circular sheet, 1.2 mm; material/adhesive unselected')
    finish(ring('Black_Bezel',(0,fy+C['head']['bezel_center_offset'],hz),C['head']['bezel_outer_radius'],disp['bezel_inner_diameter_mm']/2,C['head']['bezel_thickness'],'Y'),
           'PRINTABLE','黑色遮光边框','dark','head',False,(0,-84,100),'Thin optical mask; laser-cut/film or prototype, not rigid STL batch')
    finish(cyl('Display_Module_PLACEHOLDER',(0,fy+C['head']['screen_front_offset']+disp['screen_thickness_mm']/2,hz),disp['active_screen_diameter_mm']/2,disp['screen_thickness_mm'],'Y'),
           'PLACEHOLDER','显示屏包络 / 待选型','dark','head',False,(0,-66,100),disp['status'])
    finish(cyl('Display_PCB_PLACEHOLDER',(0,fy+C['head']['pcb_center_offset'],hz),disp['pcb_diameter_mm']/2,disp['pcb_thickness_mm'],'Y'),
           'PLACEHOLDER','显示 PCB 包络','pcb','head',False,(0,-48,100),disp['status'])
    finish(box('Display_Connector_PLACEHOLDER',(0,fy+C['head']['connector_y_offset'],hz+C['head']['connector_z_offset']),disp['connector_size_mm']),
           'PLACEHOLDER','显示连接器包络','dark','head',False,(0,-36,100),'Connector orientation and strain relief pending real module')
    # Only two simple eyes: capsule mesh on the actual display plane, under the protector.
    for sign,name in [(-1,'L'),(1,'R')]:
        x=sign*disp['eye_spacing_mm']/2; w=disp['eye_width_mm']; h=disp['eye_height_mm']
        verts=[]; contour=[]
        for cz,start in [(h/2-w/2,0),(-h/2+w/2,180)]:
            for j in range(17):
                a=math.radians(start+j*180/16)
                contour.append((w/2*math.cos(a),cz+w/2*math.sin(a)))
        for y in [fy+C['head']['eye_front_offset'],fy+C['head']['eye_back_offset']]: verts += [(x+xx,y,hz+zz) for xx,zz in contour]
        n=len(contour); faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        o=mesh('Eye_'+name,verts,faces)
        finish(o,'PURCHASED_REFERENCE','屏幕眼睛像素 '+name,'eye','head',False,(0,-66,100),'Rendered display content, not a physical extra part',role='display_content')
    for o in [outer,shell]: bpy.data.objects.remove(o,do_unlink=True)

def make_wheels():
    dr=P['drive']; f=P['fasteners_assumed']; wx=D['wheel_x']; wz=D['wheel_z']
    for s,name in [(-1,'L'),(1,'R')]:
        group='wheel_'+name
        finish(ring('Tire_'+name,(s*wx,0,wz),D['wheel_radius'],P['tire_inner_radius_mm'],P['wheel_width_mm'],'X'),
               'PURCHASED_REFERENCE','轮胎 '+name,'tire',group,False,(s*53,0,0),'Rubber purchase or separately qualified flexible TPU; nominal envelope')
        hub=ring('Wheel_Hub_'+name,(s*wx,0,wz),P['wheel_hub_radius_mm'],dr['axle_diameter_mm']/2+P['assembly_clearance_per_side_mm'],P['wheel_hub_width_mm'],'X')
        for a in [0,120,240]:
            y=C['wheel']['cap_bolt_pattern_radius']*math.cos(math.radians(a)); z=wz+C['wheel']['cap_bolt_pattern_radius']*math.sin(math.radians(a))
            boolean(hub,cyl('hub_insert',(s*(wx+C['wheel']['hub_insert_x_offset']),y,z),f['head_insert_pilot_diameter_mm']/2,C['wheel']['hub_insert_depth'],'X'))
        finish(hub,'PRINTABLE','轮毂 '+name,'frame',group,False,(s*36,0,0),'HOLD: axle clamp/key and tire retention not selected; geometry trial only')
        capx=wx+P['wheel_width_mm']/2+P['wheel_cap_outer_overhang_mm']-P['wheel_cap_thickness_mm']/2
        cap=cyl('Wheel_Cap_'+name,(s*capx,0,wz),P['wheel_hub_radius_mm'],P['wheel_cap_thickness_mm'],'X')
        # Back-side sockets keep the visible circular cover plain.
        for a in [0,120,240]:
            y=C['wheel']['cap_bolt_pattern_radius']*math.cos(math.radians(a)); z=wz+C['wheel']['cap_bolt_pattern_radius']*math.sin(math.radians(a))
            boolean(cap,cyl('cap_back_socket',(s*(capx-C['wheel']['cap_socket_depth']),y,z),C['wheel']['cap_socket_radius'],C['wheel']['cap_socket_depth'],'X'))
        finish(cap,'PRINTABLE','简洁轮毂盖 '+name,'shell',group,True,(s*78,0,0),'Cosmetic trial; hidden retention/adhesive scheme pending')
        axle=cyl('Independent_Axle_'+name,(s*(dr['axle_inner_x_mm']+dr['axle_outer_x_mm'])/2,0,wz),dr['axle_diameter_mm']/2,dr['axle_outer_x_mm']-dr['axle_inner_x_mm'],'X')
        finish(axle,'PLACEHOLDER','独立承重轮轴 '+name,'metal',group,False,(s*20,0,0),'Steel shaft envelope; bearing spacing and overhang load calculation NOT done')
        for pos,tag in [(dr['bearing_inner_x_mm'],'Inner'),(dr['bearing_outer_x_mm'],'Outer')]:
            finish(ring('Wheel_Bearing_'+name+'_'+tag,(s*pos,0,wz),dr['bearing_od_mm']/2,dr['bearing_id_mm']/2,dr['bearing_width_mm'],'X'),
                   'PLACEHOLDER','轮轴承 '+name+' '+tag,'metal','body',False,(s*22,0,-15),'6 x 13 x 5 mm reservation, not an ordered bearing')

def make_frame_and_drive():
    st=P['structure']; dr=P['drive']; hj=P['head_joint']; f=P['fasteners_assumed']; wz=D['wheel_z']
    deck=cyl('Load_Frame',(0,0,st['deck_center_z_mm']),st['deck_radius_mm'],st['deck_thickness_mm'])
    intersect(deck,box('deck_clip',(0,0,st['deck_center_z_mm']),(2*st['deck_half_x_mm'],2*st['deck_half_y_mm'],20)))
    for s in [-1,1]:
        for x in [dr['bearing_inner_x_mm'],dr['bearing_outer_x_mm']]:
            # Tall pylon transfers the wheel load to the common rigid frame, not the thin shell.
            ringpart=ring('bearing_pylon',(s*x,0,wz),dr['bearing_carrier_od_mm']/2,dr['bearing_od_mm']/2+P['assembly_clearance_per_side_mm'],dr['bearing_carrier_width_mm'],'X')
            post=box('pylon_post',(s*x,0,(wz+C['frame']['pylon_join_from_axle_z']+st['deck_center_z_mm']-st['deck_thickness_mm']/2+C['frame']['deck_join_overlap'])/2),(dr['bearing_carrier_width_mm'],C['frame']['pylon_y_width'],st['deck_center_z_mm']-st['deck_thickness_mm']/2+C['frame']['deck_join_overlap']-(wz+C['frame']['pylon_join_from_axle_z'])))
            union(ringpart,post)
            boolean(ringpart,cyl('pylon_bearing_relief',(s*x,0,wz),dr['bearing_od_mm']/2+P['assembly_clearance_per_side_mm'],dr['bearing_carrier_width_mm']+2,'X'))
            union(deck,ringpart)
    for x,y in st['head_support_xy_mm']:
        union(deck,cyl('head_support',(x,y,(st['deck_center_z_mm']+st['deck_thickness_mm']/2-C['frame']['post_join_overlap']+D['bearing_z']-hj['bearing_height_mm']/2-hj['carrier_plate_thickness_mm'])/2),st['head_support_radius_mm'],D['bearing_z']-hj['bearing_height_mm']/2-hj['carrier_plate_thickness_mm']-(st['deck_center_z_mm']+st['deck_thickness_mm']/2-C['frame']['post_join_overlap'])))
    # Motor mounts have through-screws from above the deck.
    for s in [-1,1]:
        y=s*dr['motor_offset_y_mm']
        holes(deck,[(-dr['motor_clamp_x_mm'],y),(dr['motor_clamp_x_mm'],y)],f['body_screw_clearance_diameter_mm']/2,107,118)
    holes(deck,st['deck_mount_xy_mm'],f['body_screw_clearance_diameter_mm']/2,107,119)
    holes(deck,st['cable_channel_xy_mm'],st['cable_channel_radius_mm'],107,120)
    boolean(deck,box('servo_open',hj['servo_center_mm'],(hj['servo_body_mm'][0]+.6,hj['servo_body_mm'][1]+.6,40)))
    holes(deck,C['frame']['servo_mount_holes_xy'],1.4,108,118)
    finish(deck,'PRINTABLE','内部承重框架及轮轴承座','frame',candidate=True,explode=(0,0,10),note='Load path geometry only; bearing fits and strength require tests; PETG/PA trial')
    for s,name in [(-1,'L'),(1,'R')]:
        # Motor L front / output left. Motor R rear / output right.
        mx=-s*dr['motor_offset_x_mm']; my=s*dr['motor_offset_y_mm']; mz=dr['motor_z_mm']
        can=cyl('Motor_'+name+'_PLACEHOLDER',(mx,my,mz),dr['motor_can_diameter_mm']/2,dr['motor_can_length_mm'],'X')
        finish(can,'PLACEHOLDER','编码器减速电机 '+name+' 主体','metal',explode=(s*25,s*25,0),note=dr['status']); can['actuator_id']='drive_'+name
        encoderx=mx-s*(dr['motor_can_length_mm']/2+dr['motor_encoder_length_mm']/2)
        finish(cyl('Encoder_'+name+'_PLACEHOLDER',(encoderx,my,mz),dr['motor_encoder_diameter_mm']/2,dr['motor_encoder_length_mm'],'X'),
               'PLACEHOLDER','电机编码器 '+name,'dark',explode=(s*25,s*25,0),note=dr['status'])
        shaftx=mx+s*(dr['motor_can_length_mm']/2+dr['motor_output_shaft_length_mm']/2)
        finish(cyl('Motor_Output_'+name,(shaftx,my,mz),dr['motor_output_shaft_diameter_mm']/2,dr['motor_output_shaft_length_mm'],'X'),
               'PLACEHOLDER','电机输出轴 '+name,'metal',explode=(s*25,s*25,0),note='Motor output does not directly bear the wheel load')
        mount=None
        for x in [-dr['motor_clamp_x_mm'],dr['motor_clamp_x_mm']]:
            r=ring('Motor_Mount_'+name,(x,my,mz),dr['motor_clamp_od_mm']/2,dr['motor_can_diameter_mm']/2+.3,dr['motor_clamp_width_mm'],'X')
            union(r,box('clamp_riser',(x,my,(C['frame']['motor_riser_z0']+st['deck_center_z_mm']-st['deck_thickness_mm']/2)/2),(*C['frame']['motor_riser_size_xy'],st['deck_center_z_mm']-st['deck_thickness_mm']/2-C['frame']['motor_riser_z0'])))
            if mount is None: mount=r
            else: union(mount,r)
        union(mount,box('mount_bridge',(0,my,C['frame']['motor_bridge_z']),C['frame']['motor_bridge_size']))
        holes(mount,[(-dr['motor_clamp_x_mm'],my),(dr['motor_clamp_x_mm'],my)],f['body_insert_pilot_diameter_mm']/2,C['frame']['mount_insert_z0'],C['frame']['mount_insert_z1'])
        finish(mount,'PRINTABLE','电机安装件 '+name,'frame',candidate=True,explode=(s*10,s*35,0),note='Slide-in clamp for Ø25 placeholder, strap/axial stop and supplier holes pending')
        for pos,tag,bore in [((s*dr['pulley_plane_x_mm'],my,mz),'Motor',dr['motor_output_shaft_diameter_mm']/2),((s*dr['pulley_plane_x_mm'],0,wz),'Axle',dr['axle_diameter_mm']/2)]:
            finish(ring('Pulley_'+name+'_'+tag,pos,dr['pulley_pitch_radius_mm'],bore,dr['pulley_width_mm'],'X'),
                   'PLACEHOLDER','带轮节圆包络 '+name+' '+tag,'dark',explode=(s*18,0,0),note='Smooth pitch envelope only; belt pitch, teeth, ratio, tensioner and clamp NOT designed')
        # Capsule-shaped belt envelope around two equal pitch pulleys, in the YZ plane.
        a=Vector((0,wz)); b=Vector((my,mz)); d=(b-a).normalized(); n=Vector((-d.y,d.x)); pts=[]
        for center,base in [(b,d),(a,-d)]:
            for j in range(33):
                ang=-math.pi/2+j*math.pi/32
                vec=base*math.cos(ang)+Vector((-base.y,base.x))*math.sin(ang)
                pts.append((center,vec))
        vs=[]; rad=dr['pulley_pitch_radius_mm']
        for x,r in [(s*dr['pulley_plane_x_mm']-dr['belt_width_mm']/2,rad),(s*dr['pulley_plane_x_mm']+dr['belt_width_mm']/2,rad),
                    (s*dr['pulley_plane_x_mm']-dr['belt_width_mm']/2,rad+dr['belt_thickness_mm']),(s*dr['pulley_plane_x_mm']+dr['belt_width_mm']/2,rad+dr['belt_thickness_mm'])]:
            for c,v in pts: vs.append((x,c.x+v.x*r,c.y+v.y*r))
        nn=len(pts); fs=[]
        for j in range(nn):
            k=(j+1)%nn
            fs += [(j,k,nn+k,nn+j),(2*nn+j,3*nn+j,3*nn+k,2*nn+k),(j,2*nn+j,2*nn+k,k),(nn+j,nn+k,3*nn+k,3*nn+j)]
        finish(mesh('Belt_'+name+'_ENVELOPE',vs,fs),'PLACEHOLDER','同步带运动包络 '+name,'belt',explode=(s*18,0,0),note='Flexible transmission envelope; pitch/length/tension and durability unconfirmed')

def make_head_joint():
    hj=P['head_joint']; f=P['fasteners_assumed']; st=P['structure']; bz=D['bearing_z']; top=D['body_top_z']; lo=bz-hj['bearing_height_mm']/2
    carrier=ring('Head_Bearing_Carrier',(0,0,lo-hj['carrier_plate_thickness_mm']/2),hj['carrier_radius_mm'],hj['carrier_center_hole_radius_mm'],hj['carrier_plate_thickness_mm'])
    union(carrier,ring('bearing_collar',(0,0,lo+hj['carrier_collar_height_mm']/2),hj['carrier_collar_outer_radius_mm'],hj['bearing_od_mm']/2+P['assembly_clearance_per_side_mm'],hj['carrier_collar_height_mm']))
    holes(carrier,st['head_support_xy_mm'],1.4,136,146)
    finish(carrier,'PRINTABLE','独立头部承重环支座','frame',candidate=True,explode=(0,0,57),note='Bearing flange support; outer-race clamp/retention awaits bearing selection')
    finish(ring('Head_Bearing_Outer_Race',(0,0,bz),hj['bearing_od_mm']/2,hj['bearing_od_mm']/2-C['joint']['bearing_race_radial_thickness'],hj['bearing_height_mm']),'PLACEHOLDER','头部轴承外圈','metal',explode=(0,0,65),note='Bearing envelope 24 x 36 x 6 mm; rolling geometry schematic')
    finish(ring('Head_Bearing_Inner_Race',(0,0,bz),hj['bearing_id_mm']/2+C['joint']['bearing_race_radial_thickness'],hj['bearing_id_mm']/2,hj['bearing_height_mm']),'PLACEHOLDER','头部轴承内圈','metal','head',False,(0,0,69),'Independent bearing load path; fit and capacity not selected')
    # Balls show the independent load-bearing path and are explicitly schematic reference geometry.
    for j in range(10):
        a=2*math.pi*j/10
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=(hj['bearing_od_mm']/2-hj['bearing_id_mm']/2-2*C['joint']['bearing_race_radial_thickness'])/2,location=((hj['bearing_od_mm']+hj['bearing_id_mm'])/4*math.cos(a),(hj['bearing_od_mm']+hj['bearing_id_mm'])/4*math.sin(a),bz))
        finish(raw(bpy.context.object,'Head_Bearing_Ball_%02d'%j),'PLACEHOLDER','轴承滚动体示意 %02d'%j,'metal',explode=(0,0,65),note='Schematic rolling contact; not bearing manufacturing geometry')
    pb=top+hj['rotor_plate_bottom_from_body_top_mm']; pt=pb+hj['rotor_plate_thickness_mm']
    rotor=ring('Head_Turntable',(0,0,(pb+pt)/2),hj['rotor_plate_radius_mm'],hj['spindle_bore_radius_mm'],hj['rotor_plate_thickness_mm'])
    union(rotor,ring('spindle',(0,0,(C['joint']['spindle_bottom_z']+pt-C['joint']['spindle_plate_union_overlap'])/2),hj['bearing_id_mm']/2,hj['spindle_bore_radius_mm'],pt-C['joint']['spindle_plate_union_overlap']-C['joint']['spindle_bottom_z']))
    holes(rotor,hj['head_mount_xy_mm'],f['head_screw_clearance_diameter_mm']/2,148,156)
    finish(rotor,'PRINTABLE','头部转盘与空心主轴','frame','head',True,(0,0,78),'Independent bearing-supported rotor; 14 mm through-bore; torque attachment provisional')
    servobox=finish(box('Head_Servo_PLACEHOLDER',hj['servo_center_mm'],hj['servo_body_mm']),
                    'PLACEHOLDER','头部位置舵机 / 待选型','dark',explode=(-28,0,35),note=hj['status']); servobox['actuator_id']='head_yaw'
    sc=hj['servo_center_mm']; servotop=sc[2]+hj['servo_body_mm'][2]/2
    finish(cyl('Servo_Output',(sc[0],sc[1],servotop+hj['servo_output_height_mm']/2),hj['servo_output_diameter_mm']/2,hj['servo_output_height_mm']),
           'PLACEHOLDER','舵机输出轴包络','metal',explode=(-28,0,35),note='Output position and spline unconfirmed')
    servo_mount=box('Servo_Mount',(sc[0],sc[1],st['deck_center_z_mm']+st['deck_thickness_mm']/2+C['frame']['servo_mount_size'][2]/2),C['frame']['servo_mount_size'])
    boolean(servo_mount,box('servo_cavity',(sc[0],sc[1],116),(hj['servo_body_mm'][0]+2*P['assembly_clearance_per_side_mm'],hj['servo_body_mm'][1]+2*P['assembly_clearance_per_side_mm'],20)))
    holes(servo_mount,C['frame']['servo_mount_holes_xy'],1.4,111,122)
    holes(servo_mount,st['head_support_xy_mm'],st['head_support_radius_mm']+P['assembly_clearance_per_side_mm'],111,120)
    finish(servo_mount,'PRINTABLE','头部执行器支架','frame',candidate=True,explode=(-35,0,25),note='Provisional servo interface; mounting ears not selected')
    finish(ring('Servo_Gear_Pitch',(sc[0],sc[1],hj['gear_center_z_mm']),hj['gear_driver_pitch_radius_mm'],2,hj['gear_width_mm']),
           'PLACEHOLDER','舵机齿轮节圆包络','dark',explode=(-28,0,45),note='Pitch envelope only; no teeth or confirmed spline')
    finish(ring('Head_Gear_Pitch',(0,0,hj['gear_center_z_mm']),hj['gear_driven_pitch_radius_mm'],12,hj['gear_width_mm']),
           'PLACEHOLDER','头部齿轮节圆包络','dark','head',False,(0,0,53),'Pitch envelope only; ratio 14:8 would require 210° servo travel for ±60° head, pending actuator')
    # Travel stop concept: separate fixed stop blocks and moving flag, deliberately behind the bearing.
    # Flag at radius 26, underside of rotor; fixed pads lie outside commanded +/-60 deg.
    flag=box('Yaw_Stop_Flag',(0,C['joint']['stop_radius'],pb-C['joint']['stop_flag_size'][2]/2),C['joint']['stop_flag_size'])
    finish(flag,'PRINTABLE','头部机械限位旗片','frame','head',False,(0,0,78),'HOLD: ±65° hard-stop concept, fastener attachment and tolerance pending')
    for s in [-1,1]:
        a=s*(math.radians(hj['mechanical_stop_deg'])+2*math.atan(C['joint']['stop_flag_size'][0]/2/C['joint']['stop_radius'])); x=-C['joint']['stop_radius']*math.sin(a); y=C['joint']['stop_radius']*math.cos(a)
        stop=box('Yaw_Stop_Fixed_'+str(s),(x,y,(lo+pb-C['joint']['stop_rotor_axial_gap'])/2),(*C['joint']['stop_fixed_size_xy'],pb-C['joint']['stop_rotor_axial_gap']-lo))
        stop.rotation_euler.z=a
        finish(stop,'PRINTABLE','固定限位块 '+str(s),'frame',candidate=False,explode=(0,0,57),note='HOLD: stand-off pads require final gap/attachment sizing')
    # Bending-space envelope is a visible reservation, not a promised cable motion solution.
    cable=ring('Head_Cable_Service_Loop',(0,0,C['joint']['service_loop_center_z']),hj['wire_loop_radius_mm']+hj['wire_bundle_diameter_mm']/2,
               hj['wire_loop_radius_mm']-hj['wire_bundle_diameter_mm']/2,4)
    finish(cable,'PLACEHOLDER','头部线束弯曲空间包络','copper','head',False,(0,0,90),'NOT physical cable route: service-loop swept reservation; cable bend spec unknown')
    finish(cyl('Head_Wire_Through_Bore',(0,0,C['joint']['wire_center_z']),hj['wire_bundle_diameter_mm']/2,C['joint']['wire_length']),'PLACEHOLDER','头部穿轴线束包络','copper','head',False,(0,0,85),'4 mm bundle in 14 mm bore; strain-relief and dynamic fatigue pending')

def make_battery_electronics():
    ba=P['battery']; st=P['structure']; el=P['electronics']; c=P['assembly_clearance_per_side_mm']; bz=ba['center_z_mm']; bx,by,bh=ba['envelope_mm']; ay=ba['adjust_y_mm']
    ztop=bz-bh/2-c; wall=ba['tray_wall_mm']; bottom=ztop-ba['tray_floor_mm']
    tray=box('Battery_Tray',(0,ay,(bottom+ztop)/2),(bx+2*c+2*wall,by+2*c+2*wall,ba['tray_floor_mm']))
    for s in [-1,1]:
        union(tray,box('tray_side',(s*(bx/2+c+wall/2),ay,ztop+ba['tray_wall_height_mm']/2),(wall,by+2*c+2*wall,ba['tray_wall_height_mm']+.1)))
        union(tray,box('tray_end',(0,ay+s*(by/2+c+wall/2),ztop+ba['tray_wall_height_mm']/2),(bx+2*c,wall,ba['tray_wall_height_mm']+.1)))
    for x,y in st['battery_hanger_xy_mm']:
        union(tray,box('slotted_tab',(x,y,(bottom+ztop)/2),(*C['battery']['slot_tab_size_xy'],ba['tray_floor_mm'])))
        cutter=box('adjustment_slot',(x,y,ztop),(C['battery']['slot_diameter'],2*ba['adjust_y_limit_mm'],12))
        for s in [-1,1]: union(cutter,cyl('slot_end',(x,y+s*ba['adjust_y_limit_mm'],ztop),C['battery']['slot_diameter']/2,12))
        boolean(tray,cutter)
    for s in [-1,1]:
        boolean(tray,box('strap_clearance_slot',(s*(bx/2+c+wall/2),ay,ztop+1),(wall+C['battery']['strap_slot_extra_x'],ba['strap_width_mm']+2*c,12)))
    finish(tray,'PRINTABLE','可调电池托架','frame',candidate=True,explode=(0,-30,-35),note='Y adjustment ±4 mm; tray/strap prototype, final battery and fasteners unselected')
    finish(box('Battery_PLACEHOLDER',(0,ay,bz),ba['envelope_mm'],C['battery']['pack_bevel']),'PLACEHOLDER','可调电池包络','battery',explode=(0,-45,-22),note=ba['status'])
    for i,(x,y) in enumerate(st['battery_hanger_xy_mm']):
        hanger=cyl('Battery_Hanger_%d'%i,(x,y,(ztop+110)/2),st['hanger_radius_mm'],110-ztop)
        finish(hanger,'PLACEHOLDER','电池托架吊杆 %d'%i,'metal',explode=(0,-20,-5),note='Threaded rod/standoff concept, length and attachment pending')
    # Strap has a solid rectangular U-shaped envelope, above the cell with a 0.5 mm gap.
    strap=box('Battery_Strap',(0,ay,bz+bh/2+C['battery']['strap_top_offset']),(bx+C['battery']['strap_width_extra'],ba['strap_width_mm'],ba['strap_thickness_mm']))
    for s in [-1,1]: union(strap,box('strap_side',(s*(bx/2+C['battery']['strap_side_offset']),ay,bz),(ba['strap_thickness_mm'],ba['strap_width_mm'],bh+C['battery']['strap_height_extra'])))
    finish(strap,'PURCHASED_REFERENCE','电池固定带','belt',explode=(0,-45,-14),note='Removable strap, fastening/battery insulation unselected')
    for key,label in [('controller','主控'),('driver','电机驱动'),('imu','IMU'),('bms','电池保护 BMS'),('charger_regulator','匹配电池的充电与稳压模块'),('usb','USB-C 外部接口'),('switch','电源开关')]:
        mat='pcb' if key not in ['usb','switch'] else 'dark'
        o=finish(box(key.title()+'_PLACEHOLDER',el[key+'_center_mm'],el[key+'_envelope_mm']),
                 'PLACEHOLDER',label+' / 待选型',mat,explode=(0,25 if el[key+'_center_mm'][1]>0 else -25,20),note='Envelope only; hole pattern, connector, thermal and electrical compatibility unconfirmed')
        if key=='imu': o['axis_definition']=el['imu_axes']; o['mount_requirement']='Rigid deck; fixed orientation'
    for key in ['controller','driver','imu']:
        pos=el[key+'_center_mm']; dims=el[key+'_envelope_mm']; plate_thickness=C['electronics']['mount_plate_thickness'] if key!='imu' else C['electronics']['imu_mount_plate_thickness']; platez=st['deck_center_z_mm']+st['deck_thickness_mm']/2+plate_thickness/2
        plate=box(key.title()+'_Mount',(pos[0],pos[1],platez),(dims[0]+2*C['electronics']['mount_edge_margin'],dims[1]+2*C['electronics']['mount_edge_margin'],plate_thickness))
        # Interface is intentionally not faked with a supplier hole pattern.
        for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            x=pos[0]+sx*(dims[0]/2-C['electronics']['standoff_edge_inset']); y=pos[1]+sy*(dims[1]/2-C['electronics']['standoff_edge_inset'])
            plate_top=platez+plate_thickness/2
            h=pos[2]-dims[2]/2-plate_top
            if h>0: union(plate,cyl('pcb_standoff',(x,y,plate_top+(h-C['electronics']['standoff_union_overlap'])/2),C['electronics']['standoff_radius'],h+C['electronics']['standoff_union_overlap']))
            boolean(plate,cyl('pcb_trial_hole',(x,y,pos[2]-2),C['electronics']['trial_hole_radius'],20))
        finish(plate,'PRINTABLE',{'controller':'主控板支架','driver':'驱动板支架','imu':'刚性 IMU 安装座'}[key],
               'frame',candidate=True,explode=(0,25 if pos[1]>0 else -25,15),note='Trial support locations, NOT a confirmed PCB hole pattern')
    # Cable ties/strain-relief guides fixed to the frame, encoder route channels in the deck.
    for s in [-1,1]:
        guide=box('Cable_Guide_'+str(s),(st['cable_channel_xy_mm'][0][0],s*abs(st['cable_channel_xy_mm'][0][1]),C['frame']['cable_guide_center_z']),C['frame']['cable_guide_size'])
        boolean(guide,cyl('cable_channel',(st['cable_channel_xy_mm'][0][0],s*abs(st['cable_channel_xy_mm'][0][1]),C['frame']['cable_guide_center_z']),st['cable_channel_radius_mm'],C['frame']['cable_guide_size'][2]+2))
        finish(guide,'PRINTABLE','走线导向环 '+str(s),'frame',candidate=True,explode=(0,0,25),note='8 mm channel, separate clamp/tie and real cable bend radii pending')

def make_coupons():
    f=P['fasteners_assumed']
    for key,ds,depth in [('Clearance',f['coupon_clearance_diameters_mm'],C['coupons']['clearance_strip_height']),('Insert',f['coupon_insert_diameters_mm'],C['coupons']['insert_strip_height'])]:
        o=box('Coupon_'+key,(0,0,depth/2),(len(ds)*C['coupons']['hole_spacing']+C['coupons']['end_margin_total'],C['coupons']['strip_width'],depth))
        for i,d in enumerate(ds): boolean(o,cyl('coupon_hole',((i-(len(ds)-1)/2)*C['coupons']['hole_spacing'],0,depth/2),d/2,depth+2))
        finish(o,'COUPONS','试打孔径阶梯 '+key,'coupon','coupon',True,note='Hole order left to right: '+str(ds)+' mm. Measure after cooling; not universal fit.',role='coupon')
    # Matched peg/slot pairs with multiple side clearances; not falsely presented as a verified snap joint.
    o=box('Coupon_Fit_Slots',(0,0,C['coupons']['slot_block_size'][2]/2),C['coupons']['slot_block_size'])
    for x,c in zip(C['coupons']['slot_x_positions'],C['coupons']['slot_per_side_gaps']): boolean(o,box('slot',(x,0,2),(C['coupons']['peg_size'][0]+2*c,C['coupons']['peg_size'][1]+2*c,2*C['coupons']['slot_block_size'][2])))
    finish(o,'COUPONS','单边配合间隙试片','coupon','coupon',True,note='6 x 10 mm peg slots; left→right per-side .2/.3/.4/.5 mm. Snap retention NOT designed.',role='coupon')
    o=box('Coupon_Fit_Peg',(0,0,C['coupons']['peg_base_size'][2]/2),C['coupons']['peg_base_size']); union(o,box('peg',(0,0,C['coupons']['peg_base_size'][2]+C['coupons']['peg_size'][2]/2-.2),C['coupons']['peg_size']))
    finish(o,'COUPONS','配合间隙标准凸块','coupon','coupon',True,note='Use with fit slots. No confirmed snap system.',role='coupon')

def make_fasteners():
    st=P['structure']; f=P['fasteners_assumed']; ff=f['solid_envelopes']
    seam=D['body_z']+P['body_split_height_from_center_mm']
    for family,positions in [('Body',st['body_seam_mount_xy_mm']),('Frame',st['deck_mount_xy_mm'])]:
        seat=st['body_lower_screw_seat_z_mm'] if family=='Body' else st['deck_center_z_mm']-st['deck_thickness_mm']/2
        tip=seam+ff['body_screw_tip_above_seam_mm'] if family=='Body' else seat+ff['frame_screw_shank_length_mm']
        insert_z=seam+ff['body_insert_center_above_seam_mm'] if family=='Body' else st['deck_center_z_mm']+st['deck_thickness_mm']/2+ff['frame_insert_center_above_deck_mm']
        for j,(x,y) in enumerate(positions):
            bolt=cyl(f'{family}_Screw_{j}',(x,y,(seat+tip)/2),ff['screw_shank_diameter_mm']/2,tip-seat)
            union(bolt,cyl('fastener_head',(x,y,seat-ff['screw_head_height_mm']/2),ff['screw_head_diameter_mm']/2,ff['screw_head_height_mm']))
            finish(bolt,'PLACEHOLDER',('身体分壳' if family=='Body' else '承重框架')+f'螺钉 {j+1}','metal',explode=(0,0,-22 if family=='Body' else 22),note='Smooth screw envelope only, no modeled thread; diameter/head/length are trial assumptions, not selected hardware')
            ins=ring(f'{family}_Insert_{j}',(x,y,insert_z),ff['insert_outer_diameter_mm']/2,ff['screw_shank_diameter_mm']/2,ff['insert_length_mm'])
            finish(ins,'PLACEHOLDER',('身体分壳' if family=='Body' else '承重框架')+f'嵌件 {j+1}','metal',explode=(0,0,-10 if family=='Body' else 32),note='Insert reservation; outer pilot gap 0.1 mm radial, real heat-insert fit and thread not confirmed')

def make_datums_pivots():
    for name,loc,r in [('Head_Mother_Sphere',(0,0,D['head_z']),D['head_radius']),('Body_Mother_Sphere',(0,0,D['body_z']),D['body_radius'])]:
        o=sphere(name,loc,r); move_collection(o,'DATUMS'); o['role']='datum'; o['radius_mm']=r; o.display_type='WIRE'
    hp=empty('Head_Pivot',(0,0,D['bearing_z'])); hp['yaw_deg']=0.0
    hp.id_properties_ui('yaw_deg').update(min=-P['head_yaw_limit_deg'],max=P['head_yaw_limit_deg'],description='Head yaw deg; frame 1 assembly')
    pivots={'head':hp}
    for s,name in [(-1,'L'),(1,'R')]:
        q=empty('Wheel_'+name+'_Pivot',(s*D['wheel_x'],0,D['wheel_z'])); q['spin_deg']=0.0
        q.id_properties_ui('spin_deg').update(min=-10000,max=10000,description='Wheel rotation deg, local X axis')
        pivots['wheel_'+name]=q
    for key,o in pivots.items():
        prop='yaw_deg' if key=='head' else 'spin_deg'; idx=2 if key=='head' else 0
        fc=o.driver_add('rotation_euler',idx); dr=fc.driver; dr.type='SCRIPTED'
        v=dr.variables.new(); v.name='deg'; v.type='SINGLE_PROP'; v.targets[0].id=o; v.targets[0].data_path='["'+prop+'"]'
        dr.expression='deg * 0.017453292519943295'
    bpy.context.view_layer.update()
    for o in list(bpy.context.scene.objects):
        if o.get('role') not in ['part','display_content']: continue
        parent=pivots.get(o.get('group'))
        # Local origins are meaningful even without using the parent controls.
        if parent:
            set_origin(o,parent.location)
            bpy.context.view_layer.update()
            mw=o.matrix_world.copy(); o.parent=parent
            o.matrix_parent_inverse=parent.matrix_world.inverted()
            o.matrix_basis=mw
        o['assembly_location']=list(o.location); o['assembly_rotation']=list(o.rotation_euler)
        base=o.location.copy(); o.keyframe_insert(data_path='location',frame=1)
        o.location=base+Vector(o.get('explode_offset_mm',(0,0,0))); o.keyframe_insert(data_path='location',frame=80)
        o.location=base
    sc=bpy.context.scene; sc.frame_start=1; sc.frame_end=80
    sc.timeline_markers.clear(); sc.timeline_markers.new('ASSEMBLED / 装配',frame=1); sc.timeline_markers.new('EXPLODED / 爆炸',frame=80)
    assembled()

def studio():
    sc=bpy.context.scene; sc.world=bpy.data.worlds.new(PREFIX+'World') if not bpy.data.worlds.get(PREFIX+'World') else bpy.data.worlds[PREFIX+'World']
    mark(sc.world); sc.world.use_nodes=True; sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.82,.85,.9,1)
    sc.world.node_tree.nodes['Background'].inputs[1].default_value=.55
    for name,loc,power,size in [('Key',(-220,-320,430),1900000,280),('Fill',(260,-100,220),950000,240),('Rim',(50,230,360),1700000,200)]:
        light=mark(bpy.data.lights.new(PREFIX+name,'AREA')); light.energy=power; light.shape='DISK'; light.size=size
        o=mark(bpy.data.objects.new(PREFIX+name,light)); COLS['CAMERAS_LIGHTS'].objects.link(o); o.location=loc
        o.rotation_euler=(Vector((0,0,110))-o.location).to_track_quat('-Z','Y').to_euler()
    ground=box('Studio_Ground',(0,0,-1.5),(1400,1400,3)); finish(ground,'CAMERAS_LIGHTS','渲染地面','ground',role='studio')
    sc.render.engine=P['render']['engine']; sc.cycles.samples=P['render']['samples']; sc.cycles.use_denoising=True
    sc.render.resolution_x=P['render']['resolution']; sc.render.resolution_y=P['render']['resolution']; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG'; sc.render.film_transparent=False
    try: sc.view_settings.view_transform='AgX'
    except: pass
    # Default camera is a real 45° view, used also as the initial UI view.
    data=mark(bpy.data.cameras.new(PREFIX+'Camera_45')); cam=mark(bpy.data.objects.new(PREFIX+'Camera_45',data)); COLS['CAMERAS_LIGHTS'].objects.link(cam)
    cam.location=(400,-400,285); cam.rotation_euler=(Vector((0,0,116))-cam.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO'; data.ortho_scale=285; data.clip_end=5000; sc.camera=cam
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=340; area.spaces.active.region_3d.view_location=(0,0,116)
            area.spaces.active.clip_end=5000

def main():
    scene=setup_scene()
    for args in [('shell',(.79,.77,.71),0,.43),('frame',(.32,.37,.38),0,.5),('tire',(.018,.023,.026),0,.78),('metal',(.33,.39,.43),.7,.28),
                 ('pcb',(.035,.21,.19),.15,.56),('battery',(.17,.21,.28),.1,.48),('dark',(.006,.009,.012),0,.37),('eye',(.65,.9,1),0,.2,2.2),
                 ('glass',(.94,.97,.99),0,.08,0,1),('belt',(.026,.033,.041),0,.6),('copper',(.3,.17,.085),.2,.5),('coupon',(.48,.63,.66),0,.5),('ground',(.77,.8,.82),0,.8)]: material(*args)
    print('MORI: building shell solids',flush=True); make_body(); make_head()
    print('MORI: building load frame and three actuators',flush=True); make_wheels(); make_frame_and_drive(); make_head_joint()
    print('MORI: installing battery/electronic reservation envelopes',flush=True); make_battery_electronics(); make_fasteners(); make_coupons(); make_datums_pivots(); studio()
    # Text blocks make the file self-explanatory and preserve the exact parameter snapshot.
    for name,content in [('MORI_PARAMS.json',(ROOT/'params.json').read_text()),('MORI_README','MORI / STRUCTURAL STUDY\nCoordinates and STL: mm; scene scale 0.001. FRONT = -Y.\nFrame 1 ASSEMBLED; frame 80 EXPLODED.\nHead_Pivot[yaw_deg]: ±60. Wheels: spin_deg around X.\nPRINTABLE is a candidate category, not engineering approval.\nAll actuator/electronic/axle/bearing interfaces remain unselected.\nNo balance/load validation. See reports/validation.md and README.md.\n')]:
        tx=bpy.data.texts.get(name) or bpy.data.texts.new(name); tx.clear(); tx.write(content); mark(tx)
    scene['params_sha256']=__import__('hashlib').sha256((ROOT/'params.json').read_bytes()).hexdigest()
    save_json(ROOT/'reports/derived.json',D); write_bom()
    save_json(ROOT/'reports/build_manifest.json',dict(blender=bpy.app.version_string,unit_scale=scene.unit_settings.scale_length,derived=D,
              tagged_objects=len([o for o in scene.objects if o.get('mori_owner')==OWNER]),part_count=len(parts()),candidate_count=len([o for o in parts(True) if o.get('export_candidate')]),
              references='No reference images provided',params_sha256=scene['params_sha256']))
    scene.render.filepath=str(ROOT/'renders/45_assembled.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/MORI_assembly.blend'))
    print('MORI BUILD COMPLETE',flush=True)

if __name__=='__main__': main()
