"""Independent guide revision: wider feed window with the same servo-clearing root."""
import numpy as np
import manifold3d as manifold
from sliding_cam_guide_geometry import rounded_rect, loft

def build():
    outer = rounded_rect([-32.35, -13.8], [-23.85, -8.2], .6)
    slab = manifold.CrossSection([outer]).extrude(2.4).translate([0, 0, 224.3])
    sections = [(z, rounded_rect([-30.85-e, -12.3-e], [-25.35+e, -9.7+e], .4+e))
                for z, e in [(224.2, .35), (224.55, 0.), (226.45, 0.), (226.8, .35)]]
    guide = slab - loft(sections)
    yz = [[-9.05, 225.4], [-6.4, 228.35], [-4.5, 228.35],
          [-4.5, 230.6], [-6.4, 230.6], [-9.05, 227.8]]
    root = manifold.CrossSection([yz]).extrude(2.55).transform(
        [[0, 0, 1, -31.75], [1, 0, 0, 0], [0, 1, 0, 0]])
    result = guide + root
    assert result.status() == manifold.Error.NoError and len(result.decompose()) == 1
    return result, dict(window_mm=[5.5, 2.6], guide_length_mm=2.4,
        outer_mm=[8.5, 5.6, 2.4], mouth_flare_mm=.25,
        minimum_nominal_side_wall_mm=1.25, root_x_mm=[-31.75, -29.2],
        root_yz_polygon_mm=yz, servo_top_mm=227.949996948,
        root_flat_underside_mm=228.35,
        role='Sliding guide only; broad rising root clears the unchanged servo',
        added_printed_parts=0, added_fasteners=0)
