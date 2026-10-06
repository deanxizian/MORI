"""M1.13: six physical print pieces and four fasteners retired.

Short local integrations only. Retain source construction meshes and service splits.
"""
from common import *
from monocoque_structure import obj, source_build, reserve
from purchased_geometry import remove_generated
from structural_simplification import volume
from optics_mount import camera_transform, apply_mount

S=P.get('part_consolidation',{})

def archive(name):
    is_mic=name in P.get('microphone_acoustics',{}).get('retired_print_ids',[])
    o=clone(obj(name),('CONSTRUCTION_M1_18_' if is_mic else 'CONSTRUCTION_M1_12_')+name)
    o['role']='construction';o['export_candidate']=False
    o['source_revision']='V1.2-M1.18 retired microphone duct' if is_mic else 'V1.2-M1.12 pre-consolidation construction'
    move_collection(o,'DATUMS')
    return o

def material(o,name):
    o.data.materials.clear();o.data.materials.append(MATS[name])

def consolidate_camera():
    front=obj('Head_Front');cam=P['camera'];hz=D['head_z'];cy=cam['baffle_center_y_from_head_mm'];cz=hz+cam['pupil_from_head_mm'][2]
    tr=camera_transform();depth=S['camera_seat_depth_mm'];ro=S['camera_boss_outer_radius_mm']
    # Rear seat retains the original clear lens bore. The forward collar has
    # the same flared aperture as the shell, not a narrow deep sight tube.
    boss=ring('camera_integral_seat',(0,cy,cz),ro,S['camera_seat_inner_radius_mm'],depth,'Y')
    y0=cy+depth/2-.2;y1=cy+S['camera_collar_reach_mm']
    collar=cyl('camera_integral_collar',(0,(y0+y1)/2,cz),ro,y1-y0,'Y')
    cut=cyl('camera_flared_opening',(0,(y0+y1)/2,cz),cam['aperture_diameter_mm']/2,y1-y0+2,'Y')
    cut.scale.x=cam['aperture_horizontal_diameter_mm']/cam['aperture_diameter_mm']
    bpy.context.view_layer.update();boolean(collar,cut);union(boss,collar);apply_mount(boss,tr)
    intersect(boss,sphere('camera_mother_limit',(0,0,hz),D['head_radius']))
    boolean(boss,reserve('camera_window_seat',obj('Camera_Window'),S['camera_window_clearance_mm']))
    boolean(boss,reserve('camera_fork_clearance',obj('Display_Frame'),S['camera_support_clearance_mm']))
    union(front,boss);remove_generated('Camera_Baffle');material(front,'shell')
    # A coating specification on the inner collar, not another printed component.
    front.data.materials.append(MATS['dark']);inv=tr.inverted()
    for f in front.data.polygons:
        c=front.matrix_world@f.center;lc=inv@c
        if abs(lc.x)<ro+.1 and abs(lc.z-cz)<ro+.1 and cy-depth/2-.1<lc.y<y1 and (c-Vector((0,0,hz))).length<D['head_radius']-.15:
            f.material_index=1
    front['label_zh']='头前壳 / 一体相机遮光座'
    front['integrated_features']='Camera seat/collar; coat inner wall matte black; separate removable optical window remains'

