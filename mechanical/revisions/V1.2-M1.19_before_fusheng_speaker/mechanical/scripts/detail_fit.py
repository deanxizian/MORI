"""M1.10: local mounts and source-backed purchased geometry.

No electrical BOM is rewritten. Nominal drawings, exact CAD and photo estimates
are explicitly different evidence classes. All transforms preserve millimetres.
"""
from common import *
from monocoque_structure import obj, reserve, source_build
from purchased_geometry import remove_generated, finish_reference
from structural_simplification import hardware, volume
from simple_modules import module
from belly_relayout import relocate


def assumed(o,label,group='pitch',mat='unknown',fidelity='ALLOCATION_ONLY'):
    finish(o,'PLACEHOLDER',label,mat,group,False)
    o['model_fidelity']=fidelity;o['measured_unit']=False;o['mounting_release']=False
    return o


def flat_strip(name,a,b,width=7,depth=2.4):
    a,b=Vector(a),Vector(b);o=box(name,(a+b)/2,(width,depth,(b-a).length+width))
    direction=b-a;o.rotation_euler.y=math.atan2(direction.x,direction.z)
    bpy.context.view_layer.update();return o


def screen_fork():
    hz=D['head_z'];old=obj('Display_Frame');fy=36.2
    # Retain the existing four accessible side-screw interfaces, not the ring.
    ears=[]
    for sign in [-1,1]:
        e=clone(old,'retained_short_ear')
        intersect(e,box('ear_only',(sign*55,20,hz),(48,80,35)))
        ears.append(e)
    remove_generated('Display_Frame')
    o=box('Display_Frame',(0,fy,hz-12),(64,2.4,7))
    holes=INTERFACES['components']['display']['vendor_dimensions']['cad_post_center_xz_from_screen_mm']
    for x,z in holes:
        union(o,flat_strip('short_flat_fork',(x,fy,hz+z),(x,fy,hz-12),6,2.4))
        union(o,cyl('LCD_post_seat',(x,38.15,hz+z),3.4,3.9,'Y'))
        boolean(o,cyl('trial_LCD_M2_clear',(x,38,hz+z),1.2,14,'Y'))
    for sign,e in zip([-1,1],ears):
        union(o,box('side_step',(sign*31.5,37,hz-4.5),(7,4,22)))
        union(o,e)
    # Short, wide camera tongue, separate aperture from the display.
    cy=P['camera']['body_center_from_head_mm'][1]-2.6
    cz=hz+P['camera']['body_center_from_head_mm'][2]
    union(o,box('camera_tongue',(0,fy,(hz+21+cz+6)/2),(12,2.4,cz+6-hz-21)))
    union(o,box('camera_seat_step',(0,(fy+cy)/2,cz),(16,fy-cy+2.4,8)))
    boolean(o,reserve('camera_package_clear',obj('Camera_PCB'),.25))
    boolean(o,reserve('camera_lens_clear',obj('Camera_Lens'),.25))
    for n in ['Head_Front','Head_Rear','Pitch_Cradle','Display_Collision_Proxy']:
        boolean(o,clone(obj(n),'interface_relief'))
    module(o,'三点屏幕叉架 / 平条与短侧耳','pitch','Rear flat face down; inspect the short stepped seats',
           'Three original M2 post seats plus four existing accessible side screws. Full circular rear ring removed. Camera tongue is only a provisional package seat.',(0,85,80))
    # Camera lead now follows a gap beside the fork, instead of cutting the ring.
    remove_generated('Camera_Lead');b=source_build();q=None
    pts=[(7,31,hz+40),(19,27,hz+36),(24,-16,hz+24)]
    for a,bb in zip(pts,pts[1:]):
        w=b.beam('cam_wire',a,bb,1.2)
        if q is None:q=w
        else:union(q,w)
    q.name=PREFIX+'Camera_Lead';finish(q,'PLACEHOLDER','相机排线路径 / 长度弯曲待核','copper','pitch',False,role='routing')


