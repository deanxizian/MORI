"""Read-only power reservations, checked against every source width pair.

The output is a conservative planning constraint, not copper to manufacture.
Native refill and the unchanged 50 power checks remain mandatory. Sparse paths
are used only when their actual strokes fit the original copper; otherwise the
whole source component is retained and that conservative fallback is recorded.
"""
import copy
import hashlib
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from shapely import to_wkb

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import mask, simplify

b = Path('robot/.state/c3-completion/trials')
out = b / 'R182-supply-reservations'
out.mkdir(exist_ok=False)
c = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
expected_sha = '13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
assert c.sha == expected_sha
reports = json.loads(Path('robot/hardware/driver/evidence/R108P/power_width_regression.json').read_text())['reports']
nets = [r['net'] for r in reports]
assert len(nets) == len(set(nets)) == 10
physical = defaultdict(list)
for (u, ly), shape_ in c.shapes.items():
    physical[c.by_id[u].GetNetname(), ly].append(shape_)
physical = {k: unary_union(v) for k, v in physical.items()}
reserved = dict(physical)
probe = copy.copy(c)
rows, checks = [], []

def pairs(net, width):
    probe.__dict__['copper'] = reserved
    return probe.connected_pairs(net, width)

def connected(ids, allpairs):
    return all(tuple(sorted((ids[0], x))) in allpairs for x in ids[1:])

def tree(region, lands, native, width, grid):
    # Add a small planning margin, then verify the actual finished geometry.
    # If the source has no such margin the native-component fallback is used.
    radius = width / 2 + .008
    safe = native.buffer(-radius).intersection(region)
    if safe.is_empty:
        return None, {'reason': 'NO_MARGIN_REGION', 'grid_mm': grid}
    x0, y0, x1, y1 = safe.bounds
    xs = np.arange(math.floor(x0/grid)*grid, x1+grid/2, grid)
    ys = np.arange(math.floor(y0/grid)*grid, y1+grid/2, grid)
    xx, yy = np.meshgrid(xs, ys)
    free = mask(safe, xx, yy, True)
    iy, ix = np.where(free)
    count = len(iy)
    labels = np.full(free.shape, -1, dtype=np.int32)
    labels[iy, ix] = np.arange(count, dtype=np.int32)
    terminals = []
    for land in lands:
        indices = labels[free & mask(land, xx, yy, True)]
        if not len(indices):
            return None, {'reason': 'NO_MARGIN_TERMINAL', 'grid_mm': grid}
        terminals.append(indices)
    if not count:
        return None, {'reason': 'NO_GRID', 'grid_mm': grid}
    # Eight-neighbour graph. Whole path/stroke validation below rejects corner
    # cutting; a graph route alone is never accepted as a native reservation.
    rr, cc, vv = [], [], []
    height, breadth = free.shape
    for dy, dx in [(0,1), (1,0), (1,1), (1,-1)]:
        valid = (iy+dy >= 0) & (iy+dy < height) & (ix+dx >= 0) & (ix+dx < breadth)
        aa = labels[iy[valid], ix[valid]]
        bb = labels[iy[valid]+dy, ix[valid]+dx]
        ok = bb >= 0
        aa, bb = aa[ok], bb[ok]
        rr.extend([aa, bb]); cc.extend([bb, aa])
        cost = np.full(len(aa), grid * (math.sqrt(2) if dx and dy else 1))
        vv.extend([cost, cost])
    graph = coo_matrix((np.concatenate(vv), (np.concatenate(rr), np.concatenate(cc))), shape=(count,count)).tocsr()
    root_options = terminals[0]
    centre = lands[0].centroid
    distance = (xs[ix[root_options]]-centre.x)**2 + (ys[iy[root_options]]-centre.y)**2
    root = int(root_options[np.argmin(distance)])
    distances, predecessors = dijkstra(graph, directed=False, indices=root, return_predecessors=True)
    strokes, visited, paths = [], {root}, []
    for options in terminals[1:]:
        target = int(options[np.argmin(distances[options])])
        if not math.isfinite(float(distances[target])):
            return None, {'reason': 'DISCONNECTED_MARGIN_GRID', 'grid_mm': grid}
        path = [target]
        while path[-1] not in visited:
            parent = int(predecessors[path[-1]])
            if parent < 0:
                return None, {'reason': 'MISSING_PREDECESSOR', 'grid_mm': grid}
            path.append(parent)
        visited.update(path)
        if len(path) > 1:
            pts = simplify([(float(xs[ix[k]]), float(ys[iy[k]])) for k in path])
            line = LineString(pts)
            stroke = line.buffer(radius)
            if stroke.difference(native).area > 1e-7:
                return None, {'reason': 'STROKE_OUTSIDE_NATIVE', 'grid_mm': grid}
            strokes.append(stroke)
            paths.append([list(p) for p in pts])
    # Include root disk when multiple lands touch the same raster node.
    strokes.append(Point(float(xs[ix[root]]), float(ys[iy[root]])).buffer(radius))
    result = unary_union(strokes)
    if result.difference(native).area > 1e-7:
        return None, {'reason': 'ROOT_OUTSIDE_NATIVE', 'grid_mm': grid}
    return result, {'reason': 'PATH_TREE', 'grid_mm': grid, 'paths_mm': paths, 'grid_nodes': count}

