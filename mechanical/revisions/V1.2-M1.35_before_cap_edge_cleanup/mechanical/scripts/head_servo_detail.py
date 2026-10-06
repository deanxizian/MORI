"""M1.30 SCS0009 drawing reconstruction and uncomplicated head-servo seats.

The drawing defines the interfaces. Undimensioned appearance features are
explicitly assumptions; neither these meshes nor the old horns certify a fit.
"""
from common import *
from monocoque_structure import obj,source_build
from purchased_geometry import remove_generated
from simple_modules import module
from structural_simplification import plate,hardware,volume

S=P.get('head_servo_detail',{})


def canonical_case(name):
    c=S['cosmetic_assumptions'];w=S['case_width_mm'];h=S['main_case_height_mm'];cx=S['case_center_from_output_x_mm']
    o=box(name,(cx,0,h/2),(S['case_length_mm'],w,h),c['case_corner_relief_mm'])
    eb,et=S['ear_bottom_mm'],S['ear_top_mm'];ex=S['ear_outer_x_mm']
    # The actual ear is a continuous flange reaching the case, not an isolated
    # four-millimetre box centred at its hole.
    union(o,box('continuous_ear_flange',((ex[0]+ex[1])/2,0,(eb+et)/2),
                (ex[1]-ex[0],S['ear_width_mm'],et-eb),.15))
    for x in S['output_to_ear_hole_mm']:
        boolean(o,cyl('documented_ear_hole',(x,0,(eb+et)/2),S['ear_hole_diameter_mm']/2,et-eb+2,n=64))
    union(o,cyl('main_gear_cap',(0,0,(h+S['gearbox_top_mm'])/2),S['ear_width_mm']/2,S['gearbox_top_mm']-h,n=128))
    gh=c['secondary_gear_boss_height_mm']
    union(o,cyl('secondary_gear_cap',(5.7,0,h+gh/2),c['secondary_gear_boss_radius_mm'],gh,n=96))
    # Shallow cover seams remain closed through the body. They are visual
    # assumptions, not gaps between disconnected servo components.
    for z in c['cover_seam_z_mm']:
        cutter=box('seam_outer',(cx,0,z),(S['case_length_mm']+2,w+2,c['cover_seam_width_mm']))
        boolean(cutter,box('preserve_closed_case',(cx,0,z),
                    (S['case_length_mm']-2*c['cover_seam_depth_mm'],w-2*c['cover_seam_depth_mm'],1)))
        boolean(o,cutter)
    boolean(o,cyl('M2_thread_indication',(0,0,S['gearbox_top_mm']-1.5),1,3.1,n=64))
    return o


def canonical_output(name):
    count=S['spline_teeth'];ro=S['spline_outer_diameter_mm']/2;ri=S['cosmetic_assumptions']['spline_visual_root_radius_mm']
    z0=S['gearbox_top_mm'];z1=S['overall_with_spline_mm'];xy=[]
    for k in range(count):
        for offset,r in [(0,ri),(.22,ro),(.55,ro),(.77,ri)]:
            a=(k+offset)*2*math.pi/count;xy.append((r*math.cos(a),r*math.sin(a)))
    from layout_cleanup import mm_mesh
    o=mm_mesh(name,manifold.CrossSection([xy]).extrude(z1-z0).translate([0,0,z0]))
    boolean(o,cyl('M2_thread_indication',(0,0,(z0+z1)/2),1,z1-z0+2,n=64))
    return o


def poses():
    hz=D['head_z'];tip=hz+P['belly_relayout']['yaw_output_tip_from_head_mm']
    # Local Z is the output axis, local X is the case length; no hardware scale.
    yaw=Matrix.Translation((0,0,tip+S['overall_with_spline_mm']))@Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Rotation(math.pi,4,'X')
    pitch=Matrix(((0,0,-1,S['pitch_output_tip_x_mm']+S['overall_with_spline_mm']),
                  (0,1,0,0),(1,0,0,hz),(0,0,0,1)))
    pitch=Matrix.Translation((0,0,hz))@Matrix.Rotation(math.radians(S['pitch_case_clock_deg']),4,'X')@Matrix.Translation((0,0,-hz))@pitch
    return {'Yaw':yaw,'Pitch':pitch}


