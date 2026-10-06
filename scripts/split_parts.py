"""Split the existing MORI assembly into real, independently editable part files.

Run inside Blender: blender --background --python scripts/split_parts.py
                    -- --output models/parts_v2
Only reads the source assembly. An existing nonempty output is never overwritten.
No third-party Python packages or Blender add-ons are required.
"""
import argparse
import collections
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

OWNER = 'mori_parametric_v1'
PREFIX = 'MORI__'
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
VIEW_DIRECTION = Vector((6, -9, 7)).normalized()
VIEW_ROTATION = (-VIEW_DIRECTION).to_track_quat('-Z', 'Y')
RIGHT = VIEW_ROTATION @ Vector((1, 0, 0))
UP = VIEW_ROTATION @ Vector((0, 1, 0))
CATEGORY_ZH = {'PRINTABLE': '自制结构件 / 原型',
               'PURCHASED_REFERENCE': '外购件参考形状',
               'PLACEHOLDER': '硬件或运动空间占位 / 待选型'}
TOLERANCE_MM = 0.0001


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def bounds(vertices):
    return [[min(v[i] for v in vertices), max(v[i] for v in vertices)] for i in range(3)]


def mesh_vertices(obj):
    return [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]


def part_id(obj):
    return obj.get('source_part_id', obj.name.removeprefix(PREFIX))


def folder_for(name, role):
    if role == 'coupon':
        return '08_test_coupons'
    if name in {'Head_Front_Shell', 'Head_Rear_Shell', 'Body_Upper_Shell',
                'Body_Lower_Shell', 'Black_Bezel', 'Face_Protector', 'Display_Mount_Frame'}:
        return '01_shells_and_face'
    if name.startswith(('Tire_', 'Wheel_Hub_', 'Wheel_Cap_', 'Independent_Axle_')):
        return '02_wheels'
    if name in {'Load_Frame', 'Battery_Tray', 'Head_Bearing_Carrier', 'Head_Turntable',
                'Servo_Mount', 'Controller_Mount', 'Driver_Mount', 'Imu_Mount'} or name.startswith(('Motor_Mount_', 'Cable_Guide_')):
        return '03_frame_and_mounts'
    if name.startswith(('Head_', 'Servo_', 'Yaw_')):
        return '04_head_joint'
    if name.startswith(('Motor_', 'Encoder_', 'Pulley_', 'Belt_', 'Wheel_Bearing_')):
        return '05_drive_train'
    if name.startswith(('Body_Screw_', 'Body_Insert_', 'Frame_Screw_', 'Frame_Insert_', 'Battery_Hanger_')) or name == 'Battery_Strap':
        return '07_fasteners_and_strap'
    return '06_electronic_envelopes'


def set_scene(scene):
    bpy.context.window.scene = scene
    # New scenes must have an evaluated view layer before libraries.write in Blender 5.2.
    bpy.context.view_layer.update()


def new_scene(name):
    scene = bpy.data.scenes.new(name)
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene['units_contract'] = '1 coordinate = 1 mm; scale is 1,1,1'
    scene['model_status'] = 'PROTOTYPE / UNVALIDATED hardware interfaces'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new(name + '_World')
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.82, 0.85, 0.88, 1)
    bg.inputs['Strength'].default_value = 0.8
    camera_bg = scene.world.node_tree.nodes.new('ShaderNodeBackground')
    camera_bg.inputs['Color'].default_value = (0.022, 0.037, 0.054, 1)
    camera_bg.inputs['Strength'].default_value = 1
    ray = scene.world.node_tree.nodes.new('ShaderNodeLightPath')
    mix = scene.world.node_tree.nodes.new('ShaderNodeMixShader')
    world_output = next(n for n in scene.world.node_tree.nodes if n.type == 'OUTPUT_WORLD')
    scene.world.node_tree.links.new(ray.outputs['Is Camera Ray'], mix.inputs[0])
    scene.world.node_tree.links.new(bg.outputs[0], mix.inputs[1])
    scene.world.node_tree.links.new(camera_bg.outputs[0], mix.inputs[2])
    scene.world.node_tree.links.new(mix.outputs[0], world_output.inputs['Surface'])
    set_scene(scene)
    return scene


