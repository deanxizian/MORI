"""Independent guide revision: raise its broad root above the unchanged servo."""
import numpy as np
import manifold3d as manifold
from sliding_cam_guide_geometry import rounded_rect, loft

def build():
    outer = rounded_rect([-31.75, -13.5], [-24.45, -8.5], .6)
    slab = manifold.CrossSection([outer]).extrude(2.4).translate([0, 0, 224.3])
    sections = [(z, rounded_rect([-30.25-e, -12.-e], [-25.95+e, -10.+e], .4+e))
                for z, e in [(224.2, .35), (224.55, 0.), (226.45, 0.), (226.8, .35)]]
    guide = slab - loft(sections)
    yz = [[-9.05, 225.4], [-6.4, 228.35], [-4.5, 228.35],
          [-4.5, 230.6], [-6.4, 230.6], [-9.05, 227.8]]
    root = manifold.CrossSection([yz]).extrude(2.85).transform(
        [[0, 0, 1, -31.75], [1, 0, 0, 0], [0, 1, 0, 0]])
    result = guide + root
    assert result.status() == manifold.Error.NoError and len(result.decompose()) == 1
    return result, dict(window_mm=[4.3, 2.0], guide_length_mm=2.4,
        outer_mm=[7.3, 5., 2.4], mouth_flare_mm=.25,
        minimum_nominal_side_wall_mm=1.25, root_x_mm=[-31.75, -28.9],
        root_yz_polygon_mm=yz, servo_top_mm=227.949996948,
        root_flat_underside_mm=228.35,
        role='Sliding guide only; broad rising root clears the unchanged servo',
        added_printed_parts=0, added_fasteners=0)
