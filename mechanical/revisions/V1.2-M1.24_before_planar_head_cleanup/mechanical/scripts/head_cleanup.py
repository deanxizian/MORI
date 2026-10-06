"""M1.24 head print simplification, after historical construction phases.

Only owned printed geometry is changed. Hardware and optical datums stay fixed.
Dimensions live in geometry.json/head_print_cleanup; all fits remain trials.
"""
from common import *
from monocoque_structure import obj, source_build, reserve
from structural_simplification import plate, volume
from simple_modules import module

S = P.get('head_print_cleanup', {})
IDS = ['Pitch_Cradle', 'Display_Frame', 'Pitch_Yoke']


def cut_box(o, name, lo, hi):
    return boolean(o, box(name, [(a+b)/2 for a,b in zip(lo,hi)], [b-a for a,b in zip(lo,hi)]))


def archive(o):
    c = clone(o, 'CONSTRUCTION_M1_23_' + o.name.removeprefix(PREFIX))
    c['role'] = 'construction'; c['export_candidate'] = False
    c['source_revision'] = 'V1.2-M1.23 before head simplification'
    move_collection(c, 'DATUMS')


def low_cradle():
    o = obj('Pitch_Cradle'); hz = D['head_z']
    # The four rear circular cutouts were two generations of acoustic passages,
    # NOT four CAM mounting holes. Open the entire region above the low back.
    cut_box(o, 'remove_tall_acoustic_ears', [-60,-45,hz+S['rear_top_from_head_mm']],
            [60,S['rear_trim_front_y_mm'],hz+60])
    module(o, '低背平板头托 / 顶部开放', 'pitch',
           'Rear flat face down; inspect shell lugs and transverse bores',
           'Low constant-height rear wall; microphones and antenna face open air above it. '
           'Bilateral trunnion lands, shell mounts and four removable face-joint holes retained. '
           'CAM retention still needs complete supplier package/hole data; the old acoustic holes were never board mounts.',
           (0,-45,100))