def consolidate_yaw():
    hz=D['head_z'];yoke=obj('Pitch_Yoke');turn=obj('Yaw_Turntable')
    union(yoke,turn)
    # Restore the former interface's two through holes and nut recesses only
    # within its existing flat flange/floor, without adding long posts.
    for x in [-13,13]:
        for kind in ['Screw','Nut']:remove_generated(f'Gimbal_Base_{x}_{kind}')
    if P.get('head_routing',{}).get('defer_design'):
        remove_generated('Pitch_Cable_Clip')
    else:
        clip=obj('Pitch_Cable_Clip')
        centre=list(S['wire_guide_bridge_center_from_head_mm']);centre[2]+=hz
        union(clip,box('short_wire_guide_bridge',centre,S['wire_guide_bridge_xyz_mm']))
        centre=list(S['wire_guide_slot_center_from_head_mm']);centre[2]+=hz
        boolean(clip,box('wire_lay_in_slot',centre,S['wire_guide_slot_xyz_mm']))
        boolean(clip,reserve('guide_bearing_clearance',obj('Pitch_Bearing_R'),S['wire_guide_bearing_clearance_mm']))
        union(yoke,clip);material(yoke,'frame')
    yoke['label_zh']='Yaw转台与U托 / 一体开口线导'
    yoke['integrated_features']='Yaw journal + U support + open local wire guide; two obsolete bolted joints deleted'
    yoke['print_orientation_candidate']='Open U on side or journal axis vertical; evaluate bearing finish and local supports in slicer'
    yoke['functional_purpose']='One yaw-only load path, bilateral pitch supports and short lay-in wire guide. Fixed reaction shaft stays independently removable.'
    base=obj('Yaw_Base');z0,z1=[D['yaw_bearing_construction_z']+x for x in S['fixed_rim_join_z_from_bearing_mm']]
    union(base,ring('short_fixed_shroud_seat',(0,0,(z0+z1)/2),S['fixed_rim_join_outer_radius_mm'],S['fixed_rim_join_inner_radius_mm'],z1-z0))
    union(base,obj('Body_Top_Shroud'));material(base,'frame')
    # A tab below the bearing would prevent an integral journal/U from being
    # lifted out. Move BOTH stops to the accessible zone above the bearing.
    old_tab=box('old_lower_stop',(11,0,D['yaw_stop_construction_z']),(9.2,2.2,1.2))
    boolean(old_tab,cyl('preserve_journal',(0,0,D['yaw_stop_construction_z']),9.8,3))
    boolean(yoke,old_tab)
    for angle in [-76,76]:
        a=math.radians(angle);r=14
        boolean(base,box('retired_fixed_stop',(r*math.cos(a),r*math.sin(a),D['yaw_stop_construction_z']),(3.02,3.02,3.02)))
    if P.get('compact_yaw_stops',{}).get('enabled'):
        from yaw_stops import build_compact_stops
        build_compact_stops(base,yoke)
    else:
        legacy_yaw_stops(base,yoke)
    material(yoke,'frame');material(base,'frame')
    base['label_zh']='固定Yaw承重桥 / 一体遮缝环'
    base['integrated_features']='Fixed shadow rim, joined locally to bearing seat; compact stop blocks inside rim; open centre retained'

def legacy_yaw_stops(base,yoke):
    """Only for a pre-M1.21 configuration; current dimensions live in compact_yaw_stops."""
    z=D['yaw_bearing_construction_z']+S['final_yaw_stop_z_from_bearing_mm']
    union(yoke,box('upper_yaw_stop',(11,0,z),(9,2,1)))
    for angle in S['final_yaw_stop_angles_deg']:
        a=math.radians(angle);r=S['final_yaw_stop_radius_mm'];rr=S['final_yaw_stop_root_radius_mm']
        tab=box('upper_fixed_stop_tab',((r+rr)/2*math.cos(a),(r+rr)/2*math.sin(a),z),(rr-r+3,S['final_yaw_stop_tab_width_mm'],S['final_yaw_stop_tab_height_mm']))
        tab.rotation_euler.z=a;bpy.context.view_layer.update();union(base,tab)

