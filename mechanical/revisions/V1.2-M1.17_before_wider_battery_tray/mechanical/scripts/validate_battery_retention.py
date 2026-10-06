"""Check closed material around the battery-tray side screws on actual solids.

This checks a local geometric support condition, not FDM strength or thread fit.
Standalone --before records the old defect without changing the assembly.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *


def inspect_retention(solids, Solid, iv):
    frame = solids['Load_Frame']
    settings = P['structure']['simple_modules']
    outer = settings['side_plate_abs_x_mm'] + settings['side_plate_thickness_mm'] / 2
    radius = P.get('battery_retention', {}).get('head_pocket_diameter_mm', 4.6) / 2
    minimum = P.get('battery_retention', {}).get('minimum_closed_ligament_mm', 2.0)
    # The wheels and shells are already removed for this service operation.
    removed = {'Body_Upper', 'Body_Lower', 'Wheel_Spacer_L_1', 'Wheel_Spacer_R_1'} | {
        n for n in solids if n.startswith(('Wheel_Hub_', 'Wheel_End_', 'Tire_', 'Shell_'))
    }
    rows = []
    for sign in [-1, 1]:
        name = 'Battery_Retainer_Screw_' + str(sign)
        screw = solids[name]
        insert = solids['Battery_Retainer_Insert_' + str(sign)]
        y, z = ((screw.lo + screw.hi) / 2)[1:]
        # A radial ray begins in the head recess, just beneath the outer face.
        # Its first two crossings must be recess wall then outside boundary.
        rays = []
        for angle in range(0, 360, 2):
            theta = math.radians(angle)
            origin = np.array([sign * (outer - .1), y, z])
            direction = np.array([0, math.cos(theta), math.sin(theta)])
            hits = frame.m.ray_cast(origin.tolist(), (origin + 120 * direction).tolist())
            distances = sorted(float(np.linalg.norm(np.array(h.position) - origin)) for h in hits)
            entry = distances[0] if distances else None
            ligament = distances[1] - distances[0] if len(distances) >= 2 and abs(entry - radius) < .025 else 0.0
            rays.append({'angle_deg': angle, 'entry_mm': entry, 'closed_material_mm': ligament})

        # A finite annular volume behind the screw head must be solid plastic.
        # It lies outside the clearance hole and inside the bearing face.
        xlo, xhi = 45.8, 48.4
        def cylinder(r):
            return manifold.Manifold.cylinder(xhi-xlo, r, r, 96, True).rotate([0, 90, 0]).translate([sign * (xlo+xhi)/2, y, z])
        bearing_band = cylinder(1.85) - cylinder(1.25)
        missing_backing = max(0.0, (bearing_band - frame.m).volume())
        insertion = []
        for distance in range(0, 26):
            moved = Solid(screw.o, screw, Matrix.Translation((sign * distance, 0, 0)))
            for n, other in solids.items():
                if n in removed or n == name:
                    continue
                overlap = iv(moved, other)
                if overlap > .01:
                    insertion.append({'distance_mm': distance, 'part': n, 'overlap_mm3': overlap})
        head_outer = max(abs(float(screw.lo[0])), abs(float(screw.hi[0])))
        tool_o = cyl('battery_service_tool', (sign * (head_outer + 15.1), y, z), 2.1, 30, 'X')
        tool = Solid(tool_o)
        tool_hits = []
        for n, other in solids.items():
            if n in removed or n == name:
                continue
            overlap = iv(tool, other)
            if overlap > .01:
                tool_hits.append({'part': n, 'overlap_mm3': overlap})
        bpy.data.objects.remove(tool_o, do_unlink=True)
        engagement = min(float(screw.hi[0]), float(insert.hi[0])) - max(float(screw.lo[0]), float(insert.lo[0]))
        rows.append({'side': sign, 'centre_yz_mm': [float(y), float(z)],
                     'minimum_closed_ligament_mm': min(a['closed_material_mm'] for a in rays),
                     'radial_rays': rays, 'missing_head_backing_mm3': missing_backing,
                     'head_recess_margin_mm': outer - head_outer,
                     'nominal_insert_engagement_mm': engagement,
                     'screw_insertion_failures': insertion, 'tool_failures': tool_hits})
    ok = all(r['minimum_closed_ligament_mm'] >= minimum-.01 and
             r['missing_head_backing_mm3'] < .001 and r['head_recess_margin_mm'] >= .2 and
             r['nominal_insert_engagement_mm'] >= 2.4 and
             not r['screw_insertion_failures'] and not r['tool_failures'] for r in rows)
    return {'revision': P['revision'], 'status': 'PASS' if ok else 'FAIL', 'mounts': rows,
            'minimum_required_ligament_mm': minimum,
            'method': 'Actual Manifold triangle solids: 180 radial rays per side at outer-face depth0.1mm; annular head-backing containment; full screw insertion every1mm over25mm; diameter4.2x30mm straight tool.',
            'removed_before_service': sorted(removed),
            'limits': 'Discrete geometric checks only. Global wall thickness, screw recess standard, insert knurl/thread/pullout, FDM creep and physical assembly NOT_TESTED.'}


def validate_battery_retention(solids, Solid, iv, check):
    result = inspect_retention(solids, Solid, iv)
    save_json(ROOT / 'reports/battery_retention_validation.json', result)
    check('battery_retention_closed_edges', result['status'],
          '电池托盘两侧固定孔的闭合孔边、螺钉支承面与装入路径',
          {'mounts': [{k:v for k,v in row.items() if k != 'radial_rays'} for row in result['mounts']],
           'details': 'battery_retention_validation.json'}, result['method'])


if __name__ == '__main__':
    from validate import Solid, intersect_volume
    bpy.context.window.scene = bpy.data.scenes['MORI_V1_Assembly']
    load_collections(); assembled()
    solids = {o.name.removeprefix(PREFIX): Solid(o) for o in parts() if o.get('group') != 'dock'}
    result = inspect_retention(solids, Solid, intersect_volume)
    path = ROOT / 'reports' / ('battery_retention_before.json' if '--before' in sys.argv else 'battery_retention_validation.json')
    save_json(path, result)
    print(json.dumps({**{k:v for k,v in result.items() if k != 'mounts'}, 'mounts':[{k:v for k,v in r.items() if k != 'radial_rays'} for r in result['mounts']]}, ensure_ascii=False))