def new_collection(scene, name):
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    return coll


def add_camera(scene, center, scale, resolution=(1000, 1000)):
    view = new_collection(scene, 'VIEW_Camera_and_Lights')
    data = bpy.data.cameras.new(scene.name + '_Camera')
    cam = bpy.data.objects.new(scene.name + '_Camera', data)
    view.objects.link(cam)
    cam.rotation_euler = VIEW_ROTATION.to_euler()
    cam.location = Vector(center) + VIEW_DIRECTION * max(600, scale * 3)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = scale
    cam.data.clip_start = 0.1
    cam.data.clip_end = 30000
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene['view_center_mm'] = list(center)
    for label, direction, power in [('Key', (-1, -1, 1.6), 30), ('Fill', (1, -0.2, 0.8), 14), ('Rim', (0, 1, 1.8), 25)]:
        light = bpy.data.lights.new(scene.name + '_' + label, 'AREA')
        light.energy = power * scale * scale
        light.size = scale * 1.2
        obj = bpy.data.objects.new(light.name, light)
        view.objects.link(obj)
        obj.location = Vector(center) + Vector(direction) * scale
        obj.rotation_euler = (Vector(center) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return cam


def copy_normalized(source, record, collection):
    obj = source.copy()
    obj.data = source.data.copy()
    obj.animation_data_clear()
    obj.data.animation_data_clear()
    obj.parent = None
    obj.constraints.clear()
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = Matrix.Identity(4)
    obj.data.transform(Matrix.Translation(-Vector(record['assembly_offset_mm'])) @ source.matrix_world)
    obj.data.update()
    obj.name = record['code'] + '__' + record['id']
    obj.data.name = obj.name + '_Mesh'
    obj.hide_render = False
    obj.hide_viewport = False
    obj['source_part_id'] = record['id']
    obj['part_code'] = record['code']
    obj['label_zh'] = record['name_zh']
    obj['measured_dimensions_mm'] = record['dimensions_mm']
    obj['assembly_offset_mm'] = record['assembly_offset_mm']
    obj['part_file'] = record['blend_file']
    obj['coordinate_note'] = 'XY bbox center = 0; minimum Z = 0. Translation only; original orientation retained.'
    obj['source_world_matrix_json'] = json.dumps(record['source_world_matrix'])
    collection.objects.link(obj)
    obj.hide_set(False)
    return obj


def make_readme(record):
    return '\n'.join([
        'MORI — 独立零件模型',
        f"{record['code']} / {record['name_zh']} / {record['id']}",
        f"分类：{CATEGORY_ZH[record['category']]}",
        '实测 XYZ 尺寸：' + ' × '.join(f'{x:.4f}' for x in record['dimensions_mm']) + ' mm',
        '1 坐标单位 = 1 mm；对象缩放为 1。原始装配朝向保留；XY 包围盒居中，最低点 Z=0。',
        '此坐标归一化不代表推荐打印朝向。',
        '原装配坐标 = 本文件网格坐标 + assembly_offset_mm（在对象自定义属性中）。',
        'Tab 可编辑网格；N → Item 查看毫米尺寸；Object → Custom Properties 查看零件信息。',
        '独立文件是本次总装的几何快照；手工修改不会自动写回原参数或总装。',
        '参数化修改请运行原项目生成脚本，然后重新拆件到新目录。',
        '接口说明：' + record['interface_status'],
        'STL 状态：' + ('原项目中的原型试打候选；仍需切片与实测。' if record['candidate_stl'] else '未作为原型 STL 候选交付。'),
    ])


def text_block(name, body):
    tx = bpy.data.texts.new(name)
    tx.write(body)
    tx.use_fake_user = True
    return tx


def normalized_part_file(source, record, output):
    scene = new_scene(record['code'] + '_' + record['id'])
    coll = new_collection(scene, 'PART_' + record['code'])
    obj = copy_normalized(source, record, coll)
    center = (0, 0, record['dimensions_mm'][2] / 2)
    scale = max(10, max(record['dimensions_mm']) * 1.75)
    add_camera(scene, center, scale)
    scene['source_part_id'] = record['id']
    scene['source_blend_sha256'] = record['source_blend_sha256']
    tx = text_block(record['code'] + '_README', make_readme(record))
    obj.select_set(True)
    scene.view_layers[0].objects.active = obj
    bpy.context.view_layer.update()
    path = output / record['blend_file']
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(str(path), {scene, tx}, compress=True)
    return obj, scene


def label_material():
    mat = bpy.data.materials.new('Parts_label_ink')
    mat.diffuse_color = (0.61, 0.76, 0.84, 1)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    node = mat.node_tree.nodes.new('ShaderNodeEmission')
    node.inputs['Color'].default_value = (0.61, 0.76, 0.84, 1)
    output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node.outputs[0], output.inputs['Surface'])
    return mat


