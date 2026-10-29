"""Read-only native-copper routing proposals with explicitly screened vias.

No PCB is saved. Raster search is bounded, not a routability proof. Each proposal
still needs native refill/DRC, power and reference regression, and layout review.
Uses scipy 1.13.1, numpy 2.0.2 and shapely 2.0.7 in the isolated KiCad venv.
"""
import argparse
import heapq
import json
import math
from pathlib import Path

import numpy as np
from scipy import ndimage
from shapely import contains_xy, intersects_xy, prepare
from shapely.prepared import prep

from copper_geometry import *
from plan_existing_copper import groups


def mask(geometry, xx, yy, within=False):
    prepare(geometry)
    return (contains_xy if within else intersects_xy)(geometry, xx, yy)


def simplify(points):
    result = [points[0]]
    for i in range(1, len(points) - 1):
        a, b, c = result[-1], points[i], points[i + 1]
        if abs((b[0]-a[0])*(c[1]-b[1]) - (b[1]-a[1])*(c[0]-b[0])) > 1e-8:
            result.append(b)
    if points[-1] != result[-1]:
        result.append(points[-1])
    return result


class Planner:
    def __init__(self, board, grid, layers, width):
        self.c = Copper(board)
        self.internal_clearance = inner_zone_clearance(board)
        self.in2_nets = in2_routing_nets(board) if 'In2.Cu' in layers else frozenset()
        self.grid, self.layers, self.width = grid, layers, width
        self.xs = np.arange(.5 + width/2 + .005, 69.5 - width/2 - .004, grid)
        self.ys = np.arange(.5 + width/2 + .005, 34.5 - width/2 - .004, grid)
        self.xx, self.yy = np.meshgrid(self.xs, self.ys)
        c = self.c
        c.copper
        self.ground = {ref: c.copper.get(('GND', ref), GeometryCollection())
                       for ref in ['In1.Cu', 'In4.Cu']}
        # New signal-via anti-pads must not remove any presently available
        # reference copper beneath retained signal/power tracks.
        referenced = []
        for t in c.segments:
            layer = c.board.GetLayerName(t.GetLayer())
            if t.GetNetname() != 'GND' and layer in REFERENCE:
                referenced.append(c.shapes[(uid(t), layer)].intersection(self.ground[REFERENCE[layer]]))
        self.reference_guard = unary_union(referenced).buffer(.657)
        ground_anchors = [a for a in c.anchors('GND') if all(
            (uid(a), ref) in c.shapes and c.shapes[(uid(a), ref)].intersects(self.ground[ref])
            for ref in self.ground)]
        self.ground_near = mask(unary_union([Point(xy(a.GetPosition())).buffer(1.98)
                                             for a in ground_anchors]), self.xx, self.yy, True)
        self.via_common = [self.reference_guard]
        # R01 applies even to same-net pads. Native via guards retain their
        # original layer applicability; a through via intersects all six layers.
        self.via_common.extend(s.buffer(.457) for (id_, _), s in c.shapes.items()
                               if isinstance(c.by_id[id_], pcb.PAD))
        self.via_common.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
        self.via_common.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6 + .307)
                               for v in c.vias)
        for p in c.pads:
            drill = xy(p.GetDrillSize())
            if max(drill) > 0:
                # Circumscribed radius is conservative for slots.
                self.via_common.append(Point(xy(p.GetPosition())).buffer(max(drill)/2 + .557))
        self.via_common = unary_union(self.via_common)
        # Unflashed internal annuli still have drilled/plated barrels. They
        # cannot disappear from routing obstacles merely because FlashLayer is
        # false. Slot bounds use a conservative circumscribed circle.
        self.holes = [(Point(xy(p.GetPosition())), max(xy(p.GetDrillSize()))/2)
                      for p in c.pads if max(xy(p.GetDrillSize())) > 0]
        self.holes += [(Point(xy(v.GetPosition())), v.GetDrillValue()/2e6)
                       for v in c.vias]

    def routing_groups(self, net):
        """Expose an unused circular PTH layer as a *prospective* terminal.

        Native KiCad restores that layer's existing pad land when a track is
        attached. Do not add imaginary copper to Copper.shapes/connectivity;
        require an exact centre endpoint and declare the resulting activation
        for native refill and the separate planned-delta review.
        """
        c = self.c
        gs = groups(c, net)
        for p in c.pads:
            dx, dy = xy(p.GetDrillSize())
            if (p.GetNetname() != net or p.GetAttribute() != pcb.PAD_ATTRIB_PTH
                    or p.GetDrillShape() != pcb.PAD_DRILL_SHAPE_CIRCLE
                    or dx <= 0 or abs(dx-dy) > 1e-8):
                continue
            g = next(row for row in gs if c.pad_name(p) in row['pads'])
            for layer in self.layers:
                lid = c.ids[layer]
                if (not p.IsOnLayer(lid) or p.FlashLayer(lid)
                        or (layer == 'In2.Cu' and net not in self.in2_nets)):
                    continue
                land = shape(p, lid)
                if land.is_empty:
                    continue
                foreign = unary_union([s for (id_, ly), s in c.shapes.items()
                                       if ly == layer and c.by_id[id_].GetNetname() != net])
                if land.buffer(.205).intersects(foreign):
                    continue
                terminal = {'pad_uuid': uid(p), 'pad': c.pad_name(p), 'layer': layer,
                            'position_mm': list(xy(p.GetPosition())), 'source_flashed': False}
                g.setdefault('prospective_pth_terminals', []).append(terminal)
                # A small search target is snapped to the exact centre below.
                target = Point(terminal['position_mm']).buffer(self.grid*.8)
                g['layers'][layer] = g['layers'].get(layer, GeometryCollection()).union(target)
        return gs

    def geometry(self, net):
        c, w = self.c, self.width
        via_block = unary_union([self.via_common] + [s.buffer(.457)
            for (id_, _), s in c.shapes.items()
            if c.by_id[id_].GetNetname() != net and not isinstance(c.by_id[id_], pcb.PAD)])
        via_free = ~mask(via_block, self.xx, self.yy)
        free, blocked, allowed = [], [], []
        for layer in self.layers:
            if layer == 'In2.Cu' and net not in self.in2_nets:
                free.append(np.zeros(self.xx.shape, dtype=bool))
                blocked.append(Polygon([(-1,-1),(71,-1),(71,36),(-1,36)]))
                allowed.append(GeometryCollection())
                continue
            ref = REFERENCE[layer]
            clearance = max([self.internal_clearance] + [z.GetLocalClearance()/1e6 for z in c.zones
                            if not z.GetIsRuleArea() and z.GetNetname() == 'GND' and z.IsOnLayer(c.ids[ref])])
            transfer_shapes = [reference_transfer_shape(c,o,ref) for o in c.anchors(net)]
            transfers = unary_union([s.buffer(clearance+.005) for s in transfer_shapes if s is not None])
            own_lands = unary_union([s for (id_, ly), s in c.shapes.items() if ly == layer
                and isinstance(c.by_id[id_], pcb.PAD) and c.by_id[id_].GetNetname() == net])
            obstacles = [s.buffer(.205 + w/2) for (id_, ly), s in c.shapes.items()
                         if ly == layer and c.by_id[id_].GetNetname() != net]
            obstacles += [k['shape'].buffer(w/2 + .005) for k in c.keepouts
                          if layer in k['layers'] and k['tracks']]
            obstacles += [point.buffer(radius + .305 + w/2) for point, radius in self.holes
                          if not any(point.distance(Point(xy(a.GetPosition()))) < 1e-7
                                     for a in c.anchors(net))]
            ob = unary_union(obstacles)
            al = unary_union([self.ground[REFERENCE[layer]], own_lands, transfers]).buffer(-w/2-.002)
            blocked.append(ob); allowed.append(al)
            free.append(~mask(ob, self.xx, self.yy) & mask(al, self.xx, self.yy, True))
        return np.asarray(free), via_free, blocked, allowed

    def point(self, key):
        return float(self.xs[key[2]]), float(self.ys[key[1]])

    def solve(self, a, b, geometry, limit):
        free, via_free, blocked, allowed = geometry
        starts, targets = [], np.zeros(free.shape, dtype=bool)
        for l, layer in enumerate(self.layers):
            if layer in a['layers']:
                sm = mask(a['layers'][layer].buffer(-.001), self.xx, self.yy, True) & free[l]
                starts.extend((l, int(y), int(x)) for y, x in zip(*np.where(sm)))
            if layer in b['layers']:
                targets[l] = mask(b['layers'][layer].buffer(-.001), self.xx, self.yy, True) & free[l]
        if not starts or not targets.any():
            return {'status': 'NO_ENDPOINT_ACCESS', 'starts': len(starts), 'targets': int(targets.sum())}
        # Quickly reject disconnected raster regions before expensive search.
        labels, count = [], 0
        for f in free:
            lab, n = ndimage.label(f, np.ones((3, 3)))
            lab[lab > 0] += count
            labels.append(lab); count += n
        parent = list(range(count + 1))
        def root(k):
            while parent[k] != k:
                parent[k] = parent[parent[k]]; k = parent[k]
            return k
        def join(a_, b_):
            parent[root(int(a_))] = root(int(b_))
        via_masks = {}
        for i in range(len(self.layers)):
            for j in range(i + 1, len(self.layers)):
                vm = via_free & free[i] & free[j]
                if REFERENCE[self.layers[i]] != REFERENCE[self.layers[j]]:
                    vm = vm & self.ground_near
                via_masks[i, j] = vm; via_masks[j, i] = vm
                pairs = np.unique(np.column_stack((labels[i][vm], labels[j][vm])), axis=0)
                for u, v in pairs:
                    join(u, v)
        target_regions = {root(int(labels[l][y, x])) for l, y, x in zip(*np.where(targets))}
        starts = [key for key in starts if root(int(labels[key[0]][key[1:]])) in target_regions]
        if not starts:
            return {'status': 'NO_RASTER_CONNECTION', 'via_sites': int(via_free.sum()), 'regions': count}
        # Distance is a lower bound; direction-dependent bend costs are only a
        # routing preference. One state per cell bounds memory, not optimality.
        hd = ndimage.distance_transform_edt(~targets.any(axis=0)) * self.grid
        prepared_ob = [prep(s) for s in blocked]
        prepared_al = [prep(s) for s in allowed]
        directions = [(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]
        costs, previous, incoming, queue = {}, {}, {}, []
        seq = 0
        for key in starts:
            costs[key] = 0.; incoming[key] = None
            heapq.heappush(queue, (hd[key[1:]], seq, 0., key)); seq += 1
        expanded, found = 0, None
        while queue and expanded < limit:
            _, _, cost, key = heapq.heappop(queue)
            if cost != costs[key]:
                continue
            l, y, x = key
            if targets[key]:
                found = key; break
            expanded += 1
            candidates = []
            for d, (dy, dx) in enumerate(directions):
                ny, nx = y + dy, x + dx
                if not (0 <= ny < free.shape[1] and 0 <= nx < free.shape[2] and free[l, ny, nx]):
                    continue
                old = incoming[key]
                if old is not None and min((d-old)%8, (old-d)%8) > 2:
                    continue
                nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) + (.35 if old is not None and old != d else 0)
                nk = l, ny, nx
                if nc >= costs.get(nk, math.inf):
                    continue
                line = LineString([self.point(key), self.point(nk)])
                if prepared_ob[l].intersects(line) or not prepared_al[l].covers(line):
                    continue
                candidates.append((nk, nc, d))
            for j in range(len(self.layers)):
                if j != l and via_masks[l, j][y, x]:
                    candidates.append(((j, y, x), cost + 4., None))
            for nk, nc, d in candidates:
                if nc < costs.get(nk, math.inf):
                    costs[nk] = nc; previous[nk] = key; incoming[nk] = d
                    heapq.heappush(queue, (nc + hd[nk[1:]], seq, nc, nk)); seq += 1
        if found is None:
            return {'status': 'SEARCH_LIMIT' if queue else 'NO_PATH_IN_SEARCH', 'expanded': expanded}
        path = [found]
        while path[-1] in previous:
            path.append(previous[path[-1]])
        path.reverse()
        routes, vias = [], []
        current = [self.point(path[0])]; l = path[0][0]
        for key in path[1:]:
            if key[0] != l:
                if len(current) > 1:
                    routes.append({'layer': self.layers[l], 'width_mm': self.width, 'points_mm': simplify(current)})
                vias.append({'position_mm': list(self.point(key)), 'diameter_mm': .5, 'drill_mm': .3})
                current = [self.point(key)]; l = key[0]
            else:
                current.append(self.point(key))
        if len(current) > 1:
            routes.append({'layer': self.layers[l], 'width_mm': self.width, 'points_mm': simplify(current)})
        for r in routes:
            r['points_mm'] = [[round(x, 6), round(y, 6)] for x, y in r['points_mm']]
        for v in vias:
            v['position_mm'] = [round(x, 6) for x in v['position_mm']]
        activated = []
        for group, route, index in [(a, routes[0] if routes else None, 0),
                                    (b, routes[-1] if routes else None, -1)]:
            if route is None:
                continue
            endpoint = Point(route['points_mm'][index])
            for terminal in group.get('prospective_pth_terminals', []):
                centre = terminal['position_mm']
                if (terminal['layer'] == route['layer']
                        and endpoint.distance(Point(centre)) <= self.grid*.8 + 1e-6):
                    neighbour = route['points_mm'][1 if index == 0 else -2]
                    line = LineString([centre, neighbour])
                    li = self.layers.index(route['layer'])
                    if prepared_ob[li].intersects(line) or not prepared_al[li].covers(line):
                        return {'status': 'PTH_CENTRE_ESCAPE_REJECTED', 'terminal': terminal}
                    route['points_mm'][index] = centre
                    activated.append(terminal)
                    break
        return {'status': 'PROPOSAL', 'expanded': expanded, 'routes': routes, 'vias': vias,
                'activate_pth_layers': activated,
                'length_mm': sum(math.dist(a_, b_) for r in routes for a_, b_ in zip(r['points_mm'], r['points_mm'][1:]))}


