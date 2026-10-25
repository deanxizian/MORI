"""Current keyed bridge joint; retain the legacy M1.15 builder for old configs."""
from common import *
from structural_simplification import hardware

S=P.get('yaw_bridge_mount',{})

def crossbolt_enabled():
    return S.get('enabled') and S.get('type')=='KEYED_LAP_TRANSVERSE_M3_NUT'

def crossbolt_datums():
    top=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    ss=P['structure']['simple_modules'];b=P['belly_relayout']
    outer=ss['side_plate_abs_x_mm']+ss['side_plate_thickness_mm']/2
    half=outer-ss['side_plate_thickness_mm']-S['cheek_sliding_gap_mm']
    return dict(deck_top=top,deck_bottom=top-P['layout']['deck_thickness_mm'],outer=outer,
        half=half,inner=half-b['yaw_bridge_leg_thickness_mm'],thick=b['yaw_bridge_leg_thickness_mm'],
        headseat=outer-S['head_recess_depth_mm'],tongue_bottom=top-S['tongue_depth_below_deck_top_mm'],
        bolt_z=top-S['bolt_z_below_deck_top_mm'],depth=b['yaw_bridge_depth_mm'],roof_z=b['yaw_bridge_roof_z_mm'])

def sites():
    b=P['belly_relayout']
    x=b['yaw_bridge_half_width_mm']-b['yaw_bridge_leg_thickness_mm']/2
    y=b['yaw_bridge_depth_mm']/2-S['bolt_y_edge_margin_mm']
    return [(sign,sign*x,-y) for sign in [-1,1]]

def datums():
    top=P['layout']['deck_z_mm']+P['layout']['deck_thickness_mm']/2
    bottom=top-P['layout']['deck_thickness_mm']
    return top,bottom,bottom+S['head_recess_depth_mm']

def bridge_joints(base):
    if crossbolt_enabled():return [] # Build after the final integral frame exists.
    top,bottom,head=datums();joints=[]
    for sign,x,y in sites():
        boolean(base,cyl('blind_insert_pilot',(x,y,top+(S['insert_pilot_depth_mm']-.2)/2),S['insert_pilot_diameter_mm']/2,S['insert_pilot_depth_mm']+.2))
        boolean(base,cyl('blind_screw_tip_clear',(x,y,top+(S['blind_clearance_depth_mm']-.2)/2),S['screw_clearance_diameter_mm']/2,S['blind_clearance_depth_mm']+.2))
        iz=top+S['insert_inset_from_foot_mm']+S['insert_length_mm']/2
        insert=ring('Yaw_Base_'+str(sign)+'_Insert',(x,y,iz),S['insert_outer_diameter_mm']/2,S['insert_inner_diameter_model_mm']/2,S['insert_length_mm'])
        hardware(insert,'承重桥脚M2盲孔嵌件 / 试配')
        insert['interface_status']='M2 heat-set insert nominal envelope; supplier OD, length and hole compensation require a coupon'
        screw=cyl('Yaw_Base_'+str(sign)+'_Screw',(x,y,head+S['screw_length_mm']/2),S['screw_shank_diameter_model_mm']/2,S['screw_length_mm'])
        union(screw,cyl('recessed_M2_head',(x,y,head-S['head_height_mm']/2),S['head_diameter_mm']/2,S['head_height_mm']))
        hardware(screw,'板底向上M2×8 / 承重桥固定')
        joints.append({'id':'Yaw_Base_'+str(sign),'axis':'Z','xy_mm':[x,y],'head_base_mm':head,'head_height_mm':S['head_height_mm'],'access_direction':'-Z','group':'body','upper':'Yaw_Base','lower':'Load_Frame','prerequisite_removed':['Battery','Battery_Tray'],'prerequisite_removed_prefixes':['Battery_Retainer'],'fastener_type':'M2 screw into blind heat-set insert','screw_length_mm':S['screw_length_mm']})
    base['mounting_note']='Straight exterior side faces and feet; recessed underside fasteners. No projecting ear or outside vertical screwdriver groove.'
    return joints

