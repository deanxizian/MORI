"""Read-only fit screening against the released assembly; not a battery selection.

Run with Blender and the current mechanical/mori_v1_2.blend loaded.
No source configuration, main .blend or manufacturing output is written.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from common import *
from validate import Solid, intersect_volume
import hashlib
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
source = Path(bpy.data.filepath)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
sc = bpy.data.scenes['MORI_V1_Assembly']
bpy.context.window.scene = sc
load_collections()
assembled()

# Vendor maximums for ONE example cell; not a newly selected six-cell product.
dia, length = 18.6, 65.2
radius = dia / 2
base_z = bounds(bpy.data.objects[PREFIX + 'Battery'])[2][0]
obstacles = {}
for obj in parts():
    name = obj.name.removeprefix(PREFIX)
    if name == 'Battery' or name.startswith(('Parking_', 'Dock_')):
        continue
    bb = bounds(obj)
    if bb[2][0] < 150 and bb[2][1] > 65:
        obstacles[name] = Solid(obj)
routes = [Solid(o) for o in sc.objects if o.type == 'MESH' and o.get('role') == 'routing'
          and bounds(o)[2][0] < 150 and bounds(o)[2][1] > 65]

def centers(kind, axis):
    if kind == 'rect_3x2':
        cross = [(c * dia, radius + row * dia) for row in range(2) for c in [-1, 0, 1]]
    elif kind == 'stagger_3plus3':
        cross = [(c * dia + (row - .5) * radius,
                  radius + row * math.sqrt(3) * radius) for row in range(2) for c in [-1, 0, 1]]
    elif kind == 'stagger_4plus2':
        cross = [(c * dia, radius) for c in [-1.5, -.5, .5, 1.5]]
        cross += [(c * dia, radius + math.sqrt(3) * radius) for c in [-1, 0]]
    elif kind == 'single_6':
        cross = [(c * dia, radius) for c in [-2.5, -1.5, -.5, .5, 1.5, 2.5]]
    else:
        return [(x * dia, y * dia, base_z + length / 2) for x in [-1, 0, 1] for y in [-.5, .5]]
    return [(0, c, base_z + z) if axis == 'X' else (c, 0, base_z + z) for c, z in cross]

configs = [(k, ax) for k in ['rect_3x2', 'stagger_3plus3', 'stagger_4plus2', 'single_6'] for ax in ['X', 'Y']]
configs.append(('upright_3x2', 'Z'))
results = []
for kind, axis in configs:
    name = kind + '_' + axis
    objs = [cyl('STUDY_' + name + '_' + str(i), pos, radius, length, axis, n=192)
            for i, pos in enumerate(centers(kind, axis))]
    bpy.context.view_layer.update()
    cells = [Solid(o) for o in objs]
    lo = np.min([s.lo for s in cells], axis=0)
    hi = np.max([s.hi for s in cells], axis=0)
    samples = []
    for shift_y in [-4, 0, 4]:
        shifted = [Solid(o, s, Matrix.Translation((0, shift_y, 0))) for o, s in zip(objs, cells)]
        hits = []
        for n, target in obstacles.items():
            v = sum(intersect_volume(c, target) for c in shifted)
            if v > .001:
                hits.append({'part': n, 'overlap_volume_mm3': round(v, 3)})
        wire_hits = []
        for target in routes:
            v = sum(intersect_volume(c, target) for c in shifted)
            if v > .001:
                wire_hits.append({'route': target.name, 'overlap_volume_mm3': round(v, 3)})
        gap = min(c.m.min_gap(obstacles['Load_Frame'].m, 10) for c in shifted)
        samples.append({'shift_y_mm': shift_y, 'solid_intersections': hits,
                        'routing_intersections': wire_hits,
                        'load_frame_minimum_gap_mm': round(gap, 4),
                        'status_bare_cells_only': 'FAIL' if hits or wire_hits else 'PASS'})
    row = {'id': name, 'cell_axis': axis, 'bounds_xyz_mm': [lo.tolist(), hi.tolist()],
           'size_xyz_mm': [round(float(v), 3) for v in hi - lo], 'placements': samples}
    results.append(row)
    print(name, row['size_xyz_mm'], [(s['shift_y_mm'], s['status_bare_cells_only'],
          [h['part'] for h in s['solid_intersections']], s['load_frame_minimum_gap_mm']) for s in samples], flush=True)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)

frame = obstacles['Load_Frame']
ray_hits = frame.m.ray_cast([0, 0, base_z + .01], [0, 0, base_z + 80])
ceiling_z = min(h.position[2] for h in ray_hits if h.position[2] > base_z + .01)
report = {
    'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'source_blend': str(source),
    'source_sha256': source_hash, 'revision': P['revision'], 'blender': bpy.app.version_string,
    'cell_reference': {'manufacturer': 'Molicel', 'model': 'INR18650P28A', 'revision': '1.3',
        'url': 'https://www.molicel.com/wp-content/uploads/INR18650P28A_1.3_Product-Data-Sheet-of-INR-18650-P28A-80093.pdf',
        'maximum_diameter_mm': dia, 'maximum_length_mm': length,
        'purpose': 'Example dimensional screening only; no procurement or electrical qualification'},
    'bay': {'current_pack_xyz_mm': [b-a for a,b in bounds(bpy.data.objects[PREFIX+'Battery'])],
        'tray_outer_width_mm': 2*max(abs(v) for v in bounds(bpy.data.objects[PREFIX+'Battery_Tray'])[0]),
        'tray_rail_inner_width_mm': 2*P['battery_tray']['rail_inner_half_width_mm'],
        'uncompressed_side_pad_clearance_mm': obstacles['Battery_Pad_38.0'].lo[0] - obstacles['Battery_Pad_-38.0'].hi[0],
        'tray_depth_mm': P['battery_tray']['depth_mm'], 'pack_bottom_z_mm': base_z,
        'central_ceiling_z_mm': ceiling_z, 'central_height_mm': ceiling_z - base_z},
    'method': '192-sided cylinder solids in the current assembled .blend; AABB broadphase then Manifold solid intersection, including containment. 9 arrangements x 3 fixed Y translations (-4,0,+4mm). No change to tray/pads/frame/PCB. Load-frame distance from triangle solids; centre ceiling measured by actual solid ray.',
    'obstacles_checked': list(obstacles),
    'proxy_obstacles': [n for n,s in obstacles.items() if s.o.get('validation_proxy')],
    'routing_checked': [s.name for s in routes],
    'candidates': results,
    'complete_pack_fit': 'BLOCKED',
    'limitations': ['Zero cell spacing; no pack insulation, holders, nickel tabs, BMS, NTC, harness, plugs or installation allowance.',
        'Cylinder polygons approximate ideal cell outline; 192 sides have less than 0.002mm radial sag. Vendor tolerances already covered only by this example cell maximums.',
        'Nominal static fit only; no continuous placement search, assembly/removal sweep, mechanical retention, thermal or balance qualification.',
        'A bare-cell PASS is not a finished-pack fit approval. Current purchased/PCB placeholder limitations remain.'],
    'main_blend_unchanged': hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
}
save_json(OUT/'fit_report.json', report)