def main(args):
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    p = Planner(args.board, args.grid, args.layers, args.width)
    nets = args.net or sorted({q.GetNetname() for q in p.c.pads
                              if q.GetNetname() and not q.GetNetname().startswith('unconnected-')})
    results, proposals = [], 0
    for net in nets:
        gs = p.routing_groups(net)
        if len(gs) < 2:
            continue
        print(json.dumps({'net': net, 'groups': len(gs), 'phase': 'geometry'}), flush=True)
        geom = p.geometry(net)
        for i, a in enumerate(gs):
            for j, b in enumerate(gs[i+1:], i+1):
                row = {'net': net, 'groups': [a['pads'], b['pads']]}
                row.update(p.solve(a, b, geom, args.max_expanded))
                results.append(row)
                print(json.dumps({k:v for k,v in row.items() if k not in ['routes', 'groups']}
                                 | {'group_indices': [i,j]}), flush=True)
                if row['status'] == 'PROPOSAL':
                    proposals += 1
                    plan = {'revision': args.revision + str(proposals), 'board_sha256': p.c.sha,
                            'scope': 'Independent native-copper multi-layer proposal; no source changes; requires full validation',
                            'routes': [{**r, 'net': net} for r in row['routes']],
                            'vias': [{**v, 'net': net} for v in row['vias']],
                            'activate_pth_layers': row['activate_pth_layers'],
                            'search': {'grid_mm': args.grid, 'layers': args.layers,
                                       'eligible_layers': [ly for ly in args.layers if ly != 'In2.Cu' or net in p.in2_nets],
                                       'In2_policy': 'Exact unchanged native R13 allow-list; not an added net permission',
                                       'endpoint_groups': row['groups'], 'expanded': row['expanded']}}
                    (output / ('plan-' + str(proposals) + '.json')).write_text(json.dumps(plan, indent=2)+'\n')
                (output / 'searches.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps({'proposals': proposals, 'searches': len(results)}), flush=True)


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('board'); a.add_argument('output'); a.add_argument('revision')
    a.add_argument('--net', action='append'); a.add_argument('--grid', type=float, default=.1)
    a.add_argument('--width', type=float, default=.2)
    a.add_argument('--layers', nargs='+', choices=['F.Cu', 'B.Cu', 'In2.Cu', 'In3.Cu'], default=['B.Cu', 'In3.Cu', 'F.Cu'])
    a.add_argument('--max-expanded', type=int, default=300000)
    main(a.parse_args())