def shell_speaker():
    s=P['detail_fit']['speaker'];b=source_build();bz=D['body_z']
    tidy=P.get('fastener_cleanup',{});sm=tidy.get('speaker') if tidy.get('enabled') else None
    def cup_outline(name,y,depth):
        o=cyl(name,(0,y,0),sm['outer_half_height_z_mm'],depth,'Y')
        o.scale.x=sm['outer_half_width_x_mm']/sm['outer_half_height_z_mm'];bpy.context.view_layer.update()
        return o
    # Work in a local speaker system: +Y outward, front mounting face Y=0.
    tr=Matrix.Translation((0,0,bz))@Matrix.Rotation(math.radians(s['radial_pitch_deg']),4,'X')@Matrix.Translation((0,s['front_radius_from_body_mm'],0))
    for name in ['Speaker','Speaker_Mount','Speaker_Lead']:remove_generated(name)
    sp=cyl('Speaker',(0,-.85,0),20,1.7,'Y')
    # Undimensioned basket taper is conservatively represented by its full OD;
    # back magnet OD23 and axial steps come directly from the dimensioned PDF.
    union(sp,cyl('speaker_basket_envelope',(0,-6.5,0),19.7,9.6,'Y'))
    union(sp,cyl('speaker_magnet',(0,-14.4,0),11.5,6.2,'Y'))
    finish_reference(sp,'CMS-4017-34SP / Ø40×17.5 / 4Ω3W','VENDOR_DIMENSIONED_ENVELOPE',['CMS4017_DRAWING'],'body','dark')
    sp['documented_mass_g']=25;sp['envelope_limit']='Basket taper and solder-tab positions not dimensioned; full OD retained conservatively. PDF tolerance +/-0.3mm; no invented mounting holes.'
    relocate(sp,tr)
    # Gasket and shell socket: front of the gasket Y=1.2, giving >=0.8mm
    # diaphragm excursion space. Socket joins the actual body shell perimeter.
    gasket=ring('Speaker_Gasket',(0,.6,0),19.4,18,1.2,'Y')
    finish_reference(gasket,'扬声器原厂垫圈 / Ø38.8–36×1.2','VENDOR_DIMENSIONED_ENVELOPE',['CMS4017_DRAWING'],'body','tire');relocate(gasket,tr)
    socket=ring('shell_speaker_seat',(0,3.8,0),22,17.8,5.2,'Y')
    relocate(socket,tr);intersect(socket,b.body_outer('speaker_socket_outer_limit'))
    upper=obj('Body_Upper');union(upper,socket)
    # Rear cup captures the flange. Two screws attach it only to shell
    # bosses. No bracket, bolt or acoustic chamber is attached to Load_Frame.
    if sm:
        cup=cup_outline('Speaker_Mount',-10.3,20.6)
        boolean(cup,cyl('continuous_cup_cavity',(0,-10.3,0),sm['inner_radius_mm'],22,'Y'))
    else:cup=ring('Speaker_Mount',(0,-10.3,0),22,20.6,20.6,'Y')
    union(cup,ring('flange_retaining_lip',(0,-2.2,0),22,19.85,1,'Y'))
    if sm:union(cup,cup_outline('acoustic_back',(sm['back_outer_y_mm']+sm['back_inner_y_mm'])/2,sm['back_inner_y_mm']-sm['back_outer_y_mm']))
    else:union(cup,cyl('acoustic_back',(0,-21.2,0),22,1.8,'Y'))
    for sign in [-1,1]:
        if not sm:union(cup,box('shell_ear',(sign*25,-3.5,0),(8,3,9)))
        by0,by1=sm['shell_boss_y_limits_mm'] if sm else [-2,4]
        boss=cyl('shell_speaker_boss',(sign*24,(by0+by1)/2,0),4.6,by1-by0,'Y');relocate(boss,tr)
        intersect(boss,b.body_outer('boss_outer_limit'));union(upper,boss)
        bore=cyl('shell_speaker_trial',(sign*24,-12,0),1.2,36,'Y');boolean(cup,clone(bore,'ear_clear'))
        bpy.data.objects.remove(bore,do_unlink=True)
        # Screw heads are accessible after lifting off the upper shell.
        head=sm['screw_head_base_y_mm'] if sm else -5;length=sm['screw_length_mm'] if sm else 6
        bolt=cyl('Speaker_Screw_'+str(sign),(sign*24,head+length/2,0),.95,length,'Y')
        union(bolt,cyl('speaker_bolt_head',(sign*24,head-.8,0),1.9,1.6,'Y'))
        hardware(bolt,f'扬声器后盖试配M2×{length:g} / 壳体内侧盲孔','body');relocate(bolt,tr)
        # Blind insert seat follows the selected local limits and keeps the
        # exterior shell closed; no fastener opens through the front surface.
        py0,py1=sm['pilot_y_limits_mm'] if sm else [-2.4,1.8]
        seat=cyl('insert_pilot',(sign*24,(py0+py1)/2,0),1.6,py1-py0,'Y');relocate(seat,tr);boolean(upper,seat)
        insert=ring('Speaker_Insert_'+str(sign),(sign*24,sm['insert_center_y_mm'] if sm else -.1,0),1.5,1.1,3.8,'Y');hardware(insert,'扬声器壳体M2试配嵌件','body');relocate(insert,tr)
        if sm:
            # Overrun both ends of the shell pilot by 0.2 mm. Coincident end
            # planes leave zero-thickness slivers when the shell boss is cut
            # out of the cup; the insert also needs axial assembly clearance.
            cy0,cy1=py0-.2,py1+.2
            boolean(cup,cyl('cup_insert_endpoint_clear',(sign*24,(cy0+cy1)/2,0),1.65,cy1-cy0,'Y'))
    # Current design uses only rear head counterbores within the oval outline.
    for side in [-1,1]:
        if sm:
            y0=sm['back_outer_y_mm']-.2;y1=sm['screw_head_base_y_mm']
            boolean(cup,cyl('rear_recessed_speaker_head',(side*24,(y0+y1)/2,0),sm['head_recess_radius_mm'],y1-y0,'Y'))
        else:boolean(cup,cyl('speaker_driver_clear',(side*24,-18,0),2.3,30,'Y'))
    # A real lead exit, with a disconnect service loop outside the cup.
    boolean(cup,cyl('speaker_lead_exit',(-10,-21,0),2,8,'Y'))
    finish(cup,'PRINTABLE','外壳固定扬声器后盖 / 独立声腔','frame','body',True,note='Body_Upper bosses only. Gasket, sealing, screw length and acoustic volume need prototype test. Disconnect two-wire BTL plug before shell removal.')
    relocate(cup,tr)
    intersect(cup,b.body_outer('speaker_cup_inner_contour',P['shell_thickness_mm']+.3))
    boolean(cup,clone(upper,'blind_boss_relief'))
    # Contact plane must remain flat while curved exterior stays continuous.
    boolean(upper,clone(sp,'speaker_nominal_relief'))
    start=tr@Vector((-10,-20,0));pts=[start,tr@Vector((-10,-26 if sm else -24,0)),Vector((-29,31,142)),Vector((-35,24,146))]
    q=None
    for a,bb in zip(pts,pts[1:]):
        w=b.beam('speaker_wire',a,bb,1)
        if q is None:q=w
        else:union(q,w)
    q.name=PREFIX+'Speaker_Lead';finish(q,'PLACEHOLDER','扬声器可断开服务线环','copper','body',False,role='routing')
    b.contact('Speaker_Mount','Body_Upper','Shell bosses and2 rear screws; no Load_Frame attachment')
    b.contact('Speaker','Speaker_Gasket','Factory front gasket nominal planar contact')
    save_json(ROOT/'reports/speaker_mount.json',{'revision':P['revision'],'model':s['model'],'source':s['source'],'nominal_diameter_depth_mm':[40,17.5],
      'tolerance_mm':.3,'world_transform':list(map(list,tr)),'fasteners':['Speaker_Screw_-1','Speaker_Screw_1'],'structural_parent':'Body_Upper',
      'load_frame_attachment':False,'fastener_trial':f'M2x{sm["screw_length_mm"]:g}, rear recessed heads, continuous cup outline' if sm else 'M2x6, blind shell bosses, no exterior speaker screw holes','screw_head_base_local_y_mm':sm['screw_head_base_y_mm'] if sm else -5,'no_external_screw_ears':bool(sm),'diaphragm_clearance_nominal_mm':1.2,'acoustic_qualification':'NOT_TESTED','sealing_and_tool_handles':'NOT_TESTED'})


