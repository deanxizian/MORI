"""M1.12 mechanical cleanup. Native PCB references are frozen P2, not P3 release.
All printed changes are own-namespace geometry; hardware projects stay read-only.
"""
from common import *
from optics_mount import display_transform,camera_transform,apply_mount
from monocoque_structure import obj,source_build,reserve
from purchased_geometry import remove_generated,finish_reference
from belly_relayout import erase_prefix
from simple_modules import module
from structural_simplification import hardware,volume

S=P.get('layout_cleanup',{})
ROUTE_PATHS={}

def mm_mesh(name,m):
    d=m.to_mesh64();return mesh(name,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist())

def native_assembly(name,cache,rotation,translation,label):
    """Visible original triangles, double-precision collision solid in owned cache."""
    verts=[];faces=[];ms=[];fallback=[]
    comps=cache.get('components',[{'reference':'vendor','solids':cache.get('solids',[])}])
    r=np.array(rotation);t=np.array(translation)
    for c in comps:
        for i,s in enumerate(c['solids']):
            v=np.array(s['vertices_mm'])@r.T+t;f=np.array(s['triangles'],dtype=np.uint64)
            m=manifold.Manifold(manifold.Mesh64(v,f))
            if m.status()!=manifold.Error.NoError:
                lo=v.min(0)-.001;hi=v.max(0)+.001;m=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist());fallback.append([c['reference'],i])
            ms.append(m);faces.extend((f+len(verts)).tolist());verts.extend(v.tolist())
    total=manifold.Manifold.batch_boolean(ms,manifold.OpType.Add)
    assert total.status()==manifold.Error.NoError,(name,total.status())
    proxy=mm_mesh(name+'_Proxy',total);finish(proxy,'KEEP_OUT',label+'检查代理','keepout','body',False,role='validation_proxy')
    data=total.to_mesh64();path=ROOT/'reports'/('solid_'+name+'.json')
    save_json(path,{'vertices_mm':data.vert_properties[:,:3].tolist(),'triangles':data.tri_verts.tolist(),'coordinate_frame':'assembly zero in mm','fallbacks':fallback})
    o=mesh(name,verts,faces);finish_reference(o,label,'NATIVE_PCB_LIBRARY_CAD',['NATIVE_P2'],'body','pcb')
    o['preserve_vendor_tessellation']=True;o['validation_proxy']=proxy.name;o['validation_solid_source']=str(path.relative_to(PROJECT));o['source_scale_factor']=1.
    o['data_status']='ASSUMED';o['model_fidelity']='NATIVE_DESIGN_LIBRARY_CAD_NOT_AS_BUILT';o['source_revision']='P2 snapshot; P3 requires new handoff'
    return o,total

