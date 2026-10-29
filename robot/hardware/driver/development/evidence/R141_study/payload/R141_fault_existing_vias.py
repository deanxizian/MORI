"""Compare no-new-via FAULT paths between two verified native via centres.

Bounded read-only proposals only. Retain native keepouts, physical spacing,
reference geometry, mounted-face Fab outlines and L701/L901 documented maximum
body projections. A proposal is not a DRC or physical qualification result.
"""
import ast
import json
import math
import sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner, mask, simplify

base = Path('robot/.state/c3-completion/trials')
revision = sys.argv[1]
out = base/(revision+'-fault-existing-vias')
out.mkdir(exist_ok=False)
node = next(x for x in ast.parse((base/'R138_joint_search.py').read_text()).body
            if isinstance(x, ast.FunctionDef) and x.name == 'fab')
exec(compile(ast.Module(body=[node], type_ignores=[]), 'fab_helper', 'exec'))
p = Planner(str(base/revision/'MORI_Interface_C3.kicad_pcb'), .05,
            ['B.Cu', 'In3.Cu', 'F.Cu', 'In2.Cu'], .2)
c = p.c
net = '/FAULT_N'
ends = [c.by_id[u] for u in ['265567ed-c1dc-4cde-b454-f55d12b8f735',
                            'f2307f60-c4ef-5ffa-9957-65a1a34d8f3a']]
assert all(isinstance(v, pcb.PCB_VIA) and v.GetNetname() == net for v in ends)
centres = [list(xy(v.GetPosition())) for v in ends]
free, vf, blocked, allowed = p.geometry(net)
body_bounds = {}
for i, layer in enumerate(p.layers):
    if layer not in ['F.Cu', 'B.Cu']:
        continue
    bodies = []
    for f in c.footprints:
        if c.board.GetLayerName(f.GetLayer()) != layer:
            continue
        body = fab(f)
        if f.GetReference() in ['L701', 'L901']:
            x, y = xy(f.GetPosition())
            body = translate(rotate(box(-4.6, -4.25, 4.6, 4.25),
                                    -f.GetOrientationDegrees(), origin=(0, 0)), xoff=x, yoff=y)
            body_bounds[f.GetReference()] = list(body.bounds)
        bodies.append(body)
    own_lands = unary_union([s for (u, ly), s in c.shapes.items()
                             if ly == layer and isinstance(c.by_id[u], pcb.PAD)
                             and c.by_id[u].GetNetname() == net])
    blocked[i] = unary_union([blocked[i], unary_union(bodies).buffer(.102).difference(own_lands.buffer(-.001))])
free = np.array([~mask(ob, p.xx, p.yy) & mask(al, p.xx, p.yy, True)
                 for ob, al in zip(blocked, allowed)])
rows = []
for i, layer in enumerate(p.layers):
    layer_free = np.zeros(free.shape, dtype=bool)
    layer_free[i] = free[i]
    a, b = [{'pads': [], 'layers': {layer: Point(pt).buffer(.038)}} for pt in centres]
    result = p.solve(a, b, (layer_free, np.zeros(vf.shape, dtype=bool), blocked, allowed), 800000)
    if result['status'] == 'PROPOSAL':
        assert not result['vias'] and len(result['routes']) == 1
        route = result['routes'][0]
        route['points_mm'][0], route['points_mm'][-1] = centres
        route['points_mm'] = simplify(route['points_mm'])
        line = LineString(route['points_mm'])
        if line.intersects(blocked[i]) or not allowed[i].covers(line):
            result['status'] = 'EXACT_CENTRE_SEGMENT_REJECTED'
        result['exact_centerline_length_mm'] = line.length
        route['net'] = net
    row = {'source_sha256': c.sha, 'layer': layer,
           'existing_vias': [{'uuid': uid(v), 'position_mm': xy(v.GetPosition())} for v in ends],
           'maximum_inductor_body_bounds_mm': body_bounds, 'result': result}
    rows.append(row)
    (out/'searches.json').write_text(json.dumps({'scope': __doc__, 'rows': rows}, indent=2)+'\n')
    print(json.dumps(row), flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == c.sha
