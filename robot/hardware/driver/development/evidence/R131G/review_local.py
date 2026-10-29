"""R131G bounded placement measurements; never saves a board.

Usage: KiCad-Python review_local.py SOURCE.pcb CANDIDATE.pcb OUTPUT.json
Fab outlines are nominal CAD geometry, not measured assembled bodies.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from copper_geometry import Copper, Point, LineString, polyset, parts, uid, xy
from shapely.geometry import box
from shapely.ops import polygonize, unary_union
import pcbnew as pcb


def fab(c, f):
    layer = pcb.F_Fab if f.GetLayer() == pcb.F_Cu else pcb.B_Fab
    lines, rects = [], []
    for g in f.GraphicalItems():
        if not isinstance(g, pcb.PCB_SHAPE) or g.GetLayer() != layer:
            continue
        a, b = xy(g.GetStart()), xy(g.GetEnd())
        if g.GetShape() == pcb.SHAPE_T_SEGMENT:
            lines.append(LineString([a, b]))
        elif g.GetShape() == pcb.SHAPE_T_RECT:
            rects.append(box(min(a[0], b[0]), min(a[1], b[1]),
                             max(a[0], b[0]), max(a[1], b[1])))
        else:
            raise ValueError('Unexpected fabrication geometry: ' + f.GetReference())
    result = unary_union(rects + list(polygonize(unary_union(lines))))
    assert not result.is_empty, f.GetReference()
    return result


def measure(path):
    c = Copper(path)
    fp = {f.GetReference(): f for f in c.footprints}
    pads = {c.pad_name(p): p for p in c.pads}
    ilm = 'Net-(U1201-ILM)'
    sw = 'Net-(U901-SW)'
    bodies = {r: fab(c, fp[r]) for r in ('R1201', 'R1207', 'L901')}
    ilm_shape = unary_union([s for (id_, _), s in c.shapes.items()
                             if c.by_id[id_].GetNetname() == ilm])
    sw_shape = unary_union([s for (n, _), s in c.copper.items() if n == sw])
    ground_regions = [s for s in parts(c.copper['GND', 'B.Cu'])
                      if s.intersects(c.shapes[uid(pads['R1207.1']), 'B.Cu'])]
    gnd_surface = unary_union(ground_regions)
    surface_vias = [v for v in c.vias if v.GetNetname() == 'GND'
                    and gnd_surface.intersects(c.shapes[uid(v), 'B.Cu'])]
    distances = {}
    for a, b in [('R1207.2', 'U1201.9'), ('R1207.1', 'U1201.8')]:
        distances[a + ':' + b] = Point(xy(pads[a].GetPosition())).distance(
            Point(xy(pads[b].GetPosition())))
    poses = {}
    for r in ('R1201', 'R1207'):
        f = fp[r]
        court = polyset(f.GetCourtyard(f.GetLayer()))
        gaps = sorted((court.distance(polyset(other.GetCourtyard(other.GetLayer()))),
                       other.GetReference()) for other in c.footprints
                      if other.GetLayer() == f.GetLayer() and other != f
                      and not polyset(other.GetCourtyard(other.GetLayer())).is_empty)
        poses[r] = dict(position_mm=xy(f.GetPosition()), rotation_deg=f.GetOrientationDegrees(),
                        face=c.board.GetLayerName(f.GetLayer()), fab_bounds_mm=bodies[r].bounds,
                        L901_nominal_body_projection_overlap_mm2=bodies[r].intersection(bodies['L901']).area,
                        nearest_courtyards=[dict(reference=name, gap_mm=gap) for gap, name in gaps[:3]])
    pairs = c.connected_pairs('GND')
    return dict(board_sha256=c.sha, poses=poses, pad_center_distances_mm=distances,
                ILM_total_track_centerline_length_mm=sum(t.GetLength()/1e6 for t in c.segments if t.GetNetname() == ilm),
                ILM_copper_to_SW_projected_clearance_mm=ilm_shape.distance(sw_shape),
                ILM_copper_L901_nominal_body_projection_overlap_mm2=ilm_shape.intersection(bodies['L901']).area,
                R1207_ground_to_U1201_pin8_connected=tuple(sorted((uid(pads['R1207.1']), uid(pads['U1201.8'])))) in pairs,
                R1207_ground_same_B_surface_vias=[dict(uuid=uid(v), position_mm=xy(v.GetPosition())) for v in surface_vias],
                segment_count=len(c.segments), via_count=len(c.vias), footprint_count=len(c.footprints))


before, after = measure(sys.argv[1]), measure(sys.argv[2])
assert before['board_sha256'] == '42c17eaeb2588938e987a824ffdf5ba4770982bce8673eca89e7faefa16811df'
assert after['board_sha256'] == '6f9d92ebf5a36598421f064cf29523081d8004d28d2e60ef7a0c36ff8b9bd099'
assert before['R1207_ground_to_U1201_pin8_connected'] and after['R1207_ground_to_U1201_pin8_connected']
report = dict(source=before, candidate=after,
              limits='Nominal native CAD geometry and connectivity only. Distances are not magnetic, parasitic, thermal, EMC or assembly qualification. Plane connectivity does not establish a quiet Kelvin/star ground.')
Path(sys.argv[3]).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
