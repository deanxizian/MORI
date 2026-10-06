"""Front/rear body shells derived from the current shells and shared mother skin.

No purchased geometry is changed. Local locator dimensions are trial PA12
clearances, not supplier tolerances or strength qualification.
"""
from common import *
from interface_completion import axial


def boxm(lo, hi):
    return manifold.Manifold.cube((np.asarray(hi) - lo).tolist()).translate(lo)


def make_forms(upper, lower, outer, inner, q):
    skin = outer - inner
    original = upper + lower
    zones = manifold.Manifold()
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            xx = sorted(sx * v for v in q['retired_seam_zone_abs_x_mm'])
            yy = sorted(sy * v for v in q['retired_seam_zone_abs_y_mm'])
            zones += boxm([xx[0], yy[0], 0], [xx[1], yy[1], q['retired_seam_zone_top_z_mm']])
    joined = (original - zones) + (skin ^ zones)
    halfgap = q['gap_mm'] / 2
    fill = q['old_seam_fill_halfheight_mm']
    joined += skin ^ boxm([-200, -200, D['body_z'] - fill], [200, 200, D['body_z'] + fill])
    for x, y in P['shell_service']['frame_mount_xy_mm']:
        joined -= axial(q['tool_port_diameter_mm'] / 2, q['tool_port_length_mm'],
                        [x, y, q['tool_port_center_z_mm']], [0, 0, 1])
    front = joined ^ boxm([-200, halfgap, 0], [200, 200, 300])
    rear = joined ^ boxm([-200, -200, 0], [200, -halfgap, 300])
    base = {'Body_Front': front, 'Body_Rear': rear}
    locators = []
    a = q['locators']
    if a['enabled']:
        for x in a['center_x_mm']:
            root = boxm([x-a['root_width_mm']/2, halfgap, 0],
                        [x+a['root_width_mm']/2, a['root_end_y_mm'], a['tongue_top_z_mm']]) ^ outer
            tongue = boxm([x-a['tongue_width_mm']/2, a['tongue_tip_y_mm'], a['tongue_bottom_z_mm']],
                          [x+a['tongue_width_mm']/2, a['root_end_y_mm'], a['tongue_top_z_mm']])
            # A short, deliberate insertion lead on the tongue's upper and
            # lower tip edges; no decorative chamfers elsewhere.
            lead = a['tip_lead_mm']
            tip = a['tongue_tip_y_mm']
            if lead:
                verts=[]
                for xx in [x-a['tongue_width_mm']/2, x+a['tongue_width_mm']/2]:
                    verts += [[xx, tip, a['tongue_bottom_z_mm']+lead],
                              [xx, tip, a['tongue_top_z_mm']-lead],
                              [xx, tip+lead, a['tongue_bottom_z_mm']],
                              [xx, tip+lead, a['tongue_top_z_mm']],
                              [xx, a['root_end_y_mm'], a['tongue_bottom_z_mm']],
                              [xx, a['root_end_y_mm'], a['tongue_top_z_mm']]]
                tongue = manifold.Manifold.hull_points(verts)
            outside = boxm([x-a['socket_outer_width_mm']/2, a['socket_back_y_mm'], 0],
                           [x+a['socket_outer_width_mm']/2, -halfgap, a['socket_top_z_mm']]) ^ outer
            pocket = boxm([x-a['tongue_width_mm']/2-a['side_clearance_mm'],
                           a['tongue_tip_y_mm']-a['end_clearance_mm'],
                           a['tongue_bottom_z_mm']-a['vertical_clearance_mm']],
                          [x+a['tongue_width_mm']/2+a['side_clearance_mm'], halfgap+.1,
                           a['tongue_top_z_mm']+a['vertical_clearance_mm']])
            front += root + tongue
            rear = (rear + outside) - pocket
            locators.append(dict(center_x_mm=x, male=root+tongue, female=outside-pocket,
                                 pocket=pocket, external=outside, tongue=tongue))
    return {'Body_Front': front, 'Body_Rear': rear}, base, locators


def apply_body_shell_split():
    q = P.get('body_front_rear_split', {})
    if not q.get('enabled'):
        return
    from validate import Solid
    from monocoque_structure import obj, source_build
    from assembly_issue_fixes import replace
    assembled()
    b = source_build()
    o = b.body_outer('split_outer'); outer = Solid(o).m
    bpy.data.objects.remove(o, do_unlink=True)
    o = b.body_outer('split_inner', P['shell_thickness_mm']); inner = Solid(o).m
    bpy.data.objects.remove(o, do_unlink=True)
    forms, _, _ = make_forms(Solid(obj('Body_Upper')).m, Solid(obj('Body_Lower')).m, outer, inner, q)
    rows = []
    for old, new, label, direction in [('Body_Upper', 'Body_Front', '身体前壳', 1),
                                        ('Body_Lower', 'Body_Rear', '身体后壳', -1)]:
        o, ops = replace(old, forms[new])
        o.name = PREFIX + new
        o['label_zh'] = label
        o['explode_offset_mm'] = [0, direction * 90, 0]
        o['body_split_revision'] = P['revision']
        o['functional_purpose'] = 'Front/rear enclosure with integral lower locating keys; original frame bolts retain each half.'
        o['interface_status'] = 'PROTOTYPE / UNVALIDATED; PA12 sliding clearance 0.3 mm per side; strength and physical fit NOT_TESTED'
        o['print_orientation_candidate'] = 'PA12 powder-bed; keep locating pockets and frame insert bores clean; orientation/fit coupon pending supplier review'
        # Flat seating/key/parting faces stay flat. Only the mother skin is smooth.
        center = Vector((0, 0, D['body_z']))
        for f in o.data.polygons:
            radial = f.center - center
            f.use_smooth = radial.length > 70 and abs(f.normal.dot(radial.normalized())) > .95
        rows.append(dict(id=new, replaced=old, mesh_repairs=ops, volume_mm3=forms[new].volume()))
    retired = []
    for i in range(4):
        for stem in ['Shell_Screw_', 'Shell_Insert_']:
            n = stem + str(i); o = obj(n)
            if o.get('mori_owner') != OWNER:
                raise RuntimeError('Unowned retired part: ' + n)
            bpy.data.objects.remove(o, do_unlink=True); retired.append(n)
    save_json(ROOT/'reports/body_front_rear_split.json', dict(revision=P['revision'],
        status='NOT_TESTED', configuration='config/geometry.json#/body_front_rear_split',
        parts=rows, retired_fasteners=retired, printed_part_count_delta=0,
        source='Approved front/rear split with two integral lower sliding locators',
        physical_fit='NOT_TESTED', full_harness='BLOCKED', manufacturing_release=False))
    print('BODY_FRONT_REAR_SPLIT_APPLIED', flush=True)