def selected_battery():
    s=P['detail_fit']['battery'];old=obj('Battery');old.name=PREFIX+'Battery_Capacity_Reserve';move_collection(old,'KEEP_OUT');old['role']='keepout';old['category']='KEEP_OUT'
    bottom=P['layout']['battery_center_mm'][2]-P['layout']['battery_max_xyz_mm'][2]/2
    # Keep the finished pack on the existing tray, not floating at the former
    # envelope centre. The wider legacy bay remains a separate sizing reserve.
    o=box('Battery',(0,0,bottom+s['nominal_xyz_mm'][2]/2),s['nominal_xyz_mm'])
    finish_reference(o,'Tenergy31013 成品3S / 71×55×20','VENDOR_DIMENSIONED_ENVELOPE',['TENERGY31013'],'body','blue')
    o['selection_status']=s['selection_status'];o['documented_mass_g']=150
    o['unknown_dimensions']=['pack_tolerance','lead_exit','lead_length','insulated_connector','optional_NTC'];o['dimension_note']='Nominal bounding envelope; shrink-wrap contour and lead positions not documented. No bare cells are assembled here.'
    # Four removable foam locator blocks use the available bay, retaining the
    # existing adjustable strap slots and battery extraction sequence.
    for x in [-38.0,38.0]:
        pad=box('Battery_Pad_'+str(x),(x,0,bottom+3.5),(4,45,8))
        assumed(pad,'电池侧向可更换软垫 / 试配','body','tire')
    assumed(box('Battery_Pad_Base',(0,0,bottom-.25),(71,55,.5)),'电池底部0.5mm软垫 / 试配','body','tire')
    b=source_build();b.contact('Battery','Battery_Tray','Finished pack on original padded tray; final straps/lead geometry unqualified')


