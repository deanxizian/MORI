"""Read-only ADC connectivity survey of the newly accepted R142 layout.

Fixed-layout proposals are bounded, not routability/qualification proofs. Use
native rules, reference geometry, mounted-face nominal Fab bodies and recorded
maximum inductor bodies. Any proposal needs actual refill and full regression.
"""
import ast
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner, mask

base = Path('robot/.state/c3-completion/trials')
out = base/'R143B-joint-search'
out.mkdir(exist_ok=False)
p = Planner(str(base/'R143B/MORI_Interface_C3.kicad_pcb'),
            .05, ['B.Cu', 'In3.Cu', 'F.Cu', 'In2.Cu'], .2)
c = p.c
assert c.sha == '0c9bfba1e677680617042d1a1caeee6044e4cfb0a1ae86ec142a690a0b7fe96a'
node = next(x for x in ast.parse((base/'R138_joint_search.py').read_text()).body
            if isinstance(x, ast.FunctionDef) and x.name == 'fab')
exec(compile(ast.Module(body=[node], type_ignores=[]), 'fab_helper', 'exec'))
bodies = {}
for ly in ['F.Cu', 'B.Cu']:
    shapes = []
    for f in c.footprints:
        if c.board.GetLayerName(f.GetLayer()) != ly:
            continue
        body = fab(f)
        if f.GetReference() in ['L701', 'L901']:
            x, y = xy(f.GetPosition())
            body = translate(rotate(box(-4.6, -4.25, 4.6, 4.25),
                                    -f.GetOrientationDegrees(), origin=(0, 0)), xoff=x, yoff=y)
        shapes.append(body)
    bodies[ly] = unary_union(shapes)
rows = []
for net in ['/CLR_N', 'Net-(U1001-D2_{slash}_WHEEL_ADC)', '/01 {slash} Core/WHEEL_ADC']:
    gs = p.routing_groups(net)
    _, vf, blocked, allowed = p.geometry(net)
    for i, ly in enumerate(p.layers):
        if ly in bodies:
            lands = unary_union([s for (u, l), s in c.shapes.items()
                                 if l == ly and isinstance(c.by_id[u], pcb.PAD)
                                 and c.by_id[u].GetNetname() == net])
            blocked[i] = unary_union([blocked[i], bodies[ly].buffer(.102).difference(lands.buffer(-.001))])
    free = np.array([~mask(ob, p.xx, p.yy) & mask(al, p.xx, p.yy, True)
                     for ob, al in zip(blocked, allowed)])
    print(json.dumps({'net': net, 'phase': 'solve', 'groups': [g['pads'] for g in gs]}), flush=True)
    assert len(gs) == 2
    result = p.solve(gs[0], gs[1], (free, vf, blocked, allowed), 800000)
    row = {'net': net, 'source_sha256': c.sha, 'groups': [g['pads'] for g in gs], 'result': result}
    rows.append(row)
    (out/'searches.json').write_text(json.dumps({'scope': __doc__, 'rows': rows}, indent=2)+'\n')
    print(json.dumps({'net': net, **{k: v for k, v in result.items() if k not in ['routes', 'activate_pth_layers']}}), flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == c.sha
