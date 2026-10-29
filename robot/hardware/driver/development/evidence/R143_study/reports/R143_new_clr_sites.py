"""Screen replacement CLR via sites for explicit D2 reuse of the old via.

Read-only geometric screen, not a native DRC/power qualification. Existing
non-CLR trace reference copper stays protected. CLR traces intersecting a new
own transfer are listed for explicit redesign and subsequent full review.
"""
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np
from shapely import intersects_xy
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

base = Path('robot/.state/c3-completion/trials')
c = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha == '2a7c04b8430875a0f8f9e4bdde4b789da6b8efb5f84ee991a360f1d5b6d006dd'
old = '819eb181-4e28-4093-bf9b-3792433636d0'
obs = []
for (u, ly), s in c.shapes.items():
    o = c.by_id[u]
    if isinstance(o, pcb.PAD) or o.GetNetname() != '/CLR_N' or u == old:
        obs.append(s.buffer(.457))
obs.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
obs.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias)
obs.extend(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557)
           for q in c.pads if max(xy(q.GetDrillSize())) > 0)
physical = unary_union(obs)
ref_shapes = []
own = []
for t in c.segments:
    ly = c.board.GetLayerName(t.GetLayer())
    if ly not in REFERENCE or t.GetNetname() == 'GND':
        continue
    g = c.shapes[uid(t), ly].intersection(c.copper.get(('GND', REFERENCE[ly]), GeometryCollection()))
    if t.GetNetname() == '/CLR_N':
        own.append((t, g))
    else:
        ref_shapes.append(g)
foreign_reference_guard = unary_union(ref_shapes).buffer(.657)
xs, ys = np.arange(26, 34.001, .05), np.arange(10.8, 17.001, .05)
xx, yy = np.meshgrid(xs, ys)
physical_free = ~intersects_xy(physical, xx, yy)
free = physical_free & ~intersects_xy(foreign_reference_guard, xx, yy)
rows = []
for iy, ix in zip(*np.where(free)):
    pt = [round(float(xs[ix]), 4), round(float(ys[iy]), 4)]
    void = Point(pt).buffer(.655)
    hits = [{'uuid': uid(t), 'layer': c.board.GetLayerName(t.GetLayer()),
             'start_mm': xy(t.GetStart()), 'end_mm': xy(t.GetEnd()),
             'currently_referenced_intersection_mm2': g.intersection(void).area}
            for t, g in own if g.intersection(void).area > 1e-8]
    rows.append({'position_mm': pt, 'distance_to_old_via_mm': math.dist(pt, [30.4, 14]),
                 'CLR_tracks_needing_transfer_review': hits})
rows.sort(key=lambda row: row['distance_to_old_via_mm'])
chosen = []
for row in rows:
    if all(math.dist(row['position_mm'], q['position_mm']) > .35 for q in chosen):
        chosen.append(row)
    if len(chosen) == 20:
        break
out = base/'R143-new-CLR-via-sites.json'
with out.open('x') as f:
    json.dump({'scope': __doc__, 'source_sha256': c.sha, 'grid_mm': .05,
               'bounds_mm': [26, 10.8, 34, 17], 'physical_free_count': int(physical_free.sum()),
               'foreign_reference_safe_count': len(rows), 'chosen': chosen}, f, indent=2)
    f.write('\n')
print(json.dumps({'physical_free_count': int(physical_free.sum()),
                  'foreign_reference_safe_count': len(rows), 'chosen': chosen[:8]}, indent=2))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == c.sha
