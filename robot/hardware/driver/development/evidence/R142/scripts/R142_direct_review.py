"""Read-only direct-line comparisons for the two open routing-style items.

Planner obstacles and reference coverage are screening models, not native DRC
or proof that a different component-group layout cannot improve the routes.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from plan_layered_route import Planner
from shapely.geometry import LineString

base = Path('robot/.state/c3-completion/trials')
board = base/'R142/MORI_Interface_C3.kicad_pcb'
p = Planner(str(board), .1, ['B.Cu', 'In2.Cu'], .2)
assert p.c.sha == '2a7c04b8430875a0f8f9e4bdde4b789da6b8efb5f84ee991a360f1d5b6d006dd'
cases = []
for net, layer, points in [
    ('/01 {slash} Core/ACT_CURRENT_ADC', 'B.Cu', [(26.05, 11.75), (27.775, 13.475)]),
    ('/FAULT_N', 'In2.Cu', [(20.5, 27.65), (21.75, 26.4)]),
]:
    _, _, blocked, allowed = p.geometry(net)
    i = p.layers.index(layer)
    line = LineString(points)
    cases.append({
        'net': net, 'layer': layer, 'points_mm': points,
        'physical_screen_clear': not line.intersects(blocked[i]),
        'reference_screen_clear': allowed[i].covers(line),
        'centerline_outside_reference_corridor_mm': line.difference(allowed[i]).length,
        'centerline_inside_physical_obstacles_mm': line.intersection(blocked[i]).length,
    })
assert hashlib.sha256(board.read_bytes()).hexdigest() == p.c.sha
result = {'scope': __doc__, 'source_sha256': p.c.sha, 'cases': cases,
          'whole_board_style_optimization': 'NOT_TESTED'}
with (base/'R142-verification/direct-line-review.json').open('x') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(json.dumps(result))
