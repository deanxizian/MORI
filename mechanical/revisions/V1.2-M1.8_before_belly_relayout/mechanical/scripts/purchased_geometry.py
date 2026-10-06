"""Vendor geometry and honest evidence labels, applied before assembly parenting."""
import hashlib
from common import *


def remove_generated(name):
    o = bpy.data.objects.get(PREFIX + name)
    if o is not None:
        assert o.get('mori_owner') == OWNER
        SOLIDS.pop(o.name, None)
        bpy.data.objects.remove(o, do_unlink=True)


def finish_reference(o, label, fidelity, source_ids=(), group='pitch', mat='pcb'):
    finish(o, 'PURCHASED_REFERENCE', label, mat, group, False,
           note='Manufacturer geometry; physical revision, mating cables and assembly qualification remain pending')
    o['data_status'] = 'VENDOR_DOCUMENTED'
    o['model_fidelity'] = fidelity
    o['dimension_source_ids'] = list(source_ids)
    o['measured_unit'] = False
    o['mounting_release'] = False
    return o


def apply_purchased_geometry():
    hz = D['head_z']
    dp = P['display']
    screen_z = hz + dp['z_from_head_mm']
    front = dp['vendor_front_y_from_head_mm']
    cache_path = PROJECT / dp['vendor_mesh_source']
    cache = json.loads(cache_path.read_text())
    step_path = PROJECT / cache['source_file']
    assert hashlib.sha256(step_path.read_bytes()).hexdigest() == cache['source_sha256']
    assert cache['units'] == 'mm' and cache['scale_factor'] == 1.0
    # A proper rigid rotation (determinant +1), never scaling to fit.
    rotation = np.array([[-1., 0, 0], [0, 0, -1.], [0, -1., 0]])
    offset = np.array([0., front - .7, screen_z])
    solids, raw_vertices, raw_faces, proxy_sources = [], [], [], []
    for item in cache['solids']:
        v = np.array(item['vertices_mm'], dtype=np.float64) @ rotation.T + offset
        f = np.array(item['triangles'], dtype=np.uint64)
        m = manifold.Manifold(manifold.Mesh64(v, f))
        if m.status() != manifold.Error.NoError:
            # Preserve every source triangle for display. These two connector
            # subsolids have tessellation defects; do not pretend they passed
            # exact solid tests or delete them to obtain a PASS.
            bb = item['cad_bounds_xyz_mm']
            corners = np.array([[x,y,z] for x in bb[0] for y in bb[1] for z in bb[2]]) @ rotation.T + offset
            lo, hi = corners.min(axis=0)-.001, corners.max(axis=0)+.001
            m = manifold.Manifold.cube((hi-lo).tolist(), True).translate(((hi+lo)/2).tolist())
            proxy_sources.append({'CAD_solid_index':item['index'],'error':'NotManifold tessellation',
                                  'conservative_bounds_xyz_mm':list(zip(lo.tolist(),hi.tolist()))})
        solids.append(m)
        raw_faces.extend((f + len(raw_vertices)).tolist())
        raw_vertices.extend(v.tolist())
    occupied = manifold.Manifold.batch_boolean(solids, manifold.OpType.Add)
    if occupied.status() != manifold.Error.NoError:
        raise RuntimeError('Vendor LCD occupied-volume union failed')
    # Keep original component tessellations hidden, alongside the unmodified STEP.
    datum = mesh('LCD35079_Original_CAD', raw_vertices, raw_faces)
    move_collection(datum, 'DATUMS')
    datum['role'] = 'construction'
    datum['source_sha256'] = cache['source_sha256']
    datum['cad_solid_count'] = cache['solid_count']
    for name in ['Display_Module', 'Display_PCB', 'Display_Connector', 'Display_Outline_Allocation']:
        remove_generated(name)
    data = occupied.to_mesh64()
    proxy = mesh('Display_Collision_Proxy', data.vert_properties[:, :3].tolist(), data.tri_verts.tolist())
    finish(proxy,'KEEP_OUT','LCD碰撞代理 / 两接插件为原厂保守外接框','keepout','pitch',False,role='validation_proxy')
    display = mesh('Display_PCB', raw_vertices, raw_faces)
    display['preserve_vendor_tessellation'] = True
    finish_reference(display, 'LCD35079 原厂完整总成 / 含背板接插件', 'VENDOR_CAD',
                     ['LCD35079_STEP', 'LCD35079_DRAWING'], mat='dark')
    display['component_id'] = 'display'
    display['source_sha256'] = cache['source_sha256']
    display['source_revision'] = cache['source_revision']
    display['source_transform_rotation'] = rotation.tolist()
    display['source_transform_translation_mm'] = offset.tolist()
    display['source_scale_factor'] = 1.0
    display['validation_proxy'] = PREFIX+'Display_Collision_Proxy'
    display['validation_proxy_limit'] = 'Source CAD solids107/108 tessellate non-manifold. Conservative bounding solids are used ONLY for checks; original CAD mesh is preserved in all renders. Exact connector-solid check NOT_TESTED.'
    display['documented_dimension_conflict'] = 'CAD depth9.35 vs PDF9.1 reference; hole centers differ up to0.06mm. Match purchased revision before hole freeze.'
    display.data.materials.append(MATS['pcb'])
    for poly in display.data.polygons:
        cy = sum(display.data.vertices[i].co.y for i in poly.vertices) / len(poly.vertices)
        poly.material_index = 0 if cy > front - 3.5 else 1
    # Current actual occupied AABB is a hidden review aid, not a substitute solid.
    bb = bounds(display)
    aid = box('Display_Outline_Allocation', [(a+b)/2 for a,b in bb], [b-a for a,b in bb])
    finish(aid, 'KEEP_OUT', '原厂圆屏 CAD 外接框（仅辅助）', 'keepout', 'pitch', False, role='keepout')

    # Replace the generic ring with a rear spider located from the vendor CAD's
    # three threaded posts. Clearance holes are explicitly trial FDM dimensions.
    remove_generated('Display_Frame')
    back = dp['vendor_mount_back_y_from_head_mm']
    fy = back - 1.4
    frame = ring('Display_Frame', (0, fy, screen_z), 29.6, 27.1, 2, 'Y')
    def beam(a, b, radius):
        a, b = Vector(a), Vector(b)
        o = cyl('vendor_frame_beam', (a+b)/2, radius, (b-a).length)
        o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        return o
    holes = INTERFACES['components']['display']['vendor_dimensions']['cad_post_center_xz_from_screen_mm']
    for i, (x, z) in enumerate(holes):
        norm = math.hypot(x, z)
        # A flat arm remains behind the mounting face. A round 4.8mm beam
        # would intrude into the vendor posts even with a thin mounting pad.
        a = Vector((x, fy, screen_z+z))
        b = Vector((x/norm*28.3, fy, screen_z+z/norm*28.3))
        arm = box('flat_mount_arm', (a+b)/2, (4.8,2,(b-a).length))
        direction = b-a
        arm.rotation_euler = (0,math.atan2(direction.x,direction.z),0)
        bpy.context.view_layer.update()
        union(frame, arm)
        union(frame, cyl('mount_pad', (x, fy, screen_z+z), 3.4, 2, 'Y'))
        boolean(frame, cyl('trial_M2_clearance', (x, fy, screen_z+z), 1.2, 8, 'Y'))
        axis = cyl('LCD_M2_Axis_'+str(i), (x, back, screen_z+z), .2, 12, 'Y')
        move_collection(axis, 'DATUMS'); axis['role'] = 'construction'
    for sign in [-1, 1]:
        union(frame, beam((sign*25, fy, screen_z+13.2), (sign*26, 3, hz+34.5), 2))
    boolean(frame, clone(bpy.data.objects[PREFIX+'Pitch_Cradle'], 'frame_cradle_seat'))
    finish(frame, 'PRINTABLE', '按原厂三柱位置的屏幕后支架 / 试配', 'frame', 'pitch', True,
           note='M2 centers follow STEP;2.4mm FDM clearance holes are trial values. PDF rounding/version mismatch and screw length/thread engagement pending.')
    frame['interface_source_ids'] = ['LCD35079_STEP', 'LCD35079_DRAWING']
    frame['mounting_release'] = False

    # Use the documented board outline, retaining unknown populated height as a
    # clearly labeled allocation. R2.25 is the OUTER corner, not the hole radius.
    remove_generated('CAM_Mainboard')
    l = P['layout']; cx, cy, cz = l['cam_board_center_from_head_mm']; cz += hz
    w, depth, h = l['cam_board_allocation_xyz_mm']; rad = 2.25
    outline = []
    for ox, oz, start in [(w/2-rad,h/2-rad,0),(-w/2+rad,h/2-rad,90),(-w/2+rad,-h/2+rad,180),(w/2-rad,-h/2+rad,270)]:
        for angle in range(start, start+91, 10):
            a = math.radians(angle)
            outline.append((cx+ox+rad*math.cos(a), cz+oz+rad*math.sin(a)))
    n = len(outline)
    verts = [(x,y,z) for y in [cy-depth/2,cy+depth/2] for x,z in outline]
    faces = [tuple(range(n-1,-1,-1)), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cam = mesh('CAM_Mainboard', verts, faces); recalc(cam)
    finish(cam, 'PLACEHOLDER', 'CAM33700板框37×37已核 / 装件厚度待测', 'unknown', 'pitch', False,
           note='X/Z37 and outerR2.25 vendor documented.12mm Y is ONLY a draft occupied-height reserve. No final holes or connector coordinates.')
    cam['model_fidelity'] = 'PARTIAL_VENDOR_DIMENSIONS'; cam['component_id'] = 'interaction_cam'
    cam['dimension_source_ids'] = ['CAM33700_DRAWING']; cam['unknown_dimensions'] = ['total_depth','hole_diameter','connector_geometry','microphone_coordinates','antenna_coordinates']
    for x in [-16.3,16.3]:
        for z in [-16.3,16.3]:
            o = cyl('CAM_Hole_Center_'+str(x)+'_'+str(z), (cx+x,cy,cz+z), .2, depth+6, 'Y')
            move_collection(o,'DATUMS');o['role']='construction';o['diameter_status']='Axis marker only, hole diameter UNKNOWN'
    # The USB is on the board's bottom edge in the product photo. Old rearward
    # connector geometry was invented: retire it to explicitly unverified keepout.
    usb = bpy.data.objects[PREFIX+'CAM_USB_Connector']
    usb.location = (cx,cy,cz-h/2-2)
    usb.dimensions = (10,8,5)
    active(usb);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    move_collection(usb,'KEEP_OUT');usb['role']='keepout';usb['category']='PLACEHOLDER'
    usb['label_zh']='CAM底边USB候选插接空间 / 精确尺寸待核'
    usb['model_fidelity']='ALLOCATION_ONLY'
    clear = bpy.data.objects[PREFIX+'CAM_USB_Plug_Clear']
    clear.location=(cx,cy,cz-h/2-20);clear.dimensions=(16,10,30)
    active(clear);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)

    # Show unknown internals as allocations, not realistic-looking green boards.
    ids = {'Battery':'battery','MCU_Motion':'motion_mcu','Body_IMU':'body_imu',
           'Power_Module':'power_aggregate','USB_Charge':'usb_charge','Speaker':'speaker',
           'Camera_PCB':'interaction_cam_camera','Camera_Lens':'interaction_cam_camera'}
    for name, cid in ids.items():
        o = bpy.data.objects[PREFIX+name]
        o['model_fidelity']='ALLOCATION_ONLY';o['component_id']=cid;o['mounting_release']=False
        o['unknown_dimensions']='Selected product/revision, installed shape and/or connectors not dimensioned'
        if name not in ['Camera_Lens','Speaker']:
            o.data.materials.clear();o.data.materials.append(MATS['unknown'])
        if '待' not in o['label_zh']:o['label_zh'] += ' / 待选或待实物尺寸'
    for o in parts():
        if o.get('actuator_id') or o.name.startswith(PREFIX+'S288_Output_') or o.name in [PREFIX+'Yaw_Output',PREFIX+'Pitch_Output']:
            o['model_fidelity']='VENDOR_DIMENSIONED_SIMPLIFICATION'
            o['documented_fields']='Manufacturer nominal body, ears and output bounds; plugs/cables and mating interface not fully documented'
            o['dimension_source_ids']=['S288_DRAWING' if 'S288_Output_' in o.name or 'Drive_Motor_' in o.name else 'SCS0009_DRAWING']
            o['mounting_release']=False
        elif o.get('category') in ['PLACEHOLDER','PURCHASED_REFERENCE'] and not o.get('model_fidelity'):
            o['model_fidelity']='ALLOCATION_ONLY'
            o['mounting_release']=False
            if o.get('category') == 'PURCHASED_REFERENCE':
                move_collection(o,'PLACEHOLDER');o['category']='PLACEHOLDER'
    # No object in this project has yet been physically measured.
    for o in parts():o['measured_unit']=False
    save_json(ROOT/'reports/vendor_lcd_import.json', {
        'status':'PASS', 'source_sha256':cache['source_sha256'], 'solid_count':len(solids),
        'exact_collision_mesh_status':'BLOCKED' if proxy_sources else 'PASS',
        'conservative_connector_proxies':proxy_sources,
        'original_step_preserved':True, 'proper_rotation_determinant':float(np.linalg.det(rotation)),
        'source_scale_factor':1.0, 'linear_tessellation_deflection_mm':cache['linear_deflection_mm'],
        'transform_rotation':rotation.tolist(), 'transform_translation_mm':offset.tolist(),
        'imported_bounds_xyz_mm':bounds(display), 'source_unit':'mm',
        'limits':'CAD import integrity only. Two connector tessellations are non-manifold; exact all-solid fit is BLOCKED, not silently counted PASS. Mating cables, as-bought revision and dimensional tolerances NOT_TESTED.'})


