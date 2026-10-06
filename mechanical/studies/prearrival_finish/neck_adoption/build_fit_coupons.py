"""Independent PA12/6806 gauges derived from the current neck parameters.

No robot part, production geometry, hardware source or purchase is modified.
The journal set includes the current 29.9 mm trial journal explicitly.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT / 'mechanical/scripts'))
from common import *
from export import write_stl, read_stl, topology
from validate import Solid
from render import camera

OUT = HERE / 'fit_coupons'
OUT.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = ROOT / 'mori_v1_2.blend'
source_sha = sha(source)
q = P['neck_harness_capacity']
assert q['enabled'] and q['keeper_wall_correction']['approved']
# Current selected boundary dimensions, checked against the build source below.
cp = q['candidate_parameters']
print('CANDIDATE_PARAMETER_KEYS', list(cp), flush=True)
setup_scene()
material('frame', (.32, .45, .49))

def plate(name, size, note):
    o = box(name, (0, 0, size[2] / 2), size)
    boolean(o, box('gauge_origin', (-size[0] / 2, -size[1] / 2, size[2] / 2), (4, 4, size[2] + 2)))
    finish(o, 'PRINTABLE', name, 'frame', 'coupon', True, note=note)
    o['role'] = 'coupon'
    o['data_status'] = 'ASSUMED'
    o['material_selection'] = 'PA12; use the same vendor process and batch as the mating prints'
    o['robot_part'] = False
    return o

def build(bore_nominal, journal_nominal):
    bores = [round(bore_nominal + x, 3) for x in [-.2, 0, .2]]
    journals = [round(journal_nominal + x, 3) for x in [-.1, 0, .1, .2]]
    a = plate('C08_6806_housing', (162, 54, 9), '42 mm bearing outer race trial bores; radial fit only. Not an axial-retention or strength test.')
    for x, d in zip([-53, 0, 53], bores):
        boolean(a, cyl('bore', (x, 0, 4.5), d / 2, 11, n=192))
    b = plate('C09_6806_journal', (176, 42, 3), '30 mm bearing inner race trial journals. Current robot trial diameter is included. No final fit is selected by this file.')
    for x, d in zip([-66, -22, 22, 66], journals):
        union(b, cyl('journal', (x, 0, 6.995), d / 2, 8.01, n=192))
    rows = []
    for o, ds, xs, kind in [(a, bores, [-53, 0, 53], 'bore'), (b, journals, [-66, -22, 22, 66], 'journal')]:
        name = o.name.removeprefix(PREFIX)
        fn = OUT / (name + '.stl')
        write_stl(o, fn)
        v, f, n = read_stl(fn)
        topo = topology(v, f, n)
        solid = Solid(o).m
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=str(fn), global_scale=1., use_scene_unit=False, forward_axis='Y', up_axis='Z')
        imported = set(bpy.data.objects) - before
        assert len(imported) == 1
        imp = next(iter(imported))
        reloaded = Solid(imp).m
        difference = (solid - reloaded).volume() + (reloaded - solid).volume()
        count = len(reloaded.decompose())
        imported_bounds = bounds(imp)
        bpy.data.objects.remove(imp, do_unlink=True)
        tests = dict(topology=all(topo[k] == 0 for k in ['boundary_edges', 'nonmanifold_edges', 'inconsistent_edges', 'degenerate_triangles', 'inconsistent_stl_normals']),
                     connected=len(solid.decompose()) == count == 1,
                     import_volume_difference=difference < .001)
        rows.append(dict(id=name, file=str(fn.relative_to(PROJECT)), sha256=sha(fn),
                         kind=kind, diameters_mm=ds, x_centres_mm=xs, y_mm=0,
                         size_mm=[round(float(b - a), 5) for a, b in bounds(o)],
                         imported_bounds_mm=imported_bounds, topology=topo,
                         connected_components=count, imported_difference_mm3=difference,
                         checks=tests, status='PASS' if all(tests.values()) else 'FAIL',
                         qualification='Trial fits only; physical fit and PA12 strength NOT_TESTED'))
    b.location.y = 67
    return rows

# Read dimensions from the effective C5 construction rather than old 6804 fields.
outer_bore = float(cp['housing_bore_r_mm']) * 2
journal = float(cp['journal_outer_r_mm']) * 2
assert q['construction']['base_rings'][1][1] * 2 == outer_bore
assert q['construction']['yoke_rings'][0][0] * 2 == journal
assert abs(outer_bore - 42.1) < 1e-6 and abs(journal - 29.9) < 1e-6
rows = build(outer_bore, journal)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.light = 'STUDIO'
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
if scene.world is None:
    scene.world = bpy.data.worlds.new('PA12_Coupon_World')
scene.world.color = (.82, .85, .87)
scene.view_settings.view_transform = 'Standard'
scene.render.resolution_x = 1280
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
camera('FIT_6806', (160, -210, 270), (0, 34, 3), 215)
scene.render.filepath = str(OUT / 'overview.png')
bpy.ops.render.render(write_still=True)
blend = OUT / 'MORI_PA12_6806_fit_coupons.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
assert sha(source) == source_sha
report = dict(revision=P['revision'], status='PASS' if all(x['status'] == 'PASS' for x in rows) else 'FAIL',
              source_blend_sha256=source_sha, config_sha256=sha(PROJECT / 'config/geometry.json'),
              script_sha256=sha(Path(__file__)), units='mm', robot_parts_added=0,
              geometry_source='geometry.json effective C5 construction and journal radius',
              material='PA12, same vendor process and comparable orientation/batch as the affected robot parts',
              trial_dimensions=dict(housing_bore_mm=outer_bore, journal_diameter_mm=journal),
              physical_fit='NOT_TESTED', strength='NOT_TESTED', manufacturing_release=False,
              old_32_20_coupons='Historical C04/C05; do not use them to select the new 6806 fit',
              parts=rows, blend_sha256=sha(blend), overview_sha256=sha(OUT / 'overview.png'))
(OUT / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
with (OUT / 'measurements.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['coupon', 'position_left_to_right', 'nominal_mm', 'measured_X_mm', 'measured_Y_mm', 'bearing_batch', 'fit_result', 'PA12_process_batch', 'notes'])
    for row in rows:
        for i, d in enumerate(row['diameters_mm']):
            w.writerow([row['id'], i + 1, d, '', '', '', '', '', ''])
print('NEW_6806_COUPONS', report['status'], len(rows), flush=True)
assert report['status'] == 'PASS'