def replace_servos():
    records=[]
    for axis,tr in poses().items():
        for kind,builder,group in [('Servo',canonical_case,'yaw'),('Output',canonical_output,'body' if axis=='Yaw' else 'pitch')]:
            name=axis+'_'+kind;remove_generated(name);o=builder(name);o.matrix_world=tr@o.matrix_world
            SOLIDS.pop(o.name,None);bpy.context.view_layer.update()
            finish(o,'PURCHASED_REFERENCE',f'SCS0009 {axis} '+('连续壳体与安装耳' if kind=='Servo' else '20T输出端 / 齿根形状示意'),
                   'metal',group,False,note='FEETECH A/0 p4/p6 drawing reconstruction. Bought revision, horn and thread engagement not measured.')
            o['model_fidelity']='DRAWING_RECONSTRUCTED_WITH_EXPLICIT_ASSUMPTIONS';o['dimension_source_ids']=['SCS0009_DRAWING']
            o['source_document']=S['source'];o['source_sha256']=S['source_sha256'];o['source_pages']='4,6'
            o['data_status']='ASSUMED';o['documented_fields']='Body drawing length,width,height; ear span,2mm holes,pitch,height; output OD,height,20T and M2x0.4 indication'
            o['unknown_dimensions']='Cosmetic fillets, cover seams, secondary cap, tooth root/profile and blind-thread depth; matching horn remains unselected.'
            if kind=='Servo':o['actuator_id']='head_'+axis.lower();o['documented_mass_g']=13.2
        holes=[list(tr@Vector((x,0,(S['ear_bottom_mm']+S['ear_top_mm'])/2))) for x in S['output_to_ear_hole_mm']]
        records.append({'axis':axis,'local_to_assembly_mm':list(map(list,tr)),
                        'output_tip_mm':list(tr@Vector((0,0,S['overall_with_spline_mm']))),
                        'output_direction':list(tr.to_3x3()@Vector((0,0,1))),
                        'ear_hole_centres_mm':holes,'ear_thickness_mm':S['ear_top_mm']-S['ear_bottom_mm'],
                        'case_group':'yaw','output_group':'body' if axis=='Yaw' else 'pitch'})
    return records


def ear_fastener(yoke,name,loc,axis='Z'):
    """Trial M2x5 from the accessible ear face into an integral blind seat."""
    b=source_build();m=S['mount'];p=Vector(loc);direction=Vector((0,0,1)) if axis=='Z' else Vector((1,0,0))
    ear=S['ear_top_mm']-S['ear_bottom_mm'];head_plane=p+direction*ear
    length=m['screw_length_mm'];insert_top=p-direction*m['insert_top_recess_mm'];insert_mid=insert_top-direction*m['insert_length_mm']/2
    hole_mid=p-direction*(length-ear+.3)/2
    boolean(yoke,cyl('servo_M2_blind_clear',hole_mid,m['M2_clearance_radius_mm'],length-ear+.6,axis,n=64))
    boolean(yoke,cyl('servo_insert_trial',insert_mid,m['insert_pilot_radius_mm'],m['insert_length_mm']+.2,axis,n=64))
    remove_generated(name+'_Screw');remove_generated(name+'_Nut');remove_generated(name+'_Insert')
    screw=cyl(name+'_Screw',head_plane-direction*length/2,.95,length,axis,n=48)
    union(screw,cyl('M2_head',head_plane+direction*.8,1.9,1.6,axis,n=64))
    hardware(screw,'M2×5 舵机安装耳螺钉 / 试配','yaw')
    insert=ring(name+'_Insert',insert_mid,m['insert_outer_radius_mm'],1.05,m['insert_length_mm'],axis,n=64)
    hardware(insert,'M2热熔嵌件 / 尺寸待实物及试打','yaw')
    for n in [name+'_Screw',name+'_Insert']:obj(n)['group']='yaw'
    b.contact(name+'_Screw',name+'_Insert','M2 trial threaded envelope; actual insert SKU, tightening and pullout NOT_TESTED')
    return {'id':name,'seat_plane_point_mm':list(p),'ear_top_point_mm':list(head_plane),'axis':axis,
            'insert_center_mm':list(insert_mid),'screw_length_mm':length,'insert_pilot_diameter_mm':m['insert_pilot_radius_mm']*2}