def tilt_optics():
    tr=display_transform();ct=camera_transform();hz=D['head_z'];old=obj('Display_Frame')
    for n in ['Face_Mask','Face_Protector','Display_PCB','Display_Collision_Proxy','LCD35079_Original_CAD','Display_Outline_Allocation','Eye_L','Eye_R']:
        if bpy.data.objects.get(PREFIX+n):apply_mount(obj(n),tr)
    for n in ['Camera_PCB','Camera_Lens','Camera_Window','Camera_Baffle']:
        apply_mount(obj(n),ct)
    # Keep the structural fork vertical; retain its short side attachments.
    ears=[]
    for sign in [-1,1]:
        e=clone(old,'fork_side_ear');intersect(e,box('retain_ear',(sign*50,22,hz-1),(25,30,34)));ears.append(e)
    remove_generated('Display_Frame')
    fy=29.0;o=box('Display_Frame',(0,fy,hz-6),(64,3,8))
    holes=INTERFACES['components']['display']['vendor_dimensions']['cad_post_center_xz_from_screen_mm']
    for x,z in holes:
        point=tr@Vector((x,40.1,hz+z));base=Vector((x,fy,point.z))
        union(o,box('vertical_LCD_rail',(x,fy,(hz-6+point.z)/2),(7,3,abs(point.z-(hz-6))+7)))
        # Short orthogonal block to a tilted bearing face, no long connecting rod.
        depth=max(.1,point.y-fy+1.5);seat=box('LCD_seat',(x,fy+depth/2-1.5,point.z),(7,depth,7))
        # Plane at the true original post tips, rearward material only.
        half=box('seat_front_plane',(x,40.1+50,hz+z),(20,100,30));apply_mount(half,tr);boolean(seat,half)
        union(o,seat)
        bore=cyl('LCD_trial_M2',(x,38,hz+z),1.2,24,'Y');apply_mount(bore,tr);boolean(o,bore)
    for sign,e in zip([-1,1],ears):
        union(o,box('fork_short_return',(sign*36,31,hz-5),(14,7,24)));union(o,e)
    cb=np.array(bounds(obj('Camera_PCB')));cy=float(cb[1,0])-.8;cz=(cb[2,0]+cb[2,1])/2
    union(o,box('camera_vertical_tongue',(0,fy,(hz+21+cz)/2),(14,3,cz-hz-21+8)))
    union(o,box('camera_short_seat',(0,(fy+cy)/2,cz),(16,abs(cy-fy)+3,10)))
    for n in ['Camera_PCB','Camera_Lens','Camera_Baffle']:boolean(o,reserve('camera_seat_clear',obj(n),.3))
    for n in ['Head_Front','Head_Rear','Pitch_Cradle','Display_Collision_Proxy']:boolean(o,clone(obj(n),'fork_mating_clear'))
    module(o,'直立屏幕叉架 / 局部10°安装面','pitch','Rear planar rails on bed; short seat overhangs need slicer review','Upright structural rails; only LCD seat faces tilted. Three source CAD post positions retained; four accessible side joints allow bench fitting.',(0,85,80))
    # Cable starts move with their attached optical hardware, continuation stays in the level frame.
    for name,pts in [('Screen_Lead',[tr@Vector((0,39,hz-23)),Vector((15,32,hz-20)),Vector((25,26,hz-14)),Vector((25,-10,hz-11)),Vector((22,-15,hz-9))]),('Camera_Lead',[ct@(Vector(P['camera']['body_center_from_head_mm'])+Vector((7,-1.7,hz+5))),Vector((19,19,hz+37)),Vector((24,-16,hz+24))])]:
        route(name,pts,'pitch')
    save_json(ROOT/'reports/optical_mounts.json',{'head_default_pitch_deg':0,'head_bottom_cut_plane_z_mm':hz+P['head_lower_opening_z_from_center_mm'], 'screen_fixed_mount_pitch_deg':S['display_mount_pitch_deg'],'camera_fixed_mount_pitch_deg':S['camera_mount_pitch_deg'],'display_rigid_transform':list(map(list,tr)),'camera_rigid_transform':list(map(list,ct)),'geometry_scaled':False,'main_frame_axes':'unchanged; horizontal/vertical','screen_active_center_mm':list(tr@Vector((0,P['display']['vendor_front_y_from_head_mm'],hz)))})

def route(name,pts,group='body',r=1.2):
    remove_generated(name);b=source_build();o=None
    ROUTE_PATHS[name]=([list(v) for v in pts],r)
    for a,c in zip(pts,pts[1:]):
        w=b.beam('route_segment',a,c,r)
        if o is None:o=w
        else:union(o,w)
    o.name=PREFIX+name;finish(o,'PLACEHOLDER',name+' 有限线束空间','copper',group,False,role='routing');o['model_fidelity']='ROUTING_ALLOCATION_NOT_REAL_CABLE'

