"""M1.14 wheel transmission. All purchased dimensions retain their evidence status.

The flange and shaft are ONE custom machined metal part, never a printed shaft.
Thread roots are simplified; no claimed thread-contact or preload simulation.
"""
from common import *
from monocoque_structure import obj,source_build
from purchased_geometry import remove_generated
from simple_modules import module
from structural_simplification import hardware,volume


def xcyl(name,sign,x0,x1,r,y=0,z=None,n=None):
    return cyl(name,(sign*(x0+x1)/2,y,D['wheel_z'] if z is None else z),r,x1-x0,'X',n)


def d_profile(name,sign,x0,x1,diameter,af):
    o=xcyl(name,sign,x0,x1,diameter/2)
    intersect(o,box('double_D_limits',(sign*(x0+x1)/2,0,D['wheel_z']),(x1-x0+2,af,diameter+2)))
    return o


def wheel_ref(o,label,group='body',documented=False,note='Custom design nominal, no physical qualification'):
    finish(o,'PURCHASED_REFERENCE' if documented else 'PLACEHOLDER',label,'metal',group,False,note=note)
    o['model_fidelity']='VENDOR_DIMENSIONED_SIMPLIFICATION' if documented else 'CUSTOM_DESIGN_OR_FASTENER_REQUIREMENT'
    o['data_status']='VENDOR_DOCUMENTED' if documented else 'ASSUMED'
    o['measured_unit']=False;o['mounting_release']=False
    return o


