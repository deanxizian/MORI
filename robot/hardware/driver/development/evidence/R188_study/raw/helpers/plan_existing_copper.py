"""Read-only proposals joining existing disconnected copper groups on one layer.

Use actual filled copper and plated anchors, rather than measuring only pad
centres. No new via, moved part, rule relaxation, or source save is performed.
Proposals still require native DRC, regression, transition and visual review.
"""
import argparse
import heapq
import json
import math
from pathlib import Path

import numpy as np
from shapely import contains_xy, intersects_xy, prepare
from shapely.prepared import prep

from copper_geometry import *


def groups(c, net):
    parents = {}
    regions = {}

    def root(x):
        parents.setdefault(x, x)
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x

    def join(a, b):
        parents[root(a)] = root(b)

    for layer in LAYERS:
        for i, region in enumerate(parts(c.copper.get((net, layer), GeometryCollection()))):
            key = (layer, i)
            regions[key] = region
            root(key)
            for a in c.anchors(net):
                land = c.shapes.get((uid(a), layer))
                if land is not None and land.intersects(region):
                    join(uid(a), key)
    result = defaultdict(lambda: {'pads': [], 'layers': defaultdict(list)})
    for p in c.pads:
        if p.GetNetname() == net:
            result[root(uid(p))]['pads'].append(c.pad_name(p))
    for key, region in regions.items():
        result[root(key)]['layers'][key[0]].append(region)
    return [{'pads': sorted(g['pads']), 'layers': {ly: unary_union(v) for ly, v in g['layers'].items()}}
            for g in result.values() if g['pads']]


def search(sa, sb, blocked, allowed, grid, margin, width, max_expanded):
    minx, miny, maxx, maxy = sa.union(sb).bounds
    x0 = max(.505 + width / 2, math.floor((minx - margin) / grid) * grid)
    y0 = max(.505 + width / 2, math.floor((miny - margin) / grid) * grid)
    xs = np.arange(x0, min(69.495 - width / 2, maxx + margin) + 1e-9, grid)
    ys = np.arange(y0, min(34.495 - width / 2, maxy + margin) + 1e-9, grid)
    xx, yy = np.meshgrid(xs, ys)
    prepare(blocked); prepare(allowed)
    free = ~intersects_xy(blocked, xx, yy) & contains_xy(allowed, xx, yy)
    # Start/end centres must be inside existing copper. The full-stroke free
    # mask already checks clearance, keepouts and reference coverage. Requiring
    # an additional half-width pad inset incorrectly erased legal 0.20-mm lands
    # and existing 0.20-mm traces when proposing a 0.20-mm route.
    starts = list(zip(*np.where(contains_xy(sa.buffer(-.001), xx, yy) & free)))
    goals = set(zip(*np.where(contains_xy(sb.buffer(-.001), xx, yy) & free)))
    if not starts or not goals:
        return {'status': 'NO_ENDPOINT_ACCESS', 'start_points': len(starts), 'end_points': len(goals)}
    obstacle_test, allowed_test = prep(blocked), prep(allowed)
    directions = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
    target = sb.bounds

    def point(n):
        return float(xs[n[1]]), float(ys[n[0]])

    def heuristic(n):
        x, y = point(n)
        return math.hypot(max(target[0] - x, x - target[2], 0), max(target[1] - y, y - target[3], 0))

    cost, parent, queue = {}, {}, []
    seq = 0
    for y, x in starts:
        key = int(y), int(x), 8
        cost[key] = 0.
        heapq.heappush(queue, (heuristic(key), seq, 0., key)); seq += 1
    found = None
    expanded = 0
    while queue and expanded < max_expanded:
        _, _, g, key = heapq.heappop(queue)
        if g != cost[key]:
            continue
        y, x, direction = key
        if (y, x) in goals:
            found = key
            break
        expanded += 1
        for nd, (dy, dx) in enumerate(directions):
            ny, nx = y + dy, x + dx
            if not (0 <= ny < len(ys) and 0 <= nx < len(xs) and free[ny, nx]):
                continue
            if direction != 8 and min((nd - direction) % 8, (direction - nd) % 8) > 2:
                continue
            nxt = ny, nx, nd
            ng = g + grid * (math.sqrt(2) if dx and dy else 1) + (.6 if direction != 8 and direction != nd else 0)
            if ng >= cost.get(nxt, math.inf):
                continue
            line = LineString([point(key), point(nxt)])
            if obstacle_test.intersects(line) or not allowed_test.covers(line):
                continue
            cost[nxt] = ng; parent[nxt] = key
            heapq.heappush(queue, (ng + heuristic(nxt), seq, ng, nxt)); seq += 1
    if found is None:
        return {'status': 'SEARCH_LIMIT' if queue else 'NO_PATH_IN_SEARCH', 'expanded': expanded}
    path = [found]
    while path[-1] in parent:
        path.append(parent[path[-1]])
    pts = [point(n) for n in reversed(path)]
    simplified = [pts[0]]
    for i in range(1, len(pts) - 1):
        u, v = np.subtract(pts[i], simplified[-1]), np.subtract(pts[i + 1], pts[i])
        if abs(u[0] * v[1] - u[1] * v[0]) > 1e-8:
            simplified.append(pts[i])
    simplified.append(pts[-1])
    return {'status': 'PROPOSAL', 'points_mm': [[round(x, 6), round(y, 6)] for x, y in simplified],
            'length_mm': sum(math.dist(a, b) for a, b in zip(simplified, simplified[1:])),
            'bends': len(simplified) - 2, 'expanded': expanded}


