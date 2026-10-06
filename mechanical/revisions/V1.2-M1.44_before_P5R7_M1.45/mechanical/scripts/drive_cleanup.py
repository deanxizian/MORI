"""M1.26: continuous drive-cage walls and a flat service cap."""
from common import *
from monocoque_structure import obj
from simple_modules import module
from structural_simplification import volume
from purchased_geometry import remove_generated
from wheel_interfaces import xcyl

S=P.get('drive_print_cleanup',{})

def apply_drive_cleanup():
    if not S.get('enabled'):return
    ids=S['changed_print_ids'];reviewed=S['reviewed_print_ids']
    before={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in reviewed}
    for n in ids:
        a=clone(obj(n),'CONSTRUCTION_M1_25_'+n);a['role']='construction';a['export_candidate']=False
        a['source_revision']='V1.2-M1.25 before lower frame cleanup';move_collection(a,'DATUMS')
    drive=obj('Drive_Bridge');w=P['wheel_interface'];wz=D['wheel_z']
    roof=wz+P['structure']['simple_modules']['drive_roof_top_from_axle_mm']
    hx,hy=[v/2 for v in S['central_outer_xy_mm']];ix,iy=[v/2 for v in S['central_inner_xy_mm']]
    split=S['case_cap_split_z_mm'];base=w['clamp_plate_bottom_z_mm']-w['cap_head_recess_depth_mm']
    # The former inset posts become part of the walls, instead of four ribs
    # on a second, narrower box. The roof has the same flush outer edge.
    clip_y(drive,-hy,hy);clip_z(drive,split,1000)
    for sign in [-1,1]:
        union(drive,box('continuous_end_wall',(0,sign*(hy+iy)/2,(split+roof)/2),(2*hx,hy-iy,roof-split)))
        union(drive,box('continuous_side_wall',(sign*(hx+ix)/2,0,(split+roof)/2),(hx-ix,2*hy,roof-split)))
    union(drive,box('flush_case_roof',(0,0,roof-S['motor_roof_thickness_mm']/2),(2*hx,2*hy,S['motor_roof_thickness_mm'])))
    # A single broad cap carries both motor floors and both bearing saddles.
    # The original motor/soft-pad contact plane is the flat cap top at42mm.
    remove_generated('Motor_Retainer')
    ch=S['cap_corner_chamfer_mm']
    from layout_cleanup import mm_mesh
    cap=box('Motor_Retainer',(0,0,(base+split)/2),(2*hx,2*hy,split-base))
    # Keep the cap top corners square and flush to the case. Only the four
    # lower corners meet the spherical shell; each needs one diagonal plane.
    if ch:
        for sx in [-1,1]:
            for sy in [-1,1]:
                corner=manifold.Manifold.hull_points([(sx*hx,sy*hy,base),(sx*(hx-ch),sy*hy,base),(sx*hx,sy*(hy-ch),base),(sx*hx,sy*hy,base+ch)])
                boolean(cap,mm_mesh('bottom_corner_shell_clearance',corner))
    for side,sign in [('L',-1),('R',1)]:
        lo=S['bearing_bar_inner_x_mm'];mid=S['bearing_bar_bottom_transition_x_mm'];hi=w['bearing_housing_abs_x_limits_mm'][1]
        edge=P.get('drive_edge_cleanup',{})
        if edge.get('enabled') and side in edge['sides']:
            # The approved local edit: the low root ends at the cap outline,
            # rather than projecting1.5mm below the outer bearing saddle.
            mid=hx
        top=wz-w['bearing_split_gap_mm']/2
        # One straight-topped saddle; only its underside retains the minimum
        # rise needed near the spherical lower shell. No stacked top ledges.
        union(cap,box('inner_bearing_saddle',(sign*(lo+mid)/2,0,(S['bearing_bar_bottom_inner_z_mm']+top)/2),
                      (mid-lo,S['bearing_bar_depth_mm'],top-S['bearing_bar_bottom_inner_z_mm'])))
        union(cap,box('outer_bearing_saddle',(sign*(mid+hi)/2,0,(S['bearing_bar_bottom_outer_z_mm']+top)/2),
                      (hi-mid,S['bearing_bar_depth_mm'],top-S['bearing_bar_bottom_outer_z_mm'])))
        # The bottom outer corner really meets the spherical shell. Cut
        # only this underside edge, preserving plain top/side faces.
        z0=S['bearing_bar_bottom_outer_z_mm'];c=S['bearing_outer_lower_chamfer_mm']
        profile=[(hi-c,z0),(hi+.2,z0),(hi+.2,z0+c+.2)]
        if sign<0:profile=[(-x,z) for x,z in reversed(profile)]
        edge=manifold.CrossSection([profile]).extrude(S['bearing_bar_depth_mm']+2).rotate([90,0,0]).translate([0,S['bearing_bar_depth_mm']/2+1,0])
        boolean(cap,mm_mesh('functional_lower_shell_edge',edge))
        if split>S['cap_motor_floor_z_mm']+.001:
            bb=bounds(obj('Drive_Motor_'+side));clear=w['motor_seat_clearance_per_side_mm']
            boolean(cap,box('flat_motor_pocket',((bb[0][0]+bb[0][1])/2,(bb[1][0]+bb[1][1])/2,(S['cap_motor_floor_z_mm']+80)/2),
                            (bb[0][1]-bb[0][0]+2*clear,bb[1][1]-bb[1][0]+2*clear,80-S['cap_motor_floor_z_mm'])))
        # Bottom-open output approach; the cap saddle fits within this split.
        boolean(drive,box('cap_saddle_approach',(sign*(24.15+34.6)/2,0,(0+wz+w['bearing_split_gap_mm']/2)/2),
                          (34.6-24.15,S['bearing_bar_depth_mm']+S['bearing_bar_running_gap_mm'],wz+w['bearing_split_gap_mm']/2)))
        for target in [drive,cap]:
            boolean(target,xcyl('flange_sweep_clear',sign,24.15,34.6,8.2))
            boolean(target,xcyl('shaft_spacer_clear',sign,26,54,w['bearing_housing_throat_diameter_mm']/2))
            for x in w['bearing_centers_abs_x_mm']:
                width=w['bearing_width_mm'];margin=w['bearing_seat_axial_margin_mm']
                boolean(target,xcyl('bearing_race_seat',sign,x-width/2-margin,x+width/2+margin,w['bearing_seat_nominal_diameter_mm']/2))
        # Reopen the whole cartridge's downward path after the new walls.
        boolean(drive,box('output_downward_slot',(sign*28.85,0,28),(9.3,16.4,65.4)))
    for x,y in w['clamp_bolt_xy_mm']:
        boolean(drive,cyl('M3_case_bore',(x,y,53),1.65,40))
        boolean(drive,cyl('M3_top_nut_entry',(x,y,(62.1+68)/2),w['clamp_nut_clearance_af_mm']/math.sqrt(3),68-62.1,n=6))
        boolean(cap,cyl('M3_cap_bore',(x,y,(base+split)/2),1.65,split-base+2))
        boolean(cap,cyl('M3_flush_head',(x,y,(base-.2+w['clamp_plate_bottom_z_mm'])/2),w['cap_head_recess_diameter_mm']/2,w['clamp_plate_bottom_z_mm']-base+.2))
    module(drive,'平直轮驱上座 / 锁紧柱并入侧壁','body','Roof down; inspect underside pockets and bearing finish',
           'Continuous end/side walls replace narrow cage plus four projecting cap posts. Hardware, four upper M2 frame joints and four M3 cap bolts stay fixed.',(0,0,25))
    module(cap,'平板电机底盖 / 一体轴承鞍座','body','Flat bottom on bed; verify short bearing overhang supports',
           'Flat cap at the original motor pad plane, with straight-topped bearing saddles. Existing pads/bolts unchanged; functional bearing bores and shell-clearance underside retained.',(0,0,-35))
    for n in ids:
        o=obj(n);o.data.materials.clear();o.data.materials.append(MATS['frame']);o['drive_cleanup_revision']=S['revision']
    after={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in reviewed}
    report={'revision':P['revision'],'baseline_revision':S['baseline_revision'],'status':'GENERATED_PENDING_VALIDATION','changed_prints':ids,'reviewed_prints':reviewed,'before':before,'after':after,
            'removed_features':['four protruding cap-locking ribs','roof lip outside cage walls','stacked bearing-saddle top ledges','case-cap corner seam steps'],
            'preserved':['four bearing seats and axial lips','motor/pad positions','all fastener axes and sizes','battery support and removal','whole head and electronics','Load_Frame and battery support unchanged','2.5 mm lower cap corner clearance'],
            'part_count_change':0,'fastener_count_change':0,'limits':['Print strength/creep NOT_TESTED','Cable plugs and as-bought fit not qualified']}
    save_json(ROOT/'reports/drive_print_cleanup.json',report)
    for file,key in [('structure_changes.json','after'),('module_assembly.json','after')]:
        path=ROOT/'reports'/file;data=json.loads(path.read_text());data.setdefault(key,{}).update(after);save_json(path,data)
    print('DRIVE_CLEANUP_COMPLETE',flush=True)
