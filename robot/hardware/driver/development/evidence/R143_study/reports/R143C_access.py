"""Read-only R1022 placement/rotation comparison against connected regions.

Native courtyards, pad/via spacing, mounted-face bodies, existing ground and
reference rules are retained. Region connectivity is an optimistic finite grid;
the new body and actual refill must be checked on any built candidate.
V2 seeds all copper of the already connected electrical group, rather than only
one pad: a new branch may attach anywhere on that existing group. This fixes
a conservative reachability omission; no physical/reference rule is relaxed.
"""
import ast
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely import contains_xy, intersects_xy
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
from shapely.strtree import STRtree
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner, mask

base = Path('robot/.state/c3-completion/trials')
out = base/'R143C-access-regions.json'
assert not out.exists()
p = Planner(str(base/'R143C/MORI_Interface_C3.kicad_pcb'),
            .05, ['B.Cu', 'In3.Cu', 'F.Cu'], .2)
c = p.c
assert c.sha == 'bdc62f0f151cc1755157e20c8b9d8762fccbced28638c81d5376e2817653362e'
node = next(n for n in ast.parse((base/'R138_joint_search.py').read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'fab')
exec(compile(ast.Module(body=[node], type_ignores=[]), 'fab_helper', 'exec'))
bodies = {}
for ly in ['B.Cu', 'F.Cu']:
    ss = []
    for f in c.footprints:
        if c.board.GetLayerName(f.GetLayer()) != ly:
            continue
        body = fab(f)
        if f.GetReference() in ['L701', 'L901']:
            x, y = xy(f.GetPosition())
            body = translate(rotate(box(-4.6, -4.25, 4.6, 4.25),
                                    -f.GetOrientationDegrees(), origin=(0, 0)), xoff=x, yoff=y)
        ss.append(body)
    bodies[ly] = unary_union(ss)
metrics = []
def reachable(net, seed):
    _, vf, blocked, allowed = p.geometry(net)
    for i, ly in enumerate(p.layers):
        if ly in bodies:
            lands = unary_union([s for (u, l), s in c.shapes.items()
                                 if l == ly and isinstance(c.by_id[u], pcb.PAD)
                                 and c.by_id[u].GetNetname() == net])
            blocked[i] = unary_union([blocked[i], bodies[ly].buffer(.102).difference(lands.buffer(-.001))])
    free = np.array([~mask(ob, p.xx, p.yy) & mask(al, p.xx, p.yy, True)
                     for ob, al in zip(blocked, allowed)])
    labs, n = [], 0
    for f in free:
        lab, count = ndimage.label(f, np.ones((3, 3)))
        lab[lab > 0] += n
        labs.append(lab)
        n += count
    parents = list(range(n+1))
    def root(k):
        while parents[k] != k:
            parents[k] = parents[parents[k]]
            k = parents[k]
        return k
    for i in range(len(p.layers)):
        for j in range(i+1, len(p.layers)):
            vm = vf & free[i] & free[j]
            if REFERENCE[p.layers[i]] != REFERENCE[p.layers[j]]:
                vm &= p.ground_near
            for a, b in np.unique(np.column_stack((labs[i][vm], labs[j][vm])), axis=0):
                parents[root(int(a))] = root(int(b))
    rootmap = np.array([root(k) for k in range(n+1)])
    group = next(g for g in p.routing_groups(net) if seed in g['pads'])
    sr = set()
    for i, ly in enumerate(p.layers):
        g = group['layers'].get(ly)
        if g is not None:
            m = mask(g, p.xx, p.yy) & free[i]
            sr.update(int(z) for z in np.unique(rootmap[labs[i][m]]) if z)
    m = np.isin(rootmap[labs[0]], list(sr)) & free[0]
    ys, xs = np.where(m)
    metrics.append({'net': net, 'seed': seed, 'back_cell_count': int(m.sum()),
                    'bounds_mm': [float(p.xs[xs.min()]), float(p.ys[ys.min()]),
                                  float(p.xs[xs.max()]), float(p.ys[ys.max()])] if len(xs) else None})
    print(json.dumps(metrics[-1]), flush=True)
    return m

net1 = 'Net-(U1001-D2_{slash}_WHEEL_ADC)'
net2 = '/01 {slash} Core/WHEEL_ADC'
access = {net1: reachable(net1, 'U1001.6'), net2: reachable(net2, 'R1032.2')}
reachable(net1,'R1022.1')
reachable(net2,'R1022.2')
out.write_text(json.dumps({'source_sha256':c.sha,'metrics':metrics},indent=2)+'\n')
