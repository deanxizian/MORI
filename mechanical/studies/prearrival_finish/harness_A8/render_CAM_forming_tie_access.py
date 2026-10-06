"""Show the original cutter approach on the current complete forming fixture."""
from pathlib import Path

TR_SCRIPT = Path(__file__).resolve()
TR_ROOT = TR_SCRIPT.parent
TR_HELPER = TR_ROOT / 'render_CAM_contact_refined_forming.py'
__file__ = str(TR_HELPER)
exec(compile(TR_HELPER.read_text().split('\nscene=bpy.context.scene;', 1)[0],
             str(TR_HELPER), 'exec'), globals())
__file__ = str(TR_SCRIPT)
TR_OUT = OR_OUT / 'root_tie_access'
tr_screen = json.loads((TR_OUT / 'screen.json').read_text())
assert tr_screen['status'] == 'PASS'
tr_case = next(row for row in tr_screen['trials'] if row['angle_about_tail_axis_deg'] == 0.)
assert tr_case['nominal_tool_sweep'] == 'PASS'
or_pose(0, 0.)


def tr_solid(filename):
    data = np.load(TR_OUT / filename)
    return manifold.Manifold(manifold.Mesh64(data['vertices_mm'], data['triangles']))


def tr_edges(label, solid, color, radius=.10):
    obj = or_mesh(label, solid, color)
    mesh = obj.data
    adjacent = {}
    for poly in mesh.polygons:
        for edge in poly.edge_keys:
            adjacent.setdefault(tuple(sorted(edge)), []).append(poly.normal.copy())
    curves = bpy.data.curves.new('A8_ROOT_TIE_'+label+'_edges', 'CURVE')
    curves.dimensions = '3D'
    curves.bevel_depth = radius
    curves.bevel_resolution = 2
    for edge, normals in adjacent.items():
        if len(normals) == 2 and normals[0].dot(normals[1]) > .99:
            continue
        spline = curves.splines.new('POLY')
        spline.points.add(1)
        for point, idx in zip(spline.points, edge):
            point.co = (*mesh.vertices[idx].co, 1.)
    shown = bpy.data.objects.new('A8_ROOT_TIE_'+label+'_edges', curves)
    bpy.context.scene.collection.objects.link(shown)
    curves.materials.append(material('A8_ROOT_TIE_MAT_'+label, color, roughness=.6))
    shown['study_owner'] = 'CAM_ROOT_TIE_ACCESS'
    shown['part_class'] = 'PLACEHOLDER'
    shown['data_status'] = 'ASSUMED'
    shown['scope'] = 'Presentation edges of full checked solid allocation; not detailed tool CAD'
    obj.hide_render = True
    obj.hide_viewport = True
    return shown


tool = tr_edges('cutter', tr_solid('tool_0.npz'), (.02, .57, .28), .17)
tail = tr_edges('tail_work', tr_solid('tail_corridor.npz'), (.86, .43, .06), .08)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = 1100
scene.render.resolution_y = 1050
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
tr_images = []
for label, eye, target, scale in [
        ('complete_tool', (110, 190, 395), (-5, 8, 301), 241),
        ('root_detail', (40, 115, 277), (-6, 0, 234), 69)]:
    camera('A8_ROOT_TIE_CAMERA', eye, target, scale)
    scene.render.filepath = str(TR_OUT / (label+'.png'))
    bpy.ops.render.render(write_still=True)
    tr_images.append(dict(file=label+'.png', sha256=sha(TR_OUT/(label+'.png')),
                          scope='Green edges: cutter; amber edges: free-tail work volume; four full straight wire tails and upstream wires retained',
                          tool_angle_deg=0., state='before first forming stage'))
assert all(geometry_record(o) == or_source[o.name] for o in parts() if o.name in or_source)
scene['independent_study'] = 'Current forming-stage root-tie cutter approach; not actual tie threading or complete harness installation'
scene.render.use_file_extension = True
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(TR_OUT / 'review.blend'))
(TR_OUT / 'render_manifest.json').write_text(json.dumps(dict(
    status='PASS', script_sha256=sha(TR_SCRIPT), helper_sha256=sha(TR_HELPER),
    source_main_sha256=source_hash, source_screen_sha256=sha(TR_OUT/'screen.json'),
    physical_source_objects_preserved=len(or_source), images=tr_images,
    review_sha256=sha(TR_OUT/'review.blend'), main_applied=False,
    presentation_only='Tool and tail shown as sharp edges; collision tests used entire solids',
    complete_harness='BLOCKED'), ensure_ascii=False, indent=2)+'\n')
assert sha(source) == source_hash
print('ROOT_TIE_ACCESS_RENDER_DONE', len(tr_images), flush=True)