def new_deck():
    dz=P['layout']['deck_z_mm'];t=P['layout']['deck_thickness_mm'];top=dz+t/2
    # Symmetric deliberate outline. No accidental square bites around wheels.
    poly=S['frame_outline_xy_mm']
    m=manifold.CrossSection([poly]).extrude(t).translate([0,0,dz-t/2]);o=mm_mesh('Load_Frame_New',m)
    boolean(o,cyl('speaker_service_arc',(*S['frame_speaker_clear_center_xy_mm'],dz),S['frame_speaker_clear_radius_mm'],t+2))
    # The whole outline clears the inner wheel pocket. Do not carve a curved
    # wheel/shell bite into the underside of the plate.
    # Preserve short shell seating and screw passages from the prior same datum.
    for x,y in P['shell_service']['frame_mount_xy_mm']:boolean(o,cyl('shell_M3_clear',(x,y,dz),1.7,t+12))
    for side in ['L','R']:
        cheek=obj('Body_Cheek_'+side)
        # Fill the now-redundant deck joint holes; keep lower wheel-drive joints.
        sign=-1 if side=='L' else 1
        for yy in [-8,8]:
            union(cheek,cyl('filled_old_deck_hole',(sign*P['structure']['simple_modules']['frame_joint_abs_x_mm'],yy,109.5),1.3,3))
        union(o,clone(cheek,'integral_short_side'))
        # Broad overlapping corner fillet/web; planar, no slender posts.
        ss=P['structure']['simple_modules']
        union(o,box('continuous_corner',(sign*ss['side_plate_abs_x_mm'],0,110.8),(ss['side_plate_thickness_mm'],26,1)))
    for n in ['Load_Frame','Body_Cheek_L','Body_Cheek_R','Power_Board_Carrier']:remove_generated(n)
    erase_prefix('Deck_');erase_prefix('Power_Carrier_')
    o.name=PREFIX+'Load_Frame';module(o,'主托板与两侧短板一体 / 平面轮廓','body','Candidate: broad side face toward bed with brim; compare inverted deck orientation. Opposed PCB bosses and short side legs require limited supports; no slicing claim.','Shared rigid electronics datum and short wheel-load sides. Four lower drive joints retained; four deck and four carrier screw/nut pairs removed.',(0,-70,-10))
    import yaw_bridge_mount
    if yaw_bridge_mount.S.get('enabled'):
        yaw_bridge_mount.deck_holes(o)
    else:
        for sign in [-1,1]:
            boolean(o,cyl('YawBase_M2_clear',(sign*49,0,dz),1.2,12))
            boolean(o,reserve('YawBase_captive_nut',obj('Yaw_Base_'+str(sign)+'_Nut'),.15))
    # Remove old rectangular chip seats; native boards use local short bosses.
    return o