def text_label(coll, name, text, position, size, mat):
    data = bpy.data.curves.new(name, 'FONT')
    data.body = text
    data.size = size
    data.align_x = 'CENTER'
    data.align_y = 'TOP'
    data.space_line = 1.2
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.location = position
    obj.rotation_euler = VIEW_ROTATION.to_euler()
    obj.data.materials.append(mat)
    obj['role'] = 'annotation'
    obj.hide_select = True
    return obj


def create_board(scene_name, title, records, normalized, cols, cell, mat):
    scene = new_scene(scene_name)
    groups = {}
    labels = new_collection(scene, 'LABELS_Reference_only')
    rows = math.ceil(len(records) / cols)
    dx, dy = cell
    total_height = rows * dy + 120
    for index, record in enumerate(records):
        folder = record['folder']
        if folder not in groups:
            groups[folder] = new_collection(scene, folder)
        obj = normalized[record['id']].copy()
        obj.name = record['code'] + '__' + record['id'] + '__LAYOUT'
        groups[folder].objects.link(obj)
        x = (index % cols - (cols - 1) / 2) * dx
        y = ((rows - 1) / 2 - index // cols) * dy - 25
        center = RIGHT * x + UP * y
        obj.location = center - Vector((0, 0, record['dimensions_mm'][2] / 2))
        obj['layout_translation_mm'] = list(obj.location)
        short = record['id'].replace('_PLACEHOLDER', '').replace('_ENVELOPE', '')
        if len(short) > 27:
            short = short.replace('Charger_Regulator', 'Charger_Reg.').replace('Head_Bearing', 'Head_Brg.')
        size = 8.5 if cols <= 5 else 6
        dimensions = ' x '.join(f'{v:.1f}' for v in record['dimensions_mm']) + ' mm'
        text_label(labels, record['code'] + '_Label', record['code'] + '  ' + short + '\n' + dimensions,
                   center - UP * (dy * 0.35) + VIEW_DIRECTION * 100, size, mat)
    text_label(labels, title, title, UP * (total_height / 2 - 15) + VIEW_DIRECTION * 130, 23, mat)
    text_label(labels, title + '_Subtitle', f'{len(records)} separate meshes  /  actual scale  /  dimensions: X x Y x Z (mm)',
               UP * (total_height / 2 - 49) + VIEW_DIRECTION * 130, 8.5, mat)
    text_label(labels, title + '_Footer', 'MORI  /  PROTOTYPE  /  hardware interfaces pending verification',
               -UP * (total_height / 2 - 18) + VIEW_DIRECTION * 130, 7.5, mat)
    width = cols * dx + 60
    resolution = (1600, round(1600 * total_height / width))
    # ortho_scale is the longer image axis, not always its width.
    add_camera(scene, (0, 0, 0), max(width, total_height), resolution)
    scene['part_count'] = len(records)
    scene['layout_note'] = 'Positions separated for inspection; all meshes keep 1:1 millimetre dimensions.'
    bpy.context.view_layer.update()
    return scene


def create_assembly(records, normalized, source_scene):
    scene = new_scene('04_Assembly_Check')
    groups = {}
    for record in records:
        if record['role'] != 'part':
            continue
        if record['folder'] not in groups:
            groups[record['folder']] = new_collection(scene, record['folder'])
        obj = normalized[record['id']].copy()
        obj.name = record['code'] + '__' + record['id'] + '__ASSEMBLED'
        groups[record['folder']].objects.link(obj)
        obj.location = record['assembly_offset_mm']
    visuals = new_collection(scene, 'DISPLAY_CONTENT_Not_physical_parts')
    for source in source_scene.objects:
        if source.get('role') == 'display_content':
            obj = source.copy()
            obj.data = source.data.copy()
            obj.animation_data_clear()
            obj.parent = None
            obj.matrix_world = Matrix.Identity(4)
            obj.data.transform(source.matrix_world)
            visuals.objects.link(obj)
    add_camera(scene, (0, 0, 116), 290, (1000, 1000))
    scene['part_count'] = sum(r['role'] == 'part' for r in records)
    scene['note'] = 'Static reassembly from normalized meshes; linked mesh data with the part boards. Original assembly retains animation and controls.'
    bpy.context.view_layer.update()
    return scene


def configure_ui(scene):
    set_scene(scene)
    scene.tool_settings.use_snap = False
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            space.clip_start = 0.1
            space.clip_end = 30000
            space.shading.type = 'SOLID'
            space.shading.color_type = 'MATERIAL'
            space.shading.light = 'STUDIO'
            space.overlay.show_floor = False
            space.overlay.show_axis_x = False
            space.overlay.show_axis_y = False
            space.region_3d.view_rotation = VIEW_ROTATION
            space.region_3d.view_distance = scene.camera.data.ortho_scale * 1.3
            space.region_3d.view_location = Vector(scene.get('view_center_mm', (0, 0, 0)))
            space.region_3d.view_perspective = 'ORTHO'
            space.show_region_ui = True
    for obj in scene.objects:
        obj.select_set(False)
    meshes = [o for o in scene.objects if o.get('role') in ('part', 'coupon')]
    if len(meshes) == 1:
        meshes[0].select_set(True)
        scene.view_layers[0].objects.active = meshes[0]


def finish_native_file(path, active_scene_name=None):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    scene = bpy.data.scenes.get(active_scene_name) if active_scene_name else bpy.data.scenes[0]
    configure_ui(scene)
    bpy.context.preferences.filepaths.save_version = 0
    # A full native save includes a configured viewport and removes the library-file warning.
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)


