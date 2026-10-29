"""Read-only U303 placement/rotation comparison against connected regions.

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
out = base/'R143A-U303-placement.json'
assert not out.exists()
p = Planner(str(base/'R143A/MORI_Interface_C3.kicad_pcb'),
            .05, ['B.Cu', 'In3.Cu', 'F.Cu'], .2)
c = p.c
assert c.sha == 'e0959f02f77c4f28aa85e3e698f22a7de1f9d5187dd109619a9cb695069b6a29'
node = next(n for n in ast.parse((base/'R138_joint_search.py').read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'fab')
exec(compile(ast.Module(body=[node], type_ignores=[]), 'fab_helper', 'exec'))
bodies = {}
for ly in ['B.Cu', 'F.Cu']:
    ss = []
    for f in c.footprints:
        if c.board.GetLayerName(f.GetLayer()) != ly or f.GetReference() == 'U303':
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

net1 = '/CLR_N'
net2 = 'MOTION_3V3'
access = {net1: reachable(net1, 'J102.4'), net2: reachable(net2, 'U303.3'), 'GND': mask(c.copper[('GND','B.Cu')],p.xx,p.yy,True)}
f = next(f for f in c.footprints if f.GetReference() == 'U303')
origin, angle0 = xy(f.GetPosition()), f.GetOrientationDegrees()
pads = list(f.Pads())
mine = {uid(q) for q in pads}
court = polyset(f.GetCourtyard(pcb.B_CrtYd))
body = fab(f)
others = [polyset(q.GetCourtyard(pcb.B_CrtYd)) for q in c.footprints
          if q.GetLayer() == pcb.B_Cu and q.GetReference() != 'U303']
others = [g for g in others if not g.is_empty]
others += [s for (u, ly), s in c.shapes.items() if ly == 'B.Cu'
           and isinstance(c.by_id[u], pcb.PAD) and max(xy(c.by_id[u].GetDrillSize())) > 0]
others += [k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'B.Cu' in k['layers']]
via = prep(unary_union([s.buffer(.205) for (u, ly), s in c.shapes.items()
                       if ly == 'B.Cu' and isinstance(c.by_id[u], pcb.PCB_VIA)]))
obs = {q.GetNetname(): prep(unary_union([s.buffer(.205) for (u, ly), s in c.shapes.items()
                                       if ly == 'B.Cu' and u not in mine and isinstance(c.by_id[u], pcb.PAD)
                                       and c.by_id[u].GetNetname() != q.GetNetname()])) for q in pads}
tracks = [t for t in c.segments if t.GetLayer() == pcb.B_Cu]
shapes = [c.shapes[uid(t), 'B.Cu'] for t in tracks]
tree = STRtree(shapes)
source = Point(24.76,9.61)
target = c.copper[('MOTION_3V3','B.Cu')]
def access_count(g, net, center):
    a, b, d, e = g.bounds
    x0, x1 = max(0, int((a-.8)/p.grid)-1), min(p.xx.shape[1], int((d-.8)/p.grid)+2)
    y0, y1 = max(0, int((b-.8)/p.grid)-1), min(p.xx.shape[0], int((e-.8)/p.grid)+2)
    xx, yy = p.xx[y0:y1, x0:x1], p.yy[y0:y1, x0:x1]
    vx, vy = g.centroid.x-center[0], g.centroid.y-center[1]
    return int((contains_xy(g, xx, yy) & access[net][y0:y1, x0:x1]
                & ((xx-g.centroid.x)*vx+(yy-g.centroid.y)*vy >= 0)).sum())
xs, ys = np.arange(10, 29.001, .1), np.arange(6, 20.001, .1)
xx, yy = np.meshgrid(xs, ys)
rows = []
for angle in [0, 90, 180, 270]:
    r = rotate(court, -(angle-angle0), origin=origin)
    x0, y0, x1, y1 = r.bounds
    hx, hy = (x1-x0)/2+.015, (y1-y0)/2+.015
    obstacle = unary_union([box(a-hx, b-hy, d+hx, e+hy) for a, b, d, e in [g.bounds for g in others]])
    free = ~intersects_xy(obstacle, xx, yy)
    count = 0
    for yi, xi in zip(*np.where(free)):
        x, y = float(xs[xi]), float(ys[yi])
        def tr(g):
            return translate(rotate(g, -(angle-angle0), origin=origin), xoff=x-origin[0], yoff=y-origin[1])
        pp = [(q, tr(c.shapes[uid(q), 'B.Cu'])) for q in pads]
        if any(obs[q.GetNetname()].intersects(g) or via.intersects(g) for q, g in pp):
            continue
        counts = {q.GetNumber(): access_count(g, q.GetNetname(), (x, y)) for q, g in pp}
        if not all(counts.values()):
            continue
        bg = tr(body)
        hits = {int(j) for j in tree.query(bg) if shapes[j].intersects(bg)}
        for q, g in pp:
            grown = g.buffer(.205)
            hits.update(int(j) for j in tree.query(grown)
                        if tracks[j].GetNetname() != q.GetNetname() and shapes[j].intersects(grown))
        if len(hits) > 2 or any(tracks[j].GetWidth()/1e6 > .201 or tracks[j].GetNetname() in ['GND', 'MOTION_3V3'] for j in hits):
            continue
        pts = {q.GetNumber(): [round(g.centroid.x, 6), round(g.centroid.y, 6)] for q, g in pp}
        rows.append({'position_mm': [round(x, 4), round(y, 4)], 'angle_deg': angle,
                     'pads_mm': pts, 'optimistic_outward_access_cells': counts,
                     'tracks_needing_review': [{'uuid': uid(tracks[j]), 'net': tracks[j].GetNetname(),
                                               'start_mm': xy(tracks[j].GetStart()), 'end_mm': xy(tracks[j].GetEnd())} for j in sorted(hits)],
                     'score': 10*len(hits)+Point(pts['2']).distance(source)+2*Point(pts['3']).distance(target)})
        count += 1
    print(json.dumps({'angle': angle, 'passing_preliminary_positions': count}), flush=True)
rows.sort(key=lambda row: row['score'])
chosen = []
for row in rows:
    if all(math.dist(row['position_mm'], other['position_mm']) > .6 or row['angle_deg'] != other['angle_deg'] for other in chosen):
        chosen.append(row)
    if len(chosen) == 20:
        break
out.write_text(json.dumps({'scope': __doc__, 'source_sha256': c.sha, 'metrics': metrics,
                           'candidate_count': len(rows), 'chosen': chosen}, indent=2)+'\n')
print(json.dumps({'candidate_count': len(rows), 'chosen': chosen[:3]}, indent=2), flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == c.sha