def boards_and_bay(deck):
    remove_generated('Body_IMU');remove_generated('MCU_Motion');remove_generated('WeAct_Collision_Proxy')
    im=S['imu'];r=np.diag([1.,-1.,-1.]);t=np.array([*im['center_xy_mm'],im['pcb_reference_z_mm']])-r@np.array([10,-8,0.])
    cache=json.loads((PROJECT/im['native_mesh']).read_text());imu,imsolid=native_assembly('Body_IMU',cache,r,t,'IMU P2 原生20×16 / 器件朝下');imu['mounting_frame']='Load_Frame underside; PCB top normal -Z'
    for i,(x,y) in enumerate(im['mounting_holes_native_xy_mm']):
        p=r@np.array([x,-y,0])+t;x,y,z=p
        union(deck,cyl('integral_imu_boss',(x,y,(z+111.3)/2),3.3,111.3-z))
        boolean(deck,cyl('imu_trial_pilot',(x,y,110.3),1.6,4.0))
        hardware(ring('IMU_Insert_'+str(i),(x,y,110),1.5,1.05,3.2),'IMU试配M2短嵌件')
        bolt=cyl('IMU_Screw_'+str(i),(x,y,109.2),.95,6)
        union(bolt,cyl('head',(x,y,105.45),1.9,1.5));hardware(bolt,'IMU底面M2试配 / 无独立螺母')
    socket=box('IMU_Plug_Reserve',(-25,-44.5,97.6),(14,7,10));finish(socket,'KEEP_OUT','IMU插头向下10mm空间 / 选型待核','keepout','body',False,role='keepout')
    route('IMU_Lead',im['lead_points_mm'],r=1)
    # Actual P2 populated carrier, not the previously detached core-board box.
    mp=S['motion_carrier'];center=np.array([*mp['center_xy_mm'],mp['pcb_reference_z_mm']]);cache=json.loads((PROJECT/mp['native_mesh']).read_text())
    carrier,cs=native_assembly('MCU_Carrier',cache,np.eye(3),center-np.array([35,-17.5,0]),'Motion 基板P2 / 原生70×35');carrier['documented_mass_g']=12
    wc=json.loads((PROJECT/P['detail_fit']['weact_mesh']).read_text());wr=np.array([[0,-1,0],[-1,0,0],[0,0,-1.]])
    wt=center+np.array([61.016,116.078,1.595+mp['core_socket_height_assumed_mm']])
    core,ws=native_assembly('MCU_Motion',wc,wr,wt,'WeAct V1.1 原厂CAD / 基板插接朝向');core['source_sha256']=wc['source_sha256']
    for x in [-32.5,32.5]:
        for y in [-59,-29]:
            union(deck,cyl('carrier_short_boss',(x,y,118),3.2,6));boolean(deck,cyl('carrier_trial_M2',(x,y,118.8),1.6,4.5))
    # Hole geometry follows the native P2 carrier. Fasteners are not frozen for P3.
    for i,(x,y) in enumerate([(x,y) for x in [-32.5,32.5] for y in [-59,-29]]):
        hardware(ring('Carrier_Insert_'+str(i),(x,y,118.8),1.5,1.05,3.8),'基板M2试配嵌件');bolt=cyl('Carrier_Screw_'+str(i),(x,y,120),.95,6);union(bolt,cyl('head',(x,y,123.6),1.9,1.5));hardware(bolt,'P2基板M2试配 / P3交接复核')
    # Only the selected core geometry is exact; sockets are visible allocations.
    o=box('MCU_Socket_Reserve',(center[0]-8.2,center[1],center[2]+1.595+3),(41.6,33.22,6))
    finish(o,'KEEP_OUT','排母6mm假设 / 选型与插深待核','keepout','body',False,role='keepout')
    # Adopt the existing capacity study, not a fabricated completed power PCB.
    pw=S['power_bay'];remove_generated('Power_Module');x,y=pw['center_xy_mm'];z=pw['pcb_bottom_z_mm']
    low=z-pw['component_below_mm'];high=z+pw['nominal_pcb_thickness_mm']+pw['component_above_mm']
    o=box('Power_Module',(x,y,(low+high)/2),(*pw['max_pcb_xy_mm'],high-low));finish(o,'PLACEHOLDER','电源板80×55安装总包络 / 非完整装件CAD','unknown','body',False)
    o['documented_mass_g']=30
    from power_board_mount import build_mount
    build_mount(deck,o)
    route('Head_Trunk',[[-45,28,137],[-42+70/22,25-105/22,144],[-32,10,159],[-22,0,153]])
    info=json.loads((ROOT/'reports/vendor_weact_import.json').read_text());info.update(imported_bounds_xyz_mm=bounds(core),destination_board_top_datum_mm=center.tolist(),carrier_stack='P2 native carrier integrated;6mm socket is an unselected allocation',collision_method='Original224 CAD solids; exact double precision union plus declared per-solid fallback. Render meshes unscaled.');save_json(ROOT/'reports/vendor_weact_import.json',info)
    save_json(ROOT/'reports/imu_mount_transform.json',{'native_board_revision':'P2','native_pcb_xy_mm':[20,16],'native_to_assembly_rotation':r.tolist(),'native_to_assembly_translation_mm':t.tolist(),'PCB_front_normal_body':[0,0,-1],'board_axes_in_body':{'X':[1,0,0],'Y_step':[0,-1,0],'Z':[0,0,-1]},'IMU_sensor_to_PCB_axes':'Use P3 footprint orientation and ICM-42688-P axis drawing; board transform is not firmware sensor-axis calibration','components_face':'down','mount':'two short bosses integral with Load_Frame; two M2 trial screws','no_foam_mount':True,'source':im['native_mesh'],'cable_allocation':'IMU_Plug_Reserve + IMU_Lead; mating plug SKU and vibration response NOT_TESTED'})

