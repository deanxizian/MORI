"""Show the independent empty-housing approach with all four wires retained."""
from pathlib import Path

HV_SCRIPT = Path(__file__).resolve()
HV_ROOT = HV_SCRIPT.parent
HV_HELPER = HV_ROOT / 'render_CAM_contact_refined_forming.py'
__file__ = str(HV_HELPER)
exec(compile(HV_HELPER.read_text().split('\nscene=bpy.context.scene;', 1)[0],
             str(HV_HELPER), 'exec'), globals())
__file__ = str(HV_SCRIPT)
HV_OUT = OR_OUT / 'housing_approach'
hv_report = json.loads((HV_OUT / 'screen.json').read_text())
assert hv_report['status'] == 'PASS' and hv_report['source_main_sha256'] == source_hash
or_pose(3, 1.)
# The rear cradle wall occludes the connector from this inspection angle.
# Ghost only the generated study copy; the complete solid remains in the
# external approach calculation and original scene objects are untouched.
ghost = bpy.data.objects.get('A8_ORDER_Pitch_Cradle')
assert ghost is not None
for slot in ghost.material_slots:
    mat = slot.material.copy()
    mat.name = 'A8_HOUSING_CRADLE_GHOST'
    slot.material = mat
    if mat.use_nodes:
        node = next(node for node in mat.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
        node.inputs['Alpha'].default_value = .12
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = 1050
scene.render.resolution_y = 950
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
hv_images = []
housing_object = None
for label in ['initial', 'final']:
    if housing_object is not None:
        bpy.data.objects.remove(housing_object, do_unlink=True)
    housing_object = or_mesh('empty_housing', pw_readsolid(HV_OUT / (label + '.npz')), (.93, .55, .15))
    camera('A8_HOUSING_APPROACH_CAMERA', (-55, -65, 315), (-10.1, -20.8, 218), 48)
    scene.render.filepath = str(HV_OUT / (label + '.png'))
    bpy.ops.render.render(write_still=True)
    hv_images.append(dict(file=label + '.png', sha256=sha(HV_OUT / (label + '.png')),
                          housing_position=label, all_four_wires_and_contacts_present=True,
                          shown_structure_subset=sorted(show),
                          transparent_for_inspection_only=['Pitch_Cradle']))
assert all(geometry_record(obj) == or_source[obj.name] for obj in parts() if obj.name in or_source)
scene['independent_study'] = 'Empty housing external approach only; contact insertion/locking and handling remain unqualified.'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(HV_OUT / 'review.blend'))
(HV_OUT / 'render_manifest.json').write_text(json.dumps(dict(
    status='PASS', script_sha256=sha(HV_SCRIPT), helper_sha256=sha(HV_HELPER),
    source_main_sha256=source_hash, source_screen_sha256=sha(HV_OUT / 'screen.json'),
    images=hv_images, physical_source_objects_preserved=len(or_source),
    review_sha256=sha(HV_OUT / 'review.blend'), main_applied=False,
    whole_harness='BLOCKED', manufacturing_release=False), ensure_ascii=False, indent=2) + '\n')
assert sha(source) == source_hash
print('HOUSING_APPROACH_RENDER_DONE', len(hv_images), flush=True)