def yaw_pad_layout():
    """Seat faces are centered on documented ear holes, never the reverse."""
    m=S['mount'];c=S.get('centered_yaw_pads',{})
    case0=S['case_center_from_output_x_mm']-S['case_length_mm']/2
    case1=S['case_center_from_output_x_mm']+S['case_length_mm']/2
    rear,front=S['output_to_ear_hole_mm'];gap=m['ear_edge_clearance_mm']
    rear_half=case0-gap-rear;front_half=front-case1-gap
    if min(rear_half,front_half)<=m['insert_pilot_radius_mm']:
        raise ValueError('Documented servo ears leave insufficient material around insert pilot')
    top=(poses()['Yaw']@Vector((0,0,S['ear_top_mm']))).z
    rear0=m['yaw_rear_support_y_mm']-m['yaw_rear_support_depth_mm']/2
    if not c.get('enabled'):
        return {'rear_y_mm':[rear0,case0-gap],
                'front_y_mm':[m['yaw_front_support_y_min_mm'],m['yaw_front_support_y_max_mm']],
                'rear_arm_y_mm':[rear0,case0-gap],'seat_z_mm':top,'rear_arm_top_z_mm':top}
    return {'rear_y_mm':[rear-rear_half,rear+rear_half],
            'front_y_mm':[front-front_half,front+front_half],
            'rear_arm_y_mm':[rear0,case0-gap],'seat_z_mm':top,
            'rear_arm_top_z_mm':top-c['rear_arm_drop_mm']}


def rebuild_yoke():
    from head_cleanup import S as H
    o=obj('Pitch_Yoke');hz=D['head_z'];z0,z1=[hz+z for z in H['yoke_floor_z_from_head_mm']];m=S['mount'];pads=yaw_pad_layout()
    # Preserve the separate-load bearing journal/stops and thin shadow guard.
    # All old upper saddles and cable cuts are replaced by explicit plain solids.
    keep=cyl('retained_yaw_journal',(0,0,(100+z1)/2),H['journal_keep_radius_mm'],z1-100)
    guard=clone(o,'retained_shadow_guard');boolean(guard,sphere('exclude_old_upper_parts',(0,0,hz),H['guard_preserve_radius_mm']))
    clip_z(guard,-500,z1+2);union(keep,guard);intersect(o,keep)
    f=S.get('front_corner_cleanup',{})
    if f.get('enabled'):
        # The journal-preservation cylinder also retained a narrow slice of
        # the historical 12mm-wide front seat. Remove this obsolete corner
        # infill before rebuilding the original square web and 11mm post.
        # All lower journal/stops stay intact.
        # Include the old flange's thin outer arc beside the historical seat.
        # Overlap the future web volume to avoid coincident-plane slivers.
        overlap=f['cleanup_overlap_mm'];edge=H['floor_depth_mm']/2-overlap
        outer=pads['front_y_mm'][1]+1;low=z0-overlap
        boolean(o,box('remove_old_front_seat_lip',(0,(edge+outer)/2,(low+z1+1)/2),
                      (2*f['cleanup_half_width_mm'],outer-edge,z1+1-low)))
    union(o,plate('plain_load_web',[(-H['floor_lower_half_width_mm'],z0),(H['floor_lower_half_width_mm'],z0),
                    (H['floor_upper_half_width_mm'],z1),(-H['floor_upper_half_width_mm'],z1)],0,H['floor_depth_mm']))
    dep=P['structure']['simple_modules']['yoke_depth_mm'];th=P['structure']['simple_modules']['yoke_arm_thickness_mm']
    for sign in [-1,1]:
        top=hz+(m['pitch_left_wall_top_from_head_mm'] if sign<0 else 8.5)
        union(o,box('plain_bearing_cheek',(sign*39,0,(z1+top)/2),(th,dep,top-z1)))
    # Keep the actual bilateral bearing bores and existing mechanical pitch stops.
    for sign in [-1,1]:boolean(o,cyl('bearing_bore',(sign*39,0,hz),6.25,16,'X'))
    for angle in [-28,33]:
        ca=math.cos(math.radians(angle));sa=math.sin(math.radians(angle))
        union(o,box('pitch_stop',(39,-10*ca,hz-10*sa),(4,3,3)))
    boolean(o,cyl('reaction_upper_pass',(0,0,(hz-38.5+z1+1)/2),13.5,z1+1-(hz-38.5)))
    boolean(o,cyl('reaction_stem_pass',(0,0,(z0+hz-38.5)/2),P['belly_relayout']['reaction_stem_clearance_radius_mm'],hz-38.5-z0+.02))
    fasteners=[];tr=poses();yaw_plane=pads['seat_z_mm']
    pad_bottom=yaw_plane-m['yaw_pad_thickness_mm'];rear0,rear_end=pads['rear_arm_y_mm']
    arm_top=pads['rear_arm_top_z_mm'];arm_bottom=arm_top-m['yaw_pad_thickness_mm']
    # Current flat variant restores M1.31: one continuous rear pad/arm.
    # Keep the stepped variant only for reproducibility of the retired M1.32.
    union(o,box('yaw_rear_plain_arm',(0,(rear0+rear_end)/2,(arm_bottom+arm_top)/2),
                (m['yaw_pad_width_x_mm'],rear_end-rear0,arm_top-arm_bottom)))
    if S.get('centered_yaw_pads',{}).get('enabled'):
        ya,yb=pads['rear_y_mm']
        union(o,box('yaw_rear_centered_seat',(0,(ya+yb)/2,(pad_bottom+yaw_plane)/2),
                    (m['yaw_pad_width_x_mm'],yb-ya,yaw_plane-pad_bottom)))
    union(o,box('yaw_rear_plain_web',(0,m['yaw_rear_support_y_mm'],(z1+arm_bottom+.1)/2),
                (m['yaw_pad_width_x_mm'],m['yaw_rear_support_depth_mm'],arm_bottom+.1-z1)))
    ya,yb=pads['front_y_mm']
    union(o,box('yaw_front_plain_post',(0,(ya+yb)/2,(z0+yaw_plane)/2),
                (m['yaw_pad_width_x_mm'],yb-ya,yaw_plane-z0)))
    for i,y in enumerate(S['output_to_ear_hole_mm']):fasteners.append(ear_fastener(o,'Head_Yaw_Ear_'+str(i),(0,y,yaw_plane)))
    pitch_seat_x=(tr['Pitch']@Vector((0,0,S['ear_top_mm']))).x
    for i,x in enumerate(S['output_to_ear_hole_mm']):
        center=tr['Pitch']@Vector((x,0,(S['ear_bottom_mm']+S['ear_top_mm'])/2));z=center.z
        union(o,box('pitch_integral_ear_seat',((-36+pitch_seat_x)/2,0,z),
                    (pitch_seat_x+36,m['pitch_ear_seat_half_width_y_mm']*2,m['pitch_ear_seat_half_height_mm']*2)))
        fasteners.append(ear_fastener(o,'Head_Pitch_Ear_'+str(i),(pitch_seat_x,0,z),'X'))
    module(o,'简洁双轴U托 / 四处舵机安装耳座','yaw','Print side orientation requires slicer review; test insert and bearing coupons first',
           'Continuous load web, bilateral bearings and compact flat seats. Four M2x5 trial ear fasteners. No preliminary cable bores, clip or swept cable cuts.',(0,-35,80))
    o['head_servo_revision']=P['revision'];o['integrated_features']='Bilateral bearings + four plain servo seats + existing yaw journal/stops; no head wiring holes'
    return fasteners