def audit_purchased_geometry():
    source_checks = []
    for sid, source in INTERFACES['vendor_geometry_sources'].items():
        path = PROJECT/source['path']
        source_checks.append({'source':sid,'unchanged':hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']})
    original = bpy.data.objects[PREFIX+'LCD35079_Original_CAD']
    actual = bpy.data.objects[PREFIX+'Display_PCB']
    a, b = bounds(original), bounds(actual)
    delta = max(abs(a[i][j]-b[i][j]) for i in range(3) for j in range(2))
    unsupported_measured = [o.name for o in parts() if o.get('data_status')=='MEASURED' or o.get('measured_unit')]
    missing_fidelity = [o.name for o in parts() if o.get('category') in ['PURCHASED_REFERENCE','PLACEHOLDER'] and not o.get('model_fidelity')]
    integrity = {'source_hashes':source_checks,'CAD_vs_original_bound_error_mm':delta,
                 'source_scale_factor':actual.get('source_scale_factor'),
                 'unsupported_MEASURED_objects':unsupported_measured,'unlabeled_reference_objects':missing_fidelity}
    hardware_bytes = (PROJECT/'contracts/components.json').read_bytes()
    hardware = json.loads(hardware_bytes)
    hardware_provenance = {'revision':hardware['revision'], 'sha256':hashlib.sha256(hardware_bytes).hexdigest(),
                           'mechanically_reviewed_revision':INTERFACES['hardware_component_revision_read'],
                           'populated_assembly_fit':'BLOCKED',
                           'note':INTERFACES.get('hardware_read_scope',{}).get('note','Complete populated hardware has not been qualified.')}
    hardware_provenance['matches_reviewed_input'] = hardware_provenance['sha256']==INTERFACES['hardware_component_sha256'] and hardware['revision']==INTERFACES['hardware_component_revision_read']
    components = hardware['components']
    unselected = [c['id'] for c in components if c.get('dimensions_mm') is None and c['id'] not in ['shipping','printing']]
    rows = [{'id':o.name.removeprefix(PREFIX),'label':o.get('label_zh'),'category':o.get('category'),
             'model_fidelity':o.get('model_fidelity'),'data_status':o.get('data_status'),
             'measured_unit':False,'mounting_release':False,
             'bounds_xyz_mm':bounds(o),'unknown_dimensions':o.get('unknown_dimensions','See source/interface notes')}
            for o in parts() if o.get('category') in ['PURCHASED_REFERENCE','PLACEHOLDER']]
    result = {'revision':P['revision'],'integrity_status':'PASS' if delta<.02 and not unsupported_measured and not missing_fidelity and all(v['unchanged'] for v in source_checks) and actual.get('source_scale_factor')==1.0 and hardware_provenance['matches_reviewed_input'] else 'FAIL',
              'all_purchased_parts_complete':'BLOCKED','integrity_checks':integrity,'hardware_contract_provenance':hardware_provenance,
              'unselected_component_ids':unselected,'parts':rows,
              'note':'Some hardware-owned dimension fields are still null although mechanical now has partial vendor facts; see ADR-MECH-013. No source says these parts were physically measured. Orange geometry is an allocation, never an as-built board.'}
    save_json(ROOT/'reports/purchased_geometry_audit.json',result)
    return result