def verify_object(obj, expected, location=None):
    assert obj.type == 'MESH'
    assert obj.parent is None and obj.animation_data is None and len(obj.constraints) == 0
    assert len(obj.modifiers) == 0
    assert max(abs(v - 1) for v in obj.scale) < 1e-6
    assert len(obj.data.vertices) == expected['vertex_count']
    assert [tuple(p.vertices) for p in obj.data.polygons] == expected['faces']
    actual = [tuple(v.co) for v in obj.data.vertices]
    error = max((Vector(a) - Vector(b)).length for a, b in zip(actual, expected['normalized_vertices']))
    assert error < TOLERANCE_MM, (obj.name, error)
    if location is not None:
        assert (obj.location - Vector(location)).length < TOLERANCE_MM
    return error


def validate_files(records, expected, output):
    results = []
    for i, record in enumerate(records):
        path = output / record['blend_file']
        finish_native_file(path)
        # Read the saved native file again: validation is against disk, not just in-memory objects.
        bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=True)
        assert len(bpy.data.scenes) == 1
        scene = bpy.context.scene
        assert abs(scene.unit_settings.scale_length - 0.001) < 1e-9
        meshes = [o for o in scene.objects if o.type == 'MESH']
        assert len(meshes) == 1, (record['id'], len(meshes))
        obj = meshes[0]
        assert obj['source_part_id'] == record['id']
        error = verify_object(obj, expected[record['id']], (0, 0, 0))
        verts = mesh_vertices(obj)
        bb = bounds(verts)
        dims = [hi - lo for lo, hi in bb]
        dimension_error = max(abs(a - b) for a, b in zip(dims, record['dimensions_mm']))
        assert dimension_error < TOLERANCE_MM
        assert abs(bb[2][0]) < TOLERANCE_MM
        assert abs(bb[0][0] + bb[0][1]) < TOLERANCE_MM
        assert abs(bb[1][0] + bb[1][1]) < TOLERANCE_MM
        restored = [Vector(v) + Vector(record['assembly_offset_mm']) for v in verts]
        restore_error = max((a - Vector(b)).length for a, b in zip(restored, expected[record['id']]['world_vertices']))
        assert restore_error < TOLERANCE_MM
        results.append({'id': record['id'], 'status': 'PASS', 'vertex_count': len(verts),
                        'face_count': len(obj.data.polygons), 'dimensions_mm': dims,
                        'max_vertex_error_mm': error, 'max_dimension_error_mm': dimension_error,
                        'max_reassembly_error_mm': restore_error, 'sha256': sha256(path)})
        if (i + 1) % 20 == 0:
            print(f'MORI verified {i + 1}/{len(records)} independent part files', flush=True)
    return results