def rear_interface():
    b=source_build();q=S['interface_pcb'];center=Vector(q['pcb_center_mm']);w,d=q['pcb_xy_mm'];z=center.z
    for n in ['Function_Button','Button_Cap','USB_Charge','USB_Charge_Mount','Power_Switch','USB_Receptacle']:remove_generated(n)
    pcb=box('Rear_Interface_PCB',center,(w,d,q['thickness_mm']))
    for x,y in q['holes_xy_local_mm']:boolean(pcb,cyl('PCB_M2',(center.x+x,center.y+y,z),1.1,5))
    finish(pcb,'PLACEHOLDER','后接口板24×14提案 / 电路另任务设计','unknown','body',False);pcb['model_fidelity']='MECHANICAL_BOARD_REQUIREMENT_NOT_ELECTRICAL_DESIGN'
    shell=obj('Body_Upper')
    # Two broad ledges grow directly from rear shell. Screw heads face down for access through the detached shell bottom.
    for i,(x,y) in enumerate(q['holes_xy_local_mm']):
        xx=center.x+x;yy=center.y+y
        foot=box('rear_integral_ledge',(xx,-67,(115.8+120)/2),(7,19,4.2));intersect(foot,b.body_outer('shell_outer_limit'));union(shell,foot)
        boolean(shell,cyl('interface_M2_pilot',(xx,yy,118),1.6,4.5))
        hardware(ring('Rear_Interface_Insert_'+str(i),(xx,yy,117.85),1.5,1.05,3.8),'接口板M2试配嵌件')
        screw=cyl('Rear_Interface_Screw_'+str(i),(xx,yy,116.7),.95,6)
        union(screw,cyl('head',(xx,yy,113.45),1.9,1.5));hardware(screw,'接口板M2试配 / 外壳一体安装座')
    # These are connector requirements, deliberately not selected-part CAD.
    sw=box('Power_Switch',(0,-69.5,119.8),(10,9,8))
    union(sw,box('switch_actuator',(0,-75,123),(8,4,3)))
    finish(sw,'PLACEHOLDER','顶面侧拨电源/禁驱开关包络 / 型号待选','unknown','body',False);sw['model_fidelity']='CONNECTOR_REQUIREMENT_ENVELOPE'
    usb=box('USB_Receptacle',(0,-74,112),(10,10,4.4),.3);boolean(usb,box('USB_open',(0,-78,112),(8.4,5,2.6),.2))
    finish(usb,'PLACEHOLDER','底面侧出USB-C包络 / 型号待选','metal','body',False);usb['model_fidelity']='CONNECTOR_REQUIREMENT_ENVELOPE'
    # The two ledges flank all connector bodies and solder zones.
    for n in ['Power_Switch','USB_Receptacle']:boolean(shell,reserve('interface_clear',obj(n),.5))
    # No connector overlap with bare board: contact is at top/bottom faces.
    route('Interface_Lead',q['inner_cable_points_mm'],r=1)
    save_json(ROOT/'reports/rear_interface_geometry.json',{'revision':P['revision'],'status':'MECHANICAL_REQUIREMENTS_ONLY','PCB':bounds(pcb),'shell_integral_mounts':2,'new_printed_brackets':0,'fasteners':2,'screw_access_direction':'-Z, through open underside of detached upper shell','board_top_z_mm':115.8,'board_bottom_z_mm':114.2,'USB_axis_z_mm':112,'switch_actuator_axis_z_mm':123,'USB_and_switch_toward':'-Y rear','limits':['Exact SMT/through-hole parts must be chosen for these side exits; generic board-face flip alone does not align ports','Simultaneous finger access while USB plugged in NOT_TESTED','Board thickness, mounting pilots and enclosure fit require coupon and real connectors','No charger or high-current circuit design implied']})