def plain_face_returns():
    o = obj('Display_Frame'); hz = D['head_z']
    xcut = S['face_core_half_width_mm']; z0,z1 = [hz+z for z in S['face_return_z_from_head_mm']]
    # Preserve the source-derived three LCD seats and the separate camera seat.
    # Replace stacked outer legacy ears, without copying their screw recess cuts.
    intersect(o, box('keep_optical_fork', (0,0,hz), (2*xcut,200,200)))
    union(o,box('single_face_crossbar',(0,29,hz-6),(64,3,8)))
    for sign in [-1,1]:
        poly = [(sign*x,y) for x,y in S['face_return_xy_mm']]
        # A single XY outline, extruded once, replaces overlapping return blocks.
        n = len(poly)
        vs = [(x,y,z) for z in [z0,z1] for x,y in poly]
        fs = [tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        fs += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        end = mesh('plain_face_return',vs,fs);recalc(end);union(o,end)
        for rel in S['face_joint_z_from_head_mm']:
            z=hz+rel; y=S['face_joint_y_mm']
            boolean(o,cyl('face_M2_clear',(sign*44,y,z),S['face_screw_clearance_radius_mm'],16,'X'))
            outer=S['face_nut_abs_x_mm']+S['face_nut_pocket_depth_mm']/2
            inner=S['face_nut_access_inner_x_mm']
            boolean(o,cyl('side_accessible_face_nut_pocket',(sign*(inner+outer)/2,y,z),
                          S['face_nut_pocket_radius_mm'],outer-inner,'X',6))
            nut=obj(f'Face_Joint_{sign}_{rel:.1f}_Nut')
            nut.location.x+=sign*S['face_nut_abs_x_mm']-sum(bounds(nut)[0])/2
            SOLIDS.pop(nut.name,None);bpy.context.view_layer.update()
    # No ornamental steps. Only the actual assembly envelope and routing cuts.
    for name in ['Head_Front','Head_Rear','Pitch_Cradle','Display_Collision_Proxy']:
        boolean(o,clone(obj(name),'actual_face_mating_clear'))
    for name in ['Screen_Lead','Camera_Lead']:
        from layout_cleanup import ROUTE_PATHS
        points,radius=ROUTE_PATHS[name]
        for a,c in zip(points,points[1:]):
            boolean(o,source_build().beam('optical_route_clear',a,c,radius+.6))
    module(o,'简化屏幕叉架 / 平直短搭接','pitch',
           'Rear planar rails on bed; review three optical seat supports',
           'Original three LCD M2 seats and camera location retained. Two paired side joints resist rotation; '
           'single-extrusion returns replace stacked blocks and open vertical recesses.',(0,85,80))


def continuous_yoke_floor():
    o=obj('Pitch_Yoke');hz=D['head_z'];z0,z1=[hz+z for z in S['yoke_floor_z_from_head_mm']]
    # Retain the true journal/stops and the thin lower shell guard. Replace the
    # former stacked turntable/U joining layers by one sloping load web.
    allowed=box('retain_upper_yoke',(0,0,hz+40),(180,180,2*(hz+40-z1)))
    journal_bottom=bounds(o)[2][0]-.01
    union(allowed,cyl('retain_journal',(0,0,(journal_bottom+z1)/2),S['journal_keep_radius_mm'],z1-journal_bottom))
    wedge=plate('continuous_yoke_web', [(-S['floor_lower_half_width_mm'],z0),
                  (S['floor_lower_half_width_mm'],z0),(S['floor_upper_half_width_mm'],z1),
                  (-S['floor_upper_half_width_mm'],z1)],0,S['floor_depth_mm'])
    union(allowed,clone(wedge,'web_boundary'))
    # The guard is an intentional light-control skin; it is not a deep cup.
    guard=clone(o,'keep_thin_shadow_skin')
    boolean(guard,sphere('exclude_inner_structure',(0,0,hz),S['guard_preserve_radius_mm']))
    clip_z(guard,-500,z1+2);union(allowed,guard)
    union(allowed,box('keep_front_servo_seat',(0,18,hz-24),(12,10,26)))
    intersect(o,allowed);union(o,wedge)
    # One deliberate central clearance: body-fixed reaction hardware passes
    # through the rotating support. Bearing journal lower down is unchanged.
    boolean(o,cyl('reaction_upper_clear',(0,0,(hz-38.5+z1+1)/2),13.5,z1+1-(hz-38.5)))
    boolean(o,cyl('reaction_stem_clear',(0,0,(z0+hz-38.5)/2),
                  P['belly_relayout']['reaction_stem_clearance_radius_mm'],hz-38.5-z0+.02))
    boolean(o,clone(obj('Yaw_Servo'),'actual_yaw_case_clear'))
    b=source_build()
    for a,c in zip(yaw_head_lead_points(),yaw_head_lead_points()[1:]):
        boolean(o,b.beam('yaw_harness_pass',a,c,2.5))
    for angle in range(-20,26,5):
        route=clone(obj('Screen_Lead'),'screen_route_sweep')
        route.matrix_world=Matrix.Translation((0,0,hz))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation((0,0,-hz))@route.matrix_world
        SOLIDS.pop(route.name,None);bpy.context.view_layer.update();boolean(o,route)
    module(o,'连续底座俯仰U托 / 一体Yaw轴颈','yaw',
           'U front/back face on bed; review bearing finish and local servo-seat support',
           'One tapered lower load web replaces stacked former bolted joining layers. '
           'Bilateral bearings, servo seats, fixed-reaction passage, short wire guide and compact yaw stops remain.',
           (0,-35,80))


def apply_head_cleanup():
    if not S.get('enabled'):return
    before={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in IDS}
    for n in IDS:archive(obj(n))
    low_cradle();plain_face_returns();continuous_yoke_floor()
    for n in IDS:
        o=obj(n);o.data.materials.clear();o.data.materials.append(MATS['frame'])
        o['head_cleanup_revision']='M1.24'
    after={n:{'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))} for n in IDS}
    save_json(ROOT/'reports/head_print_cleanup.json',{
        'revision':P['revision'],'before_revision':'V1.2-M1.23','status':'GENERATED_PENDING_VALIDATION',
        'before':before,'after':after,'changed_prints':IDS,
        'removed_features':['four obsolete rear acoustic holes and their high ears',
                            'stacked side-return blocks and vertical open recesses on display fork',
                            'former bolted turntable/U layered connection shapes'],
        'preserved':['hardware1:1 and positions','two head degrees of freedom','LCD3 vendor mounting locations',
                     'four removable face-side screws','bilateral pitch bearings','yaw journal and compact stops',
                     'camera location and optical10deg tilt','rear low CAM support allocation'],
        'robot_print_count_change':0,'fastener_count_change':0,
        'face_nut_change':'Four existing M2 nuts move1.3mm inward; nominal backing increases0.7 to2.0mm. No added fasteners or holes.',
        'limits':['Print strength and fatigue NOT_TESTED','CAM full package, retention and actual holes BLOCKED',
                  'FDM clearances and nut fits require trial prints']})
    changes=json.loads((ROOT/'reports/structure_changes.json').read_text())
    changes['after'].update(after);save_json(ROOT/'reports/structure_changes.json',changes)
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text())
    plan['head_cleanup']='Low rear U is open above the microphones. Bench-fit nuts in enclosed fork pockets, then four lateral face screws; original three LCD post datums and camera tilt retained. CAM permanent fastening awaits actual board dimensions.'
    save_json(ROOT/'reports/module_assembly.json',plan)
    print('HEAD_CLEANUP_COMPLETE',flush=True)