def validate_master(output, records, expected):
    path = output / 'MORI_parts.blend'
    finish_native_file(path, '01_Custom_Parts')
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=True)
    counts = {}
    errors = []
    layout_objects = {}
    for scene in bpy.data.scenes:
        set_scene(scene)
        physical = [o for o in scene.objects if o.get('role') in ('part', 'coupon')]
        counts[scene.name] = len(physical)
        for obj in physical:
            key = obj['source_part_id']
            errors.append(verify_object(obj, expected[key]))
            if scene.name != '04_Assembly_Check':
                assert key not in layout_objects
                layout_objects[key] = obj
        if scene.name == '04_Assembly_Check':
            for obj in physical:
                record = next(r for r in records if r['id'] == obj['source_part_id'])
                assert (obj.location - Vector(record['assembly_offset_mm'])).length < TOLERANCE_MM
    assert set(layout_objects) == set(expected)
    for obj in bpy.data.scenes['04_Assembly_Check'].objects:
        if obj.get('role') == 'part':
            assert obj.data == layout_objects[obj['source_part_id']].data
    physical_records = [r for r in records if r['role'] == 'part']
    assert counts == {
        '01_Custom_Parts': sum(r['category'] == 'PRINTABLE' for r in physical_records),
        '02_Hardware_References': sum(r['category'] != 'PRINTABLE' for r in physical_records),
        '03_Test_Coupons': sum(r['role'] == 'coupon' for r in records),
        '04_Assembly_Check': len(physical_records),
    }, counts
    return {'status': 'PASS', 'scenes': counts, 'shared_meshes_between_layout_and_assembly': True,
            'max_vertex_error_mm': max(errors)}