def weact_board():
    import hashlib
    c=json.loads((PROJECT/P['detail_fit']['weact_mesh']).read_text())
    source=PROJECT/c['source_file'];assert hashlib.sha256(source.read_bytes()).hexdigest()==c['source_sha256']
    # Original CAD33.22 alongX,41.603 alongY. Rz90 gives board long axis X.
    r=np.array([[0.,-1,0],[1,0,0],[0,0,1]])
    source_center=np.array([116.078,69.2145,0.])
    # Match rear bay without modifying CAD. This is a placement proposal; the
    # actual carrier/header stack must be reconciled by the hardware owner.
    origin=np.array([0.,-37.,122.])
    verts=[];faces=[];solids=[];bad=[]
    for s in c['solids']:
        v=(np.array(s['vertices_mm'])-source_center)@r.T+origin;f=np.array(s['triangles'],dtype=np.uint64)
        m=manifold.Manifold(manifold.Mesh64(v,f))
        if m.status()!=manifold.Error.NoError:
            bad.append(s['index']);lo=v.min(axis=0)-.001;hi=v.max(axis=0)+.001
            m=manifold.Manifold.cube((hi-lo).tolist(),True).translate(((hi+lo)/2).tolist())
        solids.append(m);faces.extend((f+len(verts)).tolist());verts.extend(v.tolist())
    old=obj('MCU_Motion');old.name=PREFIX+'Motion_Carrier_Reserve';move_collection(old,'KEEP_OUT');old['role']='keepout';old['category']='KEEP_OUT'
    raw=np.array(verts);lo=raw.min(axis=0)-.001;hi=raw.max(axis=0)+.001
    m=manifold.Manifold.cube((hi-lo).tolist(),True).translate(((hi+lo)/2).tolist());d=m.to_mesh64()
    proxy=mesh('WeAct_Collision_Proxy',d.vert_properties[:,:3].tolist(),d.tri_verts.tolist());finish(proxy,'KEEP_OUT','WeAct碰撞代理','keepout','body',False,role='validation_proxy')
    o=mesh('MCU_Motion',verts,faces);finish_reference(o,'WeAct F412RET6 V1.1 / 原厂整板CAD','VENDOR_CAD',['WEACT_V11'],'body','pcb')
    o['preserve_vendor_tessellation']=True;o['validation_proxy']=proxy.name;o['source_scale_factor']=1.0;o['source_sha256']=c['source_sha256']
    o['placement_limit']='Rigid board placement only. Actual carrier/header stack and connector approach still need PCB handoff; not a claim of complete populated carrier fit.'
    # A short removable support under the vendor board; actual header heights
    # stay an allocation, rather than silently shortening header pins.
    # The original frame already has a local board shelf. No redundant pad.
    # Purchased board placement does not freeze the carrier/header stack.
    save_json(ROOT/'reports/vendor_weact_import.json',{'status':'PASS','solid_count':len(c['solids']),'source_sha256':c['source_sha256'],'source_scale_factor':1,'rotation_determinant':float(np.linalg.det(r)),
      'source_center_mm':source_center.tolist(),'destination_board_top_datum_mm':origin.tolist(),'imported_bounds_xyz_mm':bounds(o),'tessellation_proxy_indices':bad,'collision_method':'Conservative complete CAD bounding solid; original224-solid rendering unchanged. Tiny CAD contact unions lose manifold validity in Blender float32; exact all-solid interference NOT_TESTED.','carrier_stack':'BLOCKED','physical_measurement':False})