def plan(args):
    c = Copper(args.board)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    nets = sorted({p.GetNetname() for p in c.pads if p.GetNetname() and not p.GetNetname().startswith('unconnected-')})
    if args.net:
        nets = args.net
    rows = []
    print('Loading native copper shapes and filled polygons', flush=True)
    c.copper
    bodies = unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_')])
    print('Loaded copper and body projections', flush=True)
    for net in nets:
        gs = groups(c, net)
        if len(gs) < 2:
            continue
        print(json.dumps({'planning_net': net, 'groups': len(gs)}), flush=True)
        own_lands = {ly: unary_union([s for (id_, layer), s in c.shapes.items()
                     if layer == ly and isinstance(c.by_id[id_], pcb.PAD) and c.by_id[id_].GetNetname() == net])
                     for ly in args.layers}
        transfers = unary_union([Point(xy(v.GetPosition())).buffer(.655) for v in c.vias if v.GetNetname() == net])
        for layer in args.layers:
            # Restrict to existing-copper F/B/In3; never add In2 whitelist entries.
            obstacles = [s.buffer(.205 + args.width / 2) for (id_, ly), s in c.shapes.items()
                         if ly == layer and c.by_id[id_].GetNetname() != net]
            obstacles += [k['shape'].buffer(args.width / 2 + .005) for k in c.keepouts
                          if layer in k['layers'] and k['tracks']]
            # Conservative all-face body projection check, outside existing lands.
            if args.body_projections == 'all':
                obstacles.append(bodies.difference(own_lands[layer]).buffer(args.width / 2 + .005))
            blocked = unary_union(obstacles)
            allowed = unary_union([c.copper.get(('GND', REFERENCE[layer]), GeometryCollection()),
                                   own_lands[layer], transfers]).buffer(-args.width / 2 - .002)
            for i, a in enumerate(gs):
                for j, b in enumerate(gs[i + 1:], i + 1):
                    if layer not in a['layers'] or layer not in b['layers']:
                        continue
                    row = {'net': net, 'layer': layer, 'groups': [a['pads'], b['pads']], 'width_mm': args.width}
                    print(json.dumps({'search': net, 'layer': layer, 'group_indices': [i, j]}), flush=True)
                    row.update(search(a['layers'][layer], b['layers'][layer], blocked, allowed,
                                      args.grid, args.margin, args.width, args.max_expanded))
                    rows.append(row)
                    print(json.dumps({k: v for k, v in row.items() if k not in ['points_mm', 'groups']}), flush=True)
        (output / 'searches.json').write_text(json.dumps(rows, indent=2) + '\n')
    proposals = [r for r in rows if r['status'] == 'PROPOSAL']
    proposals.sort(key=lambda r: (r['bends'], r['length_mm']))
    for i, row in enumerate(proposals, 1):
        plan = {'revision': args.revision + str(i), 'board_sha256': c.sha,
                'scope': 'Independent fixed-placement trial; no new vias; native, electrical and visual checks required',
                'routes': [row], 'search': {'grid_mm': args.grid, 'margin_mm': args.margin,
                                          'body_projection_mode': args.body_projections}}
        (output / ('plan-' + str(i) + '.json')).write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps({'proposals': len(proposals), 'searches': len(rows)}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('board'); p.add_argument('output'); p.add_argument('revision')
    p.add_argument('--net', action='append'); p.add_argument('--width', type=float, default=.2)
    p.add_argument('--layers', nargs='+', choices=['F.Cu', 'B.Cu', 'In3.Cu'], default=['F.Cu', 'B.Cu', 'In3.Cu'])
    p.add_argument('--grid', type=float, default=.1); p.add_argument('--margin', type=float, default=4)
    p.add_argument('--max-expanded', type=int, default=100000)
    p.add_argument('--body-projections', choices=['all', 'native'], default='native',
                   help='native retains every native keepout; projection exceptions still need explicit review')
    plan(p.parse_args())