def make_index(output, manifest):
    rows = manifest['parts']
    with (output / 'parts_index.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['编号', '零件名称', '原对象ID', '分类', '角色', 'X_mm', 'Y_mm', 'Z_mm', '原型STL候选', '独立Blender文件', '接口状态'])
        for r in rows:
            writer.writerow([r['code'], r['name_zh'], r['id'], CATEGORY_ZH[r['category']], r['role'],
                             *[round(v, 4) for v in r['dimensions_mm']], r['candidate_stl'], r['blend_file'], r['interface_status']])
    lines = ['# MORI 独立零件索引', '', '尺寸来自源文件装配姿态的网格顶点，单位 mm。重复螺钉、嵌件和轴承滚动体按实例分别编号；运动空间包络也保留原有占位标记。', '',
             '| 编号 | 零件 | 分类 | X × Y × Z / mm | 独立文件 |', '|---|---|---|---|---|']
    for r in rows:
        dims = ' × '.join(f'{d:.2f}' for d in r['dimensions_mm'])
        lines.append(f"| {r['code']} | {r['name_zh']} | {CATEGORY_ZH[r['category']]} | {dims} | [打开模型]({r['blend_file']}) |")
    (output / 'parts_index.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    default_source = SCRIPT_ROOT / 'models/MORI_assembly.blend'
    if not default_source.exists():
        default_source = SCRIPT_ROOT / 'source/MORI_assembly.blend'
    parser.add_argument('--source', type=Path, default=default_source)
    parser.add_argument('--output', type=Path, default=SCRIPT_ROOT / 'models/parts')
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args(argv)
    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Output is not empty. Choose a new output folder to preserve edited parts: ' + str(output))
    output.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    source_scene = bpy.data.scenes['MORI_Assembly']
    set_scene(source_scene)
    source_scene.frame_set(1)
    for key, prop in [('Head_Pivot', 'yaw_deg'), ('Wheel_L_Pivot', 'spin_deg'), ('Wheel_R_Pivot', 'spin_deg')]:
        obj = bpy.data.objects.get(PREFIX + key)
        if obj:
            obj[prop] = 0
            obj.update_tag()
    for coll in source_scene.collection.children:
        if coll.name == PREFIX + 'COUPONS':
            coll.hide_viewport = False
    bpy.context.view_layer.update()
    sources = [o for o in source_scene.objects if o.type == 'MESH' and o.get('mori_owner') == OWNER and o.get('role') in ('part', 'coupon')]
    sources.sort(key=lambda o: (folder_for(o.name.removeprefix(PREFIX), o['role']), o.name))
    records, expected, normalized, part_scenes = [], {}, {}, []
    for index, obj in enumerate(sources, 1):
        assert len(obj.modifiers) == 0, 'Source contains unbaked modifiers: ' + obj.name
        key = obj.name.removeprefix(PREFIX)
        world_vertices = mesh_vertices(obj)
        bb = bounds(world_vertices)
        dimensions = [hi - lo for lo, hi in bb]
        offset = [(bb[0][0] + bb[0][1]) / 2, (bb[1][0] + bb[1][1]) / 2, bb[2][0]]
        code = f'P{index:03d}'
        folder = folder_for(key, obj['role'])
        record = {'code': code, 'id': key, 'name_zh': obj.get('label_zh', key), 'role': obj['role'],
                  'category': obj['category'], 'candidate_stl': bool(obj.get('export_candidate')),
                  'folder': folder, 'blend_file': f'parts/{folder}/{code}_{key}.blend',
                  'dimensions_mm': dimensions, 'assembly_offset_mm': offset,
                  'source_world_matrix': [list(row) for row in obj.matrix_world],
                  'source_blend_sha256': source_hash,
                  'interface_status': obj.get('interface_status', 'PROVISIONAL'),
                  'material_suggestion': obj.get('material_suggestion', '')}
        records.append(record)
        expected[key] = {'world_vertices': world_vertices,
                         'normalized_vertices': [tuple(Vector(v) - Vector(offset)) for v in world_vertices],
                         'faces': [tuple(p.vertices) for p in obj.data.polygons], 'vertex_count': len(obj.data.vertices)}
        # Keep the evaluated source transform stable while switching scenes for output.
    for source_obj, record in zip(sources, records):
        obj, scene = normalized_part_file(source_obj, record, output)
        normalized[record['id']] = obj
        part_scenes.append(scene)
    print(f'MORI extracted {len(records)} part/coupon meshes', flush=True)
    mat = label_material()
    physical = [r for r in records if r['role'] == 'part']
    boards = [
        create_board('01_Custom_Parts', 'MORI / CUSTOM PARTS', [r for r in physical if r['category'] == 'PRINTABLE'], normalized, 5, (225, 245), mat),
        create_board('02_Hardware_References', 'MORI / HARDWARE REFERENCES', [r for r in physical if r['category'] != 'PRINTABLE'], normalized, 8, (145, 150), mat),
        create_board('03_Test_Coupons', 'MORI / TEST COUPONS', [r for r in records if r['role'] == 'coupon'], normalized, 2, (130, 125), mat),
    ]
    boards.append(create_assembly(records, normalized, source_scene))
    overview_readme = text_block('MORI_PARTS_README', 'MORI 零件拆解\n场景 01：25 个自制结构件；02：71 个外购或占位模型；03：4 个试打件；04：装配检查。\n零件排布只改位置，保留毫米尺寸。场景 01/02 与 04 的同一零件共享网格：编辑顶点会同步显示。\n原 MORI_assembly.blend 保留参数化来源与运动控制。\n独立 .blend 文件各包含一个零件，不与本总览自动同步。\n全部硬件接口状态仍为 PROTOTYPE / UNVALIDATED。\n')
    for scene in boards:
        set_scene(scene)
    bpy.data.libraries.write(str(output / 'MORI_parts.blend'), {*boards, overview_readme}, compress=True)
    manifest = {'schema': 'mori_independent_parts_v1', 'blender': bpy.app.version_string,
                'source_file': str(source), 'source_sha256': source_hash,
                'source_params_sha256': source_scene.get('params_sha256'),
                'units': 'mm', 'individual_files': len(records), 'physical_part_instances': len(physical),
                'coupon_count': len(records) - len(physical),
                'category_counts': dict(collections.Counter(r['category'] for r in physical)),
                'coordinate_rule': 'part local = assembly world - assembly_offset_mm; no rotation or rescaling',
                'parts': records}
    write_json(output / 'parts_manifest.json', manifest)
    make_index(output, manifest)
    results = validate_files(records, expected, output)
    master_result = validate_master(output, records, expected)
    assert sha256(source) == source_hash, 'Source assembly unexpectedly changed during splitting'
    report = {'status': 'PASS', 'checks': {
        'native_part_files_reopened': len(results), 'exact_one_mesh_per_part_file': 'PASS',
        'units_mm_and_identity_scale': 'PASS', 'vertex_order_and_polygon_winding_preserved': 'PASS',
        'normalized_position': 'PASS', 'dimensions_preserved': 'PASS',
        'reassembly_coordinates': 'PASS', 'source_file_unchanged': 'PASS'},
        'tolerance_mm': TOLERANCE_MM,
        'max_dimension_error_mm': max(r['max_dimension_error_mm'] for r in results),
        'max_reassembly_error_mm': max(r['max_reassembly_error_mm'] for r in results),
        'master': master_result, 'parts': results,
        'not_tested': ['Manufacturing suitability beyond existing source reports', 'Actual hardware fit or performance']}
    write_json(output / 'split_validation.json', report)
    if not args.no_render:
        render_dir = output / 'previews'
        render_dir.mkdir(exist_ok=True)
        for name, filename in [('01_Custom_Parts', 'custom_parts.png'), ('02_Hardware_References', 'hardware_references.png'), ('03_Test_Coupons', 'test_coupons.png')]:
            scene = bpy.data.scenes[name]
            set_scene(scene)
            scene.render.filepath = str(render_dir / filename)
            print('MORI rendering ' + name, flush=True)
            bpy.ops.render.render(write_still=True)
    set_scene(bpy.data.scenes['01_Custom_Parts'])
    configure_ui(bpy.context.scene)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'MORI_parts.blend'), compress=True)
    print('MORI PART SPLIT COMPLETE: ' + str(output), flush=True)


if __name__ == '__main__':
    main()