def deck_holes(deck):
    if crossbolt_enabled():return # No superseded underside holes in current geometry.
    top,bottom,head=datums()
    for sign,x,y in sites():
        boolean(deck,cyl('underside_bridge_M2_clear',(x,y,(top+bottom)/2),S['screw_clearance_diameter_mm']/2,top-bottom+1))
        boolean(deck,cyl('underside_bridge_head_recess',(x,y,(bottom-.2+head)/2),S['head_recess_diameter_mm']/2,head-bottom+.2))

def profile_prism(name,profile_yz,xmin,width):
    m=manifold.CrossSection([profile_yz]).extrude(width)
    m=m.transform(np.array([[0,0,1,xmin],[1,0,0,0],[0,1,0,0]],dtype=float))
    data=m.to_mesh64();o=mesh(name,data.vert_properties[:,:3].tolist(),data.tri_verts.tolist())
    SOLIDS[o.name]=m
    return o

def apply_crossbolt_joint():
    if not crossbolt_enabled():return
    d=crossbolt_datums();top=d['deck_top'];half=d['half'];inner=d['inner'];thick=d['thick']
    base=bpy.data.objects[PREFIX+'Yaw_Base'];frame=bpy.data.objects[PREFIX+'Load_Frame']
    rr=S['root_fillet_radius_mm'];ty=S['tongue_depth_y_mm']/2;z0=d['tongue_bottom'];dep=d['depth']/2
    # Add broad integral tongues to the existing legs; the original flat feet
    # outside the socket remain the shoulder bearing surfaces.
    profile=[(-ty,z0),(ty,z0),(ty,top-rr)]
    profile += [(ty+rr+rr*math.cos(a),top-rr+rr*math.sin(a)) for a in np.linspace(math.pi,math.pi/2,13)[1:]]
    profile += [(dep,top),(dep,d['roof_z']+.1),(-dep,d['roof_z']+.1),(-dep,top),(-ty-rr,top)]
    profile += [(-ty-rr+rr*math.cos(a),top-rr+rr*math.sin(a)) for a in np.linspace(math.pi/2,0,13)[1:]]
    c=S['slot_clearance_per_side_mm'];hw=[];joints=[]
    for sign in [-1,1]:
        union(base,profile_prism('lapping_bridge_leg',profile,inner if sign>0 else -half,thick))
        # Cut through both deck and its existing underside ledge, not a blind slot.
        slot=[(-ty-c,z0-1),(ty+c,z0-1),(ty+c,top-rr),(ty+c+rr,top),
              (ty+c+rr,top+1),(-ty-c-rr,top+1),(-ty-c-rr,top),(-ty-c,top-rr)]
        boolean(frame,profile_prism('tongue_socket',slot,inner-c if sign>0 else -half-c,thick+2*c))
        y=S['bolt_y_mm'];z=d['bolt_z'];nut_seat=inner+S['nut_pocket_depth_mm'];hs=d['headseat']
        for o in [base,frame]:
            boolean(o,cyl('cross_M3_clear',(sign*(inner+thick/2),y,z),S['screw_clearance_diameter_mm']/2,20,'X'))
        boolean(base,cyl('hex_nut_pocket',(sign*(inner+(S['nut_pocket_depth_mm']-.1)/2),y,z),
            S['nut_pocket_af_mm']/math.sqrt(3),S['nut_pocket_depth_mm']+.1,'X',6))
        boolean(frame,cyl('flush_button_head_seat',(sign*((hs+d['outer']+.2)/2),y,z),
            S['head_recess_diameter_mm']/2,d['outer']+.2-hs,'X'))
        name='Yaw_Base_'+str(sign)
        n=cyl(name+'_Nut',(sign*(nut_seat-S['nut_thickness_mm']/2),y,z),S['nut_af_mm']/math.sqrt(3),S['nut_thickness_mm'],'X',6)
        boolean(n,cyl('smooth_thread_bore',(sign*(nut_seat-S['nut_thickness_mm']/2),y,z),S['nut_bore_diameter_model_mm']/2,4,'X'))
        b=cyl(name+'_Screw',(sign*(hs-S['screw_length_mm']/2),y,z),S['screw_shank_diameter_model_mm']/2,S['screw_length_mm'],'X')
        union(b,cyl('button_head_envelope',(sign*(hs+S['head_height_mm']/2),y,z),S['head_diameter_mm']/2,S['head_height_mm'],'X'))
        boolean(b,cyl('hex_drive_illustration',(sign*(hs+1.45),y,z),2/math.sqrt(3),.6,'X',6))
        for ob,label in [(n,'承重桥M3金属六角螺母 / 名义外形参考'),(b,'承重桥横向M3×8低圆头螺钉 / 名义包络')]:
            finish(ob,'PURCHASED_REFERENCE',label,'metal','body',False,note=S['fit_status'])
            ob['model_fidelity']='NOMINAL_FASTENER_ENVELOPE';ob['data_status']='ASSUMED';ob['mounting_release']=False
            ob['explode_offset_mm']=[sign*(24 if ob==b else -12),0,0 if ob==b else 34]
            hw.append(ob.name.removeprefix(PREFIX))
        joints.append(dict(id=name,axis='X',sign=sign,center_yz_mm=[y,z],head_base_mm=sign*hs,
            head_height_mm=S['head_height_mm'],
            access_direction='+X' if sign>0 else '-X',upper='Yaw_Base',lower='Load_Frame',group='body',
            fastener_type='M3x8 button-head screw + metal hex nut',screw_length_mm=S['screw_length_mm'],
            validation_handler='yaw_bridge_joint_validation.json',prerequisites=S['prerequisites']))
    intersect(base,box('straight_bridge_outer_faces',(0,0,140),(2*half,200,150)))
    base['label_zh']='插接Yaw承重桥 / 横向M3穿栓与一体限位'
    base['mounting_note']=S['prerequisites'];base['structural_revision']=P['revision']
    base['print_orientation_candidate']='Compare planar Y-end down with roof-down; tongue layer adhesion, bearing roundness and support removal need slicer and physical review.'
    base['functional_purpose']='Bearing load to two broad bridge legs, shoulders and keyed/lap sockets; transverse metal nuts retain detachable joint. Compact yaw stops preserved.'
    frame['mounting_note']='Integral sockets and recessed side M3 seats for removable bridge; no underside bridge screws or heat-set inserts.'
    for o in [base,frame]:clean(o)
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text())
    plan['joints']=[j for j in plan['joints'] if not j['id'].startswith('Yaw_Base_')]+joints
    plan['yaw_bridge_mount']=dict(type=S['type'],assembly=S['prerequisites'],validation='yaw_bridge_joint_validation.json')
    for j in plan['joints']:
        if j['id'].startswith('Drive_'):
            j['prerequisite_removed_prefixes']=sorted(set(j.get('prerequisite_removed_prefixes',[]))|{'Yaw_Base','Yaw_Reaction','Yaw_Horn','Yaw_Output','Yaw_Lock'})
            j['prerequisite_removed']=sorted(set(j.get('prerequisite_removed',[]))|{'Yaw_Bearing'})
            j['service_note']=S['drive_joint_service_prerequisites']
    save_json(ROOT/'reports/module_assembly.json',plan)
    data=json.loads((ROOT/'reports/part_consolidation.json').read_text())
    data['fasteners_after']=sum(any(k in o.name for k in ['Screw','Nut','Insert','Washer']) for o in parts())
    data['current_joint_revision']=P['revision'];save_json(ROOT/'reports/part_consolidation.json',data)
    from structural_simplification import volume
    changes=json.loads((ROOT/'reports/structure_changes.json').read_text())
    for o in [base,frame]:
        n=o.name.removeprefix(PREFIX)
        if n in changes['after']:
            changes['after'][n]={'volume_mm3':volume(o),'bounds_xyz_mm':bounds(o)}
    changes['current_bridge_joint']=S['type'];save_json(ROOT/'reports/structure_changes.json',changes)
    save_json(ROOT/'reports/yaw_bridge_joint_geometry.json',dict(revision=P['revision'],datums_mm=d,
        geometry_source='config/geometry.json#/yaw_bridge_mount',hardware=hw,retired_ids=['Yaw_Base_-1_Insert','Yaw_Base_1_Insert'],
        no_new_printed_parts=True,qualification='ASSUMED / PRINT FIT AND STRENGTH NOT TESTED'))
    print('CROSSBOLT_BRIDGE_COMPLETE',flush=True)