def defer_routes():
    if not P.get('head_routing',{}).get('hide_provisional_routes'):return
    for o in list(bpy.context.scene.objects):
        if o.get('role')=='routing':
            o['previous_role']='routing';o['role']='deferred_routing';o['verification_status']='NOT_TESTED_DEFERRED_BY_USER'
            o['export_candidate']=False;move_collection(o,'DATUMS');o.hide_render=True


def apply_head_servo_detail():
    if not S.get('enabled'):return
    motors=replace_servos();seats=rebuild_yoke();defer_routes()
    b=source_build();alive={o.name.removeprefix(PREFIX) for o in parts()}
    b.CONTACTS[:]=[c for c in b.CONTACTS if c['a'] in alive and c['b'] in alive]
    for n in ['Yaw_Servo','Pitch_Servo']:b.contact(n,'Pitch_Yoke','Two documented mounting ears seated on integral plain pads; actual insert retention pending trial')
    save_json(ROOT/'reports/head_servo_geometry.json',{'revision':P['revision'],'status':'GENERATED_PENDING_VALIDATION','source':S['source'],
                'motors':motors,'mounts':seats,'documented':{k:S[k] for k in ['case_length_mm','case_width_mm','ear_bottom_mm','ear_top_mm','ear_hole_diameter_mm','output_to_ear_hole_mm','spline_outer_diameter_mm']},
                'yaw_seat_layout':yaw_pad_layout(),
                'unknowns':S['unknowns'],'routing_status':'NOT_TESTED_DEFERRED_BY_USER','new_print_parts':0})
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text())
    plan['head_servo_installation']='Fit trial M2 inserts to four plain seats. With optical/pitch head and yaw servo absent, seat and fix the180deg-clocked pitch case through both real ears. Fit the yaw servo with output down, then its two ear screws. Load is carried by bilateral pitch bearings and yaw bearing. Horn engagement/zero, insert fits and torque require real units.'
    plan['routing_status']='Deferred by user. Old routing previews hidden; preliminary head wire cuts and guide removed. No cable clearance or strain-relief qualification.'
    save_json(ROOT/'reports/module_assembly.json',plan)
    print('HEAD_SERVO_DETAIL_COMPLETE',flush=True)