def microphones():
    # The manufacturer photo establishes side and approximate registration,
    # not metrology. Keep mic coordinates/package dimensions explicitly assumed.
    s=P['detail_fit']['mic_photo_estimate'];l=P['layout'];cx,cy,cz=l['cam_board_center_from_head_mm'];cz+=D['head_z']
    cam=obj('CAM_Mainboard');old=clone(cam,'CAM_Populated_Reserve');finish(old,'KEEP_OUT','CAM12mm装件空间 / 非真实板厚','keepout','pitch',False,role='keepout')
    depth=l['cam_board_allocation_xyz_mm'][1]
    for v in cam.data.vertices:v.co.y=cy+(v.co.y-cy)*s['pcb_thickness_assumed_mm']/depth
    SOLIDS.pop(cam.name,None)
    cam['label_zh']='CAM33700 板框37×37 / 板厚示意';cam['model_fidelity']='PARTIAL_VENDOR_DIMENSIONS'
    from microphone_geometry import microphone_paths
    for datum in microphone_paths():
        side=datum['side']
        remove_generated('Mic_Duct_'+side)
        o=box('Onboard_MIC_'+side,datum['package'],s['package_xyz_mm'],.2)
        assumed(o,'CAM板载MIC'+side+' / 照片位置示意',mat='metal',fidelity='PHOTO_REGISTERED_ASSUMED')
        o['included_in']='Waveshare33700';o['do_not_buy_separately']=True;o['coordinate_uncertainty_mm']=1
        port=cyl('MIC_Sound_Port_'+side,datum['port'],.3,.04,'Y',24)
        finish(port,'ANNOTATIONS','MIC 声孔示意','dark','pitch',False,role='annotation')
        # Historical construction tube is retired by the final consolidation
        # phase in M1.19. The rear-frame opening stays as an unsealed air path.
        b=source_build();a=datum['start'];end=datum['inner']
        tube=b.beam('Mic_Duct_'+side,a,end,2.2);boolean(tube,b.beam('mic_airway',a-Vector((0,-.2,0)),end+Vector((0,-.3,0)),1.25))
        clip_y(tube,-200,cy-2.05)
        boolean(obj('Pitch_Cradle'),b.beam('mic_cradle_passage',a,end,P['microphone_acoustics']['cradle_airway_radius_mm']))
        boolean(tube,clone(obj('Head_Rear'),'mic_local_clear'))
        finish(tube,'PRINTABLE','独立麦克风声道 '+side+' / 位置待实板确认','dark','pitch',True,note='Photo-estimated mic registration. Not released for printing before measured alignment; independent from body speaker chamber.')
    obj('Function_Button')['label_zh']='功能/停止运动按钮（不是RESET）'
    obj('Button_Cap')['label_zh']='功能键帽（无外置重置开关）'


def apply_detail_fit():
    if not P.get('detail_fit',{}).get('enabled'):return
    screen_fork();shell_speaker();selected_battery();weact_board();microphones()
    # Refresh current module evidence after replacing one module's geometry.
    change=json.loads((ROOT/'reports/structure_changes.json').read_text())
    mods={o.name.removeprefix(PREFIX):o for o in parts() if o.get('simple_support_module')}
    change.update(revision=P['revision'],after={n:{'volume_mm3':volume(o),'bounds_xyz_mm':bounds(o)} for n,o in mods.items()},support_printed_parts_after=len(mods),new_integral_bodies=list(mods))
    save_json(ROOT/'reports/structure_changes.json',change)
    save_json(ROOT/'reports/detail_fit_geometry.json',{'revision':P['revision'],'default_head_pitch_deg':P['head_joint']['default_pitch_deg'],'external_reset':False,'functional_button_is_reset':False,
      'selected_geometry':{n:bounds(obj(n)) for n in ['Camera_Window','Camera_Lens','Display_Frame','Speaker','Speaker_Mount','Battery','MCU_Motion','Onboard_MIC_L','Onboard_MIC_R','Power_Switch','USB_Receptacle']},
      'limits':['CAM component coordinates and thickness are photo/assumed; exact populated CAD unavailable','Camera lens/FPC package unmeasured','Battery NTC, balancing, tolerances, lead exit and charger remain open','S3 power PCB not laid out','Carrier/WeAct actual stacked headers not fitted']})
    print('DETAIL_FIT_COMPLETE',flush=True)