for net in nets:
    start = time.monotonic()
    anchors = c.anchors(net)
    for width in [.48, .4, .3, .2, 0]:
        source = c.connected_pairs(net, width)
        current = pairs(net, width)
        if source <= current:
            checks.append(dict(net=net, width_mm=width, source_pairs=len(source), lost_pairs=0, status='PASS'))
            continue
        for ly in LAYERS:
            native = c.copper.get((net, ly), GeometryCollection())
            regions = parts(native.buffer(-width/2) if width else native)
            # Larger/native components first, deterministic for reproducibility.
            for region_index, region in enumerate(sorted(regions, key=lambda g: (-g.area, g.bounds))):
                aa = [(uid(a), c.shapes.get((uid(a), ly))) for a in anchors]
                aa = [(u,s) for u,s in aa if s is not None and s.intersects(region)]
                aa.sort(key=lambda x: (-x[1].area, x[0]))
                if len(aa) < 2 or connected([u for u,s in aa], current):
                    continue
                result, detail = tree(region, [s for u,s in aa], native, width, .05)
                if result is None and detail['reason'] in ['NO_MARGIN_TERMINAL','DISCONNECTED_MARGIN_GRID','STROKE_OUTSIDE_NATIVE']:
                    result, fine = tree(region, [s for u,s in aa], native, width, .025)
                    fine['coarse_failure'] = detail['reason']; detail = fine
                fallback = result is None
                if fallback:
                    result = native.intersection(region.buffer(width/2 + .01))
                    detail['fallback'] = 'NATIVE_COMPONENT'
                key = net, ly
                before = reserved.get(key, GeometryCollection())
                reserved[key] = unary_union([before, result])
                newpairs = pairs(net, width)
                if not connected([u for u,s in aa], newpairs):
                    # Conservative layer fallback, never weaken a check to pass.
                    reserved[key] = native
                    detail['fallback'] = 'FULL_NATIVE_LAYER_AFTER_COMPONENT_CHECK'
                    fallback = True
                    newpairs = pairs(net, width)
                    assert connected([u for u,s in aa], newpairs), (net,ly,width,'native inconsistency')
                current = newpairs
                rows.append(dict(net=net, layer=ly, width_mm=width, region_index=region_index,
                                 anchors=[u for u,s in aa], native_region_area_mm2=region.area,
                                 added_area_mm2=reserved[key].difference(before).area,
                                 conservative_fallback=fallback, **detail))
        lost = source - pairs(net, width)
        assert not lost, (net,width,len(lost))
        checks.append(dict(net=net, width_mm=width, source_pairs=len(source), lost_pairs=0, status='PASS'))
    print(json.dumps(dict(net=net, status='ALL_FIVE_SOURCE_WIDTHS_PRESERVED', seconds=time.monotonic()-start,
                          fallback_count=sum(r['conservative_fallback'] for r in rows if r['net']==net))), flush=True)
    (out/'progress.json').write_text(json.dumps(dict(source_sha256=c.sha, checks=checks, results=rows),indent=2)+'\n')

# Recheck all widths after lower-width unions. Conservative native fallback
# also covers numerical topology changes introduced by polygon union/buffer.
final_fallbacks=[]
for net in nets:
    losses=[]
    for width in [0,.2,.3,.4,.48]:
        lost=c.connected_pairs(net,width)-pairs(net,width)
        if lost: losses.append(dict(width_mm=width,lost_pairs=len(lost)))
    if losses:
        for key,g in c.copper.items():
            if key[0]==net: reserved[key]=g
        final_fallbacks.append(dict(net=net,reason='FINAL_ALL_WIDTH_RECHECK',losses=losses))

files=[]
for i, ((net,ly), original) in enumerate(sorted(c.copper.items())):
    if net not in nets:
        continue
    full = reserved.get((net,ly),GeometryCollection())
    assert full.difference(original).area < 1e-7, (net,ly,'outside original copper')
    # Preserve a 1 um overlap into fixed native objects so recombination does
    # not split a shared numerical boundary. No geometry extends outside full.
    raw_zone = full.difference(physical.get((net,ly),GeometryCollection()))
    zone_only = raw_zone.buffer(.001).intersection(full) if not raw_zone.is_empty else raw_zone
    if zone_only.is_empty:
        continue
    filename=f'{i:03d}-{ly}.wkb'
    payload=to_wkb(zone_only)
    (out/filename).write_bytes(payload)
    files.append(dict(net=net,layer=ly,path=filename,sha256=hashlib.sha256(payload).hexdigest(),
                      reserved_zone_area_mm2=zone_only.area,native_copper_area_mm2=original.area))
assert len(checks)==50 and all(r['status']=='PASS' for r in checks)
# Independent final reconstruction from the emitted WKB rather than objects
# left in memory ensures that consumers get the checked geometry.
from shapely import from_wkb
decoded=dict(physical)
for row in files:
    key=row['net'],row['layer']
    decoded[key]=unary_union([decoded.get(key,GeometryCollection()),from_wkb((out/row['path']).read_bytes())])
probe.__dict__['copper']=decoded
roundtrip=[]
for net in nets:
    for width in [0,.2,.3,.4,.48]:
        src=c.connected_pairs(net,width);lost=src-probe.connected_pairs(net,width)
        assert not lost,(net,width,'WKB roundtrip',len(lost))
        roundtrip.append(dict(net=net,width_mm=width,source_pairs=len(src),lost_pairs=0,status='PASS'))
result=dict(scope=__doc__,source_sha256=c.sha,checks=checks,roundtrip_checks=roundtrip,
            results=rows,files=files,final_fallbacks=final_fallbacks,conservative_fallback_count=sum(r['conservative_fallback'] for r in rows),
            adopted=False,manufacturing_release=False)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
print(json.dumps(dict(status='50_CHECKS_AND_SERIALIZATION_PASS',files=len(files),fallbacks=result['conservative_fallback_count'])),flush=True)