def apply_wheel_interfaces():
    w=P.get('wheel_interface',{})
    if not w.get('enabled'):return
    b=source_build();wz=D['wheel_z'];roof=wz+P['structure']['simple_modules']['drive_roof_top_from_axle_mm']
    before={o.name.removeprefix(PREFIX):{'category':o.get('category'),'candidate':o.get('export_candidate'),'volume_mm3':volume(o) if o.get('category')=='PRINTABLE' else None} for o in parts()}
    drive=obj('Drive_Bridge')
    shell=obj('Body_Lower')
    shell=obj('Body_Lower')
    slot=w['shell_axle_service_slot_width_mm']
    boolean(shell,cyl('axle_service_round',(0,0,wz),slot/2,180,'X'))
    boolean(shell,box('axle_service_to_upper_seam',(0,0,wz+50),(180,slot,100)))
    shell.data.materials.clear();shell.data.materials.append(MATS['shell'])
    clean(shell)
    shell['wheel_service_opening']='10mm open-top axle slots within wheel-covered pockets; body lower drops without extracting integrated shafts'

    for n in list(before):
        if n.startswith(('Wheel_Coupler_','Wheel_Axle_','Wheel_Bearing_','Motor_Retainer_Screw_','Motor_Retainer_Insert_')) or n=='Motor_Retainer':remove_generated(n)
    # Remove obsolete centre cap screw pillars; retain the simple shared roof.
    for y in [-20,20]:boolean(drive,box('obsolete_cap_pillar',(0,y,(42+63.5)/2),(7,7,63.5-42)))
    tidy=P.get('fastener_cleanup',{}).get('enabled',False)
    cap_bottom=w['clamp_plate_bottom_z_mm']-w.get('cap_head_recess_depth_mm',0) if tidy else 39.5
    cap_xy=w['flat_cap_outline_xy_mm'] if tidy else [55,56.6]
    if tidy:
        hx,hy=[v/2 for v in cap_xy];c=w.get('cap_corner_chamfer_mm',2.5)
        outline=[(-hx+c,-hy),(hx-c,-hy),(hx,-hy+c),(hx,hy-c),(hx-c,hy),(-hx+c,hy),(-hx,hy-c),(-hx,-hy+c)]
        from layout_cleanup import mm_mesh
        cap=mm_mesh('Motor_Retainer',manifold.CrossSection([outline]).extrude(42-cap_bottom).translate([0,0,cap_bottom]))
    else:cap=box('Motor_Retainer',(0,0,40.75),(55,56.6,2.5),.4)
    axes=[];fastener_rows=[];stack_rows=[]
    for side,sign in [('L',-1),('R',1)]:
        group='wheel_'+side
        # Vendor output holes. Keep the factory central screw untouched; the
        # flange rear relief reserves its unmeasured proud-head height.
        for tag in ['Inner','Outer']:
            out=obj(f'S288_Output_{side}_{tag}')
            for a in w['output_hole_angles_deg']:
                y=w['output_hole_pcd_mm']/2*math.cos(math.radians(a));z=wz+w['output_hole_pcd_mm']/2*math.sin(math.radians(a))
                boolean(out,xcyl('vendor_output_pilot',sign,23.95 if tag=='Outer' else .95,27.05 if tag=='Outer' else 4.05,w['output_pilot_diameter_mm']/2,y,z,n=32))
            wheel_ref(out,'S288原配输出盘 / 六孔 '+side+' '+tag,group,True,'S288 drawing: OD14 x3, 6 x1.7 pilots PCD10.5, M2 self-tapping maximum3mm. Centre factory screw profile/clocking unmeasured.')
        x0=w['output_face_abs_x_mm'];xf=x0+w['flange_thickness_mm'];shoulder=w['shoulder_end_abs_x_mm'];end=w['shaft_end_abs_x_mm']
        shaft=xcyl('Wheel_Axle_'+side,sign,x0,xf,w['flange_od_mm']/2)
        union(shaft,xcyl('integral_shoulder',sign,xf-.1,shoulder,w['shoulder_diameter_mm']/2))
        union(shaft,xcyl('round_journals',sign,shoulder-.1,w['hub_key_start_abs_x_mm'],w['shaft_journal_diameter_model_mm']/2))
        union(shaft,d_profile('double_D_end',sign,w['hub_key_start_abs_x_mm']-.1,end,w['shaft_journal_diameter_model_mm'],w['shaft_key_across_flats_mm']))
        boolean(shaft,xcyl('factory_screw_relief',sign,x0-.05,x0+w['factory_screw_recess_depth_mm'],w['factory_screw_recess_diameter_mm']/2))
        boolean(shaft,xcyl('M3_thread_major_simplification',sign,end-9.5,end+.1,1.525))
        for index,a in enumerate(w['output_hole_angles_deg']):
            y=w['output_hole_pcd_mm']/2*math.cos(math.radians(a));z=wz+w['output_hole_pcd_mm']/2*math.sin(math.radians(a))
            boolean(shaft,xcyl('M2_flange_through',sign,x0-.1,xf+.1,w['flange_hole_clearance_mm']/2,y,z,n=32))
            boolean(shaft,xcyl('head_and_tool_open_scallop',sign,xf,shoulder+.1,w['shoulder_tool_relief_diameter_mm']/2,y,z,n=40))
            screw=xcyl(f'Wheel_Output_Screw_{side}_{index}',sign,xf-w['output_screw_length_mm'],xf,.74,y,z,n=24)
            union(screw,xcyl('M2_selftap_pan_envelope',sign,xf,xf+w['output_screw_head_height_max_mm'],w['output_screw_head_diameter_max_mm']/2,y,z,n=32))
            wheel_ref(screw,'原厂兼容 M2 自攻 ×8 需求 '+side+' '+str(index),group,note='Manufacturer says M2 self-tap, not ordinary metric machine thread. Candidate head<=3.8x1.6; root shown1.48, major2 not meshed. Supplier head/length/tip must be matched before use.')
            screw['fastener_spec']='S288-compatible M2 self-tapping x8';screw['thread_engagement_mm']=w['output_screw_length_mm']-w['flange_thickness_mm']
            fastener_rows.append({'id':screw.name.removeprefix(PREFIX),'side':side,'axis_world':[sign,0,0],'head_face_abs_x_mm':xf+1.6,'yz_mm':[y,z],'engagement_mm':w['output_screw_length_mm']-w['flange_thickness_mm'],'tool_diameter_mm':w['output_tool_diameter_mm']})
        wheel_ref(shaft,'整体金属法兰轴 / 双扁位 '+side,group,note='CUSTOM MACHINED, not purchased Unitree geometry and not printable. 6mm journals, integral output flange/shoulder, double-D end and M3 axial thread. Nominal drawing; physical coaxiality/fits/strength pending.')
        shaft['material_suggestion']=w['shaft_material'];shaft['manufacturing_method']='CUSTOM_METAL_MACHINING';shaft['mass_density_g_cm3']=7.85
        shaft['positive_drive']='Six output screws -> integral shaft -> double D with12.2mm engagement';shaft['wheel_rotating']=True
        # New bearing housing replaces only the old local bearing webs.
        boolean(drive,box('old_bearing_web_clear',(sign*41,0,51.25),(24,27,24.5)))
        boolean(drive,box('output_and_flange_drop_slot',(sign*28.85,0,28),(9.3,16.4,65.4)))
        xmin,xmax=w['bearing_housing_abs_x_limits_mm'];split=wz+w['bearing_split_gap_mm']/2
        union(drive,box('upper_bearing_block',(sign*(xmin+xmax)/2,0,(split+roof)/2),(xmax-xmin,24,roof-split)))
        lower_top=wz-w['bearing_split_gap_mm']/2
        union(cap,box('short_cap_step',(sign*30.75,0,43.25),(8.5,16,5.5)))
        union(cap,box('lower_bearing_block',(sign*(xmin+xmax)/2,0,(44.3+lower_top)/2),(xmax-xmin,18,lower_top-44.3),.85))
        if not tidy:
            for y in [-18,18]:union(cap,box('cap_bolt_flat_arm',(sign*30.25,y,40.75),(20.5,9,2.5)))
        for target in [drive,cap]:
            boolean(target,xcyl('flange_and_bolt_sweep_clear',sign,24.15,34.6,8.2))
            boolean(target,xcyl('shaft_spacer_pass',sign,26,54,w['bearing_housing_throat_diameter_mm']/2))
            for i,x in enumerate(w['bearing_centers_abs_x_mm']):
                width=w['bearing_width_mm'];margin=w['bearing_seat_axial_margin_mm']
                boolean(target,xcyl('bearing_outer_race_seat',sign,x-width/2-margin,x+width/2+margin,w['bearing_seat_nominal_diameter_mm']/2))
        for i,x in enumerate(w['bearing_centers_abs_x_mm']):
            bearing=ring(f'Wheel_Bearing_{side}_{"Inner" if i==0 else "Outer"}',(sign*x,0,wz),w['bearing_od_mm']/2,w['bearing_id_mm']/2,w['bearing_width_mm'],'X')
            wheel_ref(bearing,'686ZZ 独立轮轴承 '+side+(' 内' if i==0 else ' 外'),documented=True,note='686ZZ nominal6x13x5 from SMB supplier drawing. Ring/shield/bearing internals simplified; bore P0 0/-0.008. Shaft/seat fits and internal clearance must be qualified.')
            bearing['source_url']=w['bearing_source']
        for i,(a,z) in enumerate(w['spacer_spans_abs_x_mm']):
            spacer=ring(f'Wheel_Spacer_{side}_{i}',(sign*(a+z)/2,0,wz),w['spacer_od_mm']/2,w['spacer_id_mm']/2,z-a,'X')
            wheel_ref(spacer,'金属定长隔套 '+side+f' {z-a:g}mm',group,note='Custom cut/face tube OD8 ID6.1; end faces square. Contact only inner races. Actual lengths must match bearing stack without unwanted preload.')
            spacer['manufacturing_method']='CUSTOM_METAL_CUT_TO_LENGTH';spacer['mass_density_g_cm3']=7.85
        hub=obj('Wheel_Hub_'+side)
        # Old 4.4mm round bore is completely replaced with a matching D slot.
        boolean(hub,d_profile('hub_double_D',sign,59,73.0,w['hub_key_clearance_diameter_mm'],w['hub_key_clearance_across_flats_mm']))
        boolean(hub,xcyl('hub_end_bolt_recess',sign,w['hub_washer_seat_abs_x_mm'],79,w['hub_counterbore_diameter_mm']/2))
        module(hub,'双扁位止转轮毂 '+side,group,'Outer flat face down; shaft-fit coupon first','No separate cap or coupler. Double-D is torque interface; M3 end screw and metal spacers give axial retention.',(sign*40,0,0))
        hub.data.materials.clear();hub.data.materials.append(MATS['shell'])
        wx0=w['hub_washer_seat_abs_x_mm'];wt=w['hub_washer_thickness_mm'];headbase=wx0+wt
        wheel_ref(ring('Wheel_End_Washer_'+side,(sign*(wx0+wt/2),0,wz),w['hub_washer_od_mm']/2,w['hub_washer_id_mm']/2,wt,'X'),'M3 端部平垫圈 '+side,group,note='Nominal7x3.2x0.5 washer; confirm selected ISO7089 supplier variant.')
        screw=xcyl('Wheel_End_Screw_'+side,sign,headbase-w['hub_screw_length_mm'],headbase,1.48)
        union(screw,xcyl('M3_socket_head',sign,headbase,headbase+w['hub_screw_head_height_mm'],w['hub_screw_head_diameter_mm']/2))
        wheel_ref(screw,'M3×8 轮毂轴向锁紧螺钉 '+side,group,note='Nominal ISO4762 head5.5x3; thread simplified.7.3mm axial engagement, washer contacts hub0.2mm beyond shaft tip. Removable thread patch/locking and torque require trial; do not bottom the screw.')
        screw['fastener_spec']='M3 x8 ISO4762 candidate';screw['thread_engagement_mm']=end-(headbase-w['hub_screw_length_mm'])
        motor=obj('Drive_Motor_'+side);mb=bounds(motor);ym=sum(mb[1])/2
        # Form-fitting case pocket with hard anti-rotation surfaces; no unknown
        # body screw depth is invented. Pads make cap preload adjustable.
        upper_pad=box('Motor_Top_Pad_'+side,(sign*14,ym,63),(12,12,w['motor_top_pad_thickness_mm']))
        finish(upper_pad,'PLACEHOLDER','轮驱上方定厚软垫 '+side,'tire','body',False,note='1mm nominal EPDM cut sheet; compression, temperature and creep not qualified. Case flats react torque after fit/shim adjustment.')
        upper_pad['model_fidelity']='ALLOCATION_ONLY';upper_pad['measured_unit']=False
        motor['mounting_method']='Captured rectangular case in shared cage/common bottom cap, shim-adjusted top/bottom contact; no assumed case screws';motor['material_suggestion']='Manufacturer engineering plastic case/gears; not a solid metal motor'
        axes.append({'side':side,'axis_world':[sign,0,0],'origin_world_mm':[sign*27,0,wz],'shaft_bounds_xyz_mm':bounds(shaft),'hub_bounds_xyz_mm':bounds(hub)})
        stack_rows.append({'side':side,'shoulder_abs_x_mm':shoulder,'bearing_spans_abs_x_mm':[[x-2.5,x+2.5] for x in w['bearing_centers_abs_x_mm']],'spacer_spans_abs_x_mm':w['spacer_spans_abs_x_mm'],'hub_span_abs_x_mm':[60.5,wx0],'washer_span_abs_x_mm':[wx0,headbase],'screw_head_end_abs_x_mm':headbase+3,'shaft_tip_recess_mm':wx0-end,'key_length_mm':end-60.5})
    # Four common M3 clamps secure the cap and split bearing housings. Access
    # is from below with the robot in the disabled service cradle / bench.
    for i,(x,y) in enumerate(w['clamp_bolt_xy_mm']):
        if tidy:union(drive,box('inset_M3_corner',(x,y,(42+roof)/2),(w['cap_columns_xyz_mm'][0],w['cap_columns_xyz_mm'][1],roof-42)))
        else:union(drive,cyl('short_M3_clamp_column',(x,y,(42+roof)/2),4.5,roof-42))
        boolean(drive,cyl('M3_column_clear',(x,y,53),1.65,30))
        nr=w['clamp_nut_clearance_af_mm']/math.sqrt(3)
        boolean(drive,cyl('M3_nut_top_entry',(x,y,(62.1+68)/2),nr,68-62.1,'Z',6))
        boolean(cap,cyl('M3_cap_through',(x,y,39),1.65,14))
        if tidy:boolean(cap,cyl('M3_cap_head_recess',(x,y,(cap_bottom-.2+w['clamp_plate_bottom_z_mm'])/2),w['cap_head_recess_diameter_mm']/2,w['clamp_plate_bottom_z_mm']-cap_bottom+.2))
        bottom=w['clamp_plate_bottom_z_mm'];ln=w['clamp_screw_length_mm']
        screw=cyl('Wheel_Cap_Clamp_Screw_'+str(i),(x,y,bottom+ln/2),1.48,ln)
        union(screw,cyl('M3_head',(x,y,bottom-1.5),2.75,3))
        wheel_ref(screw,'轮驱共用底盖 M3×25 '+str(i),note='M3x25 ISO4762 dimensional requirement, smooth thread approximation; nut nominal full2.4mm engagement.')
        screw['fastener_spec']='M3 x25 ISO4762 candidate'
        nut=cyl('Wheel_Cap_Clamp_Nut_'+str(i),(x,y,63.3),w['clamp_nut_af_mm']/math.sqrt(3),2.4,'Z',6)
        boolean(nut,cyl('round_M3_nut_bore',(x,y,63.3),1.55,4))
        wheel_ref(nut,'轮驱共用底盖 M3 防转六角螺母 '+str(i),note='M3 ISO4032 nominalAF5.5x2.4; print hex pocket5.8 trial. Nut insertion from top before load frame assembly.')
    # Preserve the existing deck-to-drive nut pockets and round clearances.
    for side,sign in [('L',-1),('R',1)]:
        for yy in [-8,8]:
            screw=obj(f'Drive_{side}_{yy}_Screw');nut=obj(f'Drive_{side}_{yy}_Nut');bb=bounds(nut)
            boolean(drive,cyl('original_frame_screw_pass',(sign*44.5,yy,64),1.2,18))
            boolean(drive,cyl('original_frame_nut_pocket',(sign*44.5,yy,sum(bb[2])/2),2.9,bb[2][1]-bb[2][0]+.3,'Z',6))
    module(drive,'双轮电机上座 / 686ZZ 上半轴承座','body','Shared roof flat on bed; verify split bearing pocket accuracy','Retains body load-frame interfaces. Common cage captures motor cases; local bearing lips retain outer races; four accessible M3 cap bolts.',(0,0,25))
    module(cap,'电机与轴承共用可拆底盖','body','Broad centre face on bed; short stepped bearing wings need support trial','One removable part closes both motor bays and four bearing seats; not a separate cap for each bearing.',(0,0,-35))
    # One small coupon tests the new true mating shapes, not arbitrary claimed
    # universal print compensation. It is auxiliary, outside the robot count.
    coupon=box('Coupon_Wheel_Fit',(0,0,0),(86,23,8))
    for x,d in [(-32,12.9),(-16,13.0),(0,13.1)]:boolean(coupon,cyl('bearing_trial',(x,0,0),d/2,10))
    for x,delta in [(17,0),(32,.05)]:
        tool=cyl('D_coupon',(x,0,0),(6.03+delta)/2,10)
        intersect(tool,box('D_coupon_flat',(x,0,0),(10,4.79+delta,12)));boolean(coupon,tool)
    finish(coupon,'COUPONS','686ZZ / 双扁位配合试样','coupon','coupon',True,note='Bearing seats12.9/13.0/13.1; D bores6.03x4.79 and6.08x4.84. Printer/material-specific tests, not universal clearance.',role='coupon')
    existing={o.name.removeprefix(PREFIX) for o in parts()}
    b.CONTACTS[:]=[c for c in b.CONTACTS if c['a'] in existing and c['b'] in existing]
    for side in ['L','R']:
        b.contact('Wheel_Axle_'+side,'S288_Output_'+side+'_Outer','Bolted flange faces,6 M2 selftap x8 at2.5mm documented maximum-compatible engagement; no thread-force simulation')
        b.contact('Wheel_Axle_'+side,'Wheel_Hub_'+side,'Double-D form-fit with nominal print clearance,12.2mm engagement; backlash/creep/load requires real test')
        for tag in ['Inner','Outer']:
            b.contact('Wheel_Bearing_'+side+'_'+tag,'Drive_Bridge','Nominal split bearing bore surface contact; separate friction/fit qualification')
            b.contact('Wheel_Bearing_'+side+'_'+tag,'Motor_Retainer','Nominal lower bearing seat surface, cap independently removable')
    after={o.name.removeprefix(PREFIX):o for o in parts()}
    report={'revision':P['revision'],'status':'GENERATED_PENDING_VALIDATION','source':'config/geometry.json#/wheel_interface','axes':axes,'output_fasteners':fastener_rows,'axial_stacks':stack_rows,'retired_ids':sorted(set(before)-set(after)),
            'robot_print_before':sum(v['category']=='PRINTABLE' and v['candidate'] for v in before.values()),'robot_print_after':sum(o.get('category')=='PRINTABLE' and o.get('export_candidate') for o in after.values()),
            'changed_prints':['Body_Lower','Drive_Bridge','Motor_Retainer','Wheel_Hub_L','Wheel_Hub_R'],'metal_custom_ids':['Wheel_Axle_L','Wheel_Axle_R']+[f'Wheel_Spacer_{s}_{i}' for s in ['L','R'] for i in [0,1]],'hardware_dimensions_status':'Vendor S288 and686ZZ nominal only; other screw envelopes and machining/print fits are design requirements, not measured supplier CAD','manufacturing_release':False}
    save_json(ROOT/'reports/wheel_interface_design.json',report)
    # Refresh the final module inventory used by delivery checks; historical
    # simplification phase measurements remain explicitly intermediate.
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text())
    plan['additional_assembly'] += ' M1.14: install6 flange screws per motor on bench before bearings; slide bearings/spacers onto shaft; insert whole cartridges from below; fit common cap with4 M3 bolts; install load frame, shell, then D hubs and end washers/M3 screws. Release wheel end bolts before cap/cartridge removal.'
    for key in ['after','modules']:
        if isinstance(plan.get(key),dict):
            for n in ['Drive_Bridge','Motor_Retainer','Wheel_Hub_L','Wheel_Hub_R']:
                if n in plan[key]:plan[key][n].update(volume_mm3=volume(obj(n)),bounds_xyz_mm=bounds(obj(n)))
    save_json(ROOT/'reports/module_assembly.json',plan)
    mods={o.name.removeprefix(PREFIX):o for o in parts() if o.get('simple_support_module')}
    changes=json.loads((ROOT/'reports/structure_changes.json').read_text())
    changes.update(revision=P['revision'],after={n:{'volume_mm3':volume(o),'bounds_xyz_mm':bounds(o)} for n,o in mods.items()},support_printed_parts_after=len(mods),new_integral_bodies=list(mods));save_json(ROOT/'reports/structure_changes.json',changes)
    data=json.loads((ROOT/'reports/part_consolidation.json').read_text())
    data['robot_print_after_consolidation_phase']=data['robot_print_after'];data['robot_print_after']=18
    data['fasteners_after_consolidation_phase']=data['fasteners_after'];data['fasteners_after']=sum(any(k in n for k in ['Screw','Nut','Insert','Washer']) for n in after)
    data['retired_ids']+=report['retired_ids']
    for row in data['changed_prints']:
        row.update(volume_after_mm3=volume(obj(row['id'])),bounds_xyz_mm=bounds(obj(row['id'])))
    save_json(ROOT/'reports/part_consolidation.json',data)
    cleanup=json.loads((ROOT/'reports/layout_cleanup_changes.json').read_text());cleanup['printed_parts_after']=18;save_json(ROOT/'reports/layout_cleanup_changes.json',cleanup)
    print('WHEEL_INTERFACE_COMPLETE',flush=True)