def apply_layout_cleanup():
    if not S.get('enabled'):return
    before={o.name.removeprefix(PREFIX):{'category':o.get('category'),'is_screw':o.name.endswith('_Screw') or '_Screw_' in o.name} for o in parts()}
    tilt_optics();deck=new_deck();boards_and_bay(deck);rear_interface()
    for poly in deck.data.polygons:poly.use_smooth=False
    # The interface ledges and new deck overlap their working region only at
    # an explicit service notch; it is a rounded rear connector clearance.
    boolean(deck,box('rear_connector_clear',S['frame_rear_cut_center_mm'],S['frame_rear_cut_xyz_mm'],2))
    b=source_build()
    for cable,target in [('Screen_Lead','Display_Frame'),('Camera_Lead','Display_Frame'),('IMU_Lead','Load_Frame')]:
        pts,r=ROUTE_PATHS[cable]
        for a,c in zip(pts,pts[1:]):boolean(obj(target),b.beam('dedicated_wire_passage',a,c,r+.6))
    for poly in deck.data.polygons:poly.use_smooth=False
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text());plan['revision']=P['revision']
    plan['joints']=[j for j in plan['joints'] if not j['id'].startswith(('Deck_','Power_Carrier_'))]
    for j in plan['joints']:
        if j['upper'].startswith('Body_Cheek'):j['upper']='Load_Frame'
        if j['lower'].startswith('Body_Cheek'):j['lower']='Load_Frame'
    plan['merged_same_body_parts']=['Load_Frame + Body_Cheek_L + Body_Cheek_R','Power_Board_Carrier replaced by four short integral seats at received P4 holes','IMU and rear-interface mounts integral to Load_Frame / Body_Upper']
    plan['power_board_assembly']='Install power board on four integral seats and fit two diagonal M2x6 screws before fixed yaw bridge/head; remove bridge/head and upper shell for service. P5 and populated keepouts pending.'
    plan['retained_service_splits']=['Drive_Bridge vs Load_Frame: wheel-drive installation','Yaw_Base vs Load_Frame: bearing and reaction-link installation','Display_Frame vs Pitch_Cradle: LCD rear-post screws and camera bench assembly','Speaker vs Body_Upper: direct vendor ears, trial gasket and two shell-side screws; no printed rear cover']
    save_json(ROOT/'reports/module_assembly.json',plan)
    changes=json.loads((ROOT/'reports/structure_changes.json').read_text());mods={o.name.removeprefix(PREFIX):o for o in parts() if o.get('simple_support_module')}
    changes.update(revision=P['revision'],after={n:{'volume_mm3':volume(o),'bounds_xyz_mm':bounds(o)} for n,o in mods.items()},support_printed_parts_after=len(mods),new_integral_bodies=list(mods));save_json(ROOT/'reports/structure_changes.json',changes)
    after={o.name.removeprefix(PREFIX):o.get('category') for o in parts()}
    save_json(ROOT/'reports/layout_cleanup_changes.json',{'revision':P['revision'],'removed':sorted(set(before)-set(after)),'added':sorted(set(after)-set(before)),'printed_parts_before':sum(x['category']=='PRINTABLE' for x in before.values()),'printed_parts_after':sum(x=='PRINTABLE' for x in after.values()),'removed_structural_screw_nut_pairs':8,'new_PCB_trial_screws':10,'new_rear_interface_brackets':0,'native_PCBS':'P2 motion/IMU placement reference; P4 power holes only; full populated/mated fit incomplete, P5 in progress','print_release':False})
    info=json.loads((ROOT/'reports/detail_fit_geometry.json').read_text());info['selected_geometry']={n:bounds(obj(n)) for n in info['selected_geometry'] if bpy.data.objects.get(PREFIX+n)};info['external_function_button']=False;info['limits']=['P3 populated CAD and real connector matching pending','CAM/lens/FPC are partial-dimension allocations','Head zero level; fixed screen/camera tilt10deg'];save_json(ROOT/'reports/detail_fit_geometry.json',info)
    lcd=json.loads((ROOT/'reports/vendor_lcd_import.json').read_text());lcd['imported_bounds_xyz_mm']=bounds(obj('Display_PCB'));lcd['fixed_optics_transform_mm']=[list(r) for r in display_transform()];save_json(ROOT/'reports/vendor_lcd_import.json',lcd)
    print('LAYOUT_CLEANUP_COMPLETE',flush=True)