def apply_part_consolidation():
    if not S.get('enabled'):return
    before={o.name.removeprefix(PREFIX):{'category':o.get('category'),'volume_mm3':volume(o) if o.get('category')=='PRINTABLE' else None} for o in parts()}
    for n in S['retired_print_ids']:
        if bpy.data.objects.get(PREFIX+n):archive(n)
    if not P.get('microphone_acoustics',{}).get('printed_ducts',True):
        for n in P['microphone_acoustics']['retired_print_ids']:remove_generated(n)
    for n in ['Head_Front','Pitch_Yoke','Yaw_Base','Wheel_Hub_L','Wheel_Hub_R']:archive(n)
    for side in ['L','R']:
        remove_generated('Wheel_Cap_'+side);o=obj('Wheel_Hub_'+side);material(o,'shell')
        o['label_zh']='白色外观一体轮毂 '+side
        o['integrated_features']='Outer hub disk is the visible face; axial bore retained. No separate cap or added connecting material.'
    consolidate_camera();consolidate_yaw()
    mapping={'Camera_Baffle':'Head_Front','Pitch_Cable_Clip':'Pitch_Yoke','Yaw_Turntable':'Pitch_Yoke','Body_Top_Shroud':'Yaw_Base','Wheel_Cap_L':'Wheel_Hub_L','Wheel_Cap_R':'Wheel_Hub_R'}
    b=source_build();alive={o.name.removeprefix(PREFIX) for o in parts()};contacts=[]
    for c in b.CONTACTS:
        row=dict(c);row['a']=mapping.get(row['a'],row['a']);row['b']=mapping.get(row['b'],row['b'])
        if row['a']!=row['b'] and row['a'] in alive and row['b'] in alive and row not in contacts:contacts.append(row)
    b.CONTACTS[:]=contacts
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text())
    plan['joints']=[j for j in plan['joints'] if not j['id'].startswith('Gimbal_Base_')]
    plan['merged_same_body_parts']+=['Yaw_Turntable + Pitch_Yoke + open Pitch_Cable_Clip','Body_Top_Shroud + Yaw_Base','Camera_Baffle + Head_Front','Wheel_Cap_L/R deleted; hub outer faces exposed']
    plan['microphones']='M1.19: no printed ducts or added fasteners. Keep the CAM onboard microphones, open rear-frame passages and shell sound holes; recording performance remains untested.'
    plan['additional_assembly']='With pitch head and shells detached, bench-fit fixed reaction link/horn/clamp through the combined yaw U/journal. Insert this group into bearing/bridge, then fit reaction cross-retainer, yaw servo/output and lock. Removal reverses this sequence; reaction link travels with U/journal after cross-retainer removal. In operation the reaction link remains BODY-fixed, never yaw-parented.'
    save_json(ROOT/'reports/module_assembly.json',plan)
    mods={o.name.removeprefix(PREFIX):o for o in parts() if o.get('simple_support_module')}
    changes=json.loads((ROOT/'reports/structure_changes.json').read_text())
    changes.update(revision=P['revision'],after={n:{'volume_mm3':volume(o),'bounds_xyz_mm':bounds(o)} for n,o in mods.items()},support_printed_parts_after=len(mods),new_integral_bodies=list(mods));save_json(ROOT/'reports/structure_changes.json',changes)
    after={o.name.removeprefix(PREFIX):{'category':o.get('category'),'volume_mm3':volume(o) if o.get('category')=='PRINTABLE' else None} for o in parts()}
    printed=lambda a:sum(v['category']=='PRINTABLE' for v in a.values())
    fasteners=lambda a:sum(any(k in n for k in ['Screw','Nut','Insert']) for n in a)
    save_json(ROOT/'reports/part_consolidation.json',{'revision':P['revision'],'before_revision':'V1.2-M1.12','status':'GENERATED_PENDING_VALIDATION','robot_print_before':printed(before),'robot_print_after':printed(after),'fasteners_before':fasteners(before),'fasteners_after':fasteners(after),'retired_ids':sorted(set(before)-set(after)),'integrations':mapping,'changed_prints':[{'id':n,'volume_before_mm3':before[n]['volume_mm3'],'volume_after_mm3':after[n]['volume_mm3'],'bounds_xyz_mm':bounds(obj(n))} for n in ['Head_Front','Pitch_Yoke','Yaw_Base','Wheel_Hub_L','Wheel_Hub_R']],'service_sequence':plan['additional_assembly'],'retained_splits':plan['retained_service_splits']+['Battery_Tray for pack replacement','Motor_Retainer for wheel-drive insertion'],'print_release':False})
    cleanup=json.loads((ROOT/'reports/layout_cleanup_changes.json').read_text());cleanup['printed_parts_after_cleanup_phase']=cleanup['printed_parts_after'];cleanup['printed_parts_after']=printed(after);save_json(ROOT/'reports/layout_cleanup_changes.json',cleanup)
    print('PART_CONSOLIDATION_COMPLETE',printed(before),printed(after),flush=True)
