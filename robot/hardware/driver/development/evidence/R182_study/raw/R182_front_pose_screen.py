"""Read-only front-face U301 placement comparison with C301 explicitly released.

Use native footprint flipping and exact pad geometry. Full transformed track
guard is used as the via exclusion (no grandfathered rear-face cutout is moved
to the front). This is stricter screening, not a board edit or qualification.
Actual guard transformation, bypass, every connection and all checks remain.
"""
import ast, collections, hashlib, json, math, sys
from pathlib import Path
from shapely.affinity import rotate, scale, translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

b = Path('robot/.state/c3-completion/trials')
out = b / 'R182-front-U301-C301-pose-screen.json'
assert not out.exists()
c = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
source_sha = '13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
assert c.sha == source_sha
for name, filename in [('fab', 'R138_joint_search.py'), ('outline', 'R167_joint_pose_screen.py')]:
    node = next(n for n in ast.parse((b / filename).read_text()).body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), name, 'exec'))
prior = json.loads((b / 'R182-global-U301-C301-pose-screen.json').read_text())
assert prior['source_sha256'] == source_sha
retired = set(prior['retired_tracks'])
original = next(f for f in c.footprints if f.GetReference() == 'U301')
cap = next(f for f in c.footprints if f.GetReference() == 'C301')
mine = {uid(p) for p in original.Pads()}
capids = {uid(p) for p in cap.Pads()}
f = pcb.FOOTPRINT(original)
f.Flip(f.GetPosition(), pcb.FLIP_DIRECTION_LEFT_RIGHT)
assert f.GetLayer() == c.ids['F.Cu']
assert {p.GetNumber(): p.GetNetname() for p in f.Pads()} == {p.GetNumber(): p.GetNetname() for p in original.Pads()}
origin, angle0 = xy(f.GetPosition()), f.GetOrientationDegrees()
nets = {p.GetNetname() for p in f.Pads()}
owned = [k for k in c.keepouts if k['name'].startswith('BODY_U301_')]
trackguard = scale(unary_union([k['shape'] for k in owned if k['tracks']]), xfact=-1, yfact=1, origin=origin)
bodies = unary_union([fab(o) for o in c.footprints if o.GetLayer() == c.ids['F.Cu'] and o.GetReference() not in ['U301', 'C301']])
yards = unary_union([outline(o, pcb.F_CrtYd) for o in c.footprints if o.GetLayer() == c.ids['F.Cu'] and o.GetReference() not in ['U301', 'C301']])
vias = unary_union([c.shapes[uid(v), 'F.Cu'] for v in c.vias])
tracks = unary_union([c.shapes[uid(t), 'F.Cu'] for t in c.segments if t.GetLayer() == c.ids['F.Cu'] and uid(t) not in retired])
foreign = {n: unary_union([s for (u, ly), s in c.shapes.items() if ly == 'F.Cu' and u not in mine | retired | capids and c.by_id[u].GetNetname() != n]) for n in nets}
board_inset = box(.5, .5, 69.5, 34.5)
rows, reject = [], collections.Counter()
for angle in [0, 90, 180, 270]:
    part = pcb.FOOTPRINT(f)
    part.SetOrientationDegrees(angle)
    body, yard = fab(part), outline(part, pcb.F_CrtYd)
    gd = rotate(trackguard, -(angle - angle0), origin=origin)
    pads = {p.GetNumber(): (p.GetNetname(), shape(p, c.ids['F.Cu']), xy(p.GetPosition())) for p in part.Pads()}
    for pos in [(x / 2, y / 2) for x in range(3, 138) for y in range(3, 68)]:
        dx, dy = pos[0] - origin[0], pos[1] - origin[1]
        pp = {k: (n, translate(s, xoff=dx, yoff=dy), (xy_[0] + dx, xy_[1] + dy)) for k, (n, s, xy_) in pads.items()}
        bo, ya = translate(body, xoff=dx, yoff=dy), translate(yard, xoff=dx, yoff=dy)
        if bo.intersection(bodies).area > 1e-8 or ya.intersection(yards).area > 1e-8:
            reject['package_or_courtyard'] += 1
            continue
        if not board_inset.covers(unary_union([bo] + [s for n, s, pt in pp.values()])):
            reject['edge'] += 1
            continue
        if any(s.distance(vias) < .1999996 - 1e-9 or s.distance(foreign[n]) < .1999996 - 1e-9 for n, s, pt in pp.values()):
            reject['pad_clearance'] += 1
            continue
        gg = translate(gd, xoff=dx, yoff=dy)
        if gg.intersection(vias).area > 1e-8:
            reject['full_guard_existing_vias'] += 1
            continue
        if gg.intersection(tracks).area > 1e-8 or bo.difference(unary_union([s for n, s, pt in pp.values()])).intersection(tracks).area > 1e-8:
            reject['retained_tracks'] += 1
            continue
        near_ground = min(math.dist(pp['4'][2], xy(v.GetPosition())) for v in c.vias if v.GetNetname() == 'GND')
        if near_ground > 3:
            reject['distant_ground_via'] += 1
            continue
        rows.append(dict(face='F.Cu', position_mm=list(pos), rotation_deg=angle,
                         nearest_ground_via_mm=near_ground, displacement_mm=math.dist(pos, origin),
                         pads={k: dict(net=n, position_mm=list(pt)) for k, (n, s, pt) in pp.items()}))
rows.sort(key=lambda r: (r['displacement_mm'], r['nearest_ground_via_mm']))
out.write_text(json.dumps(dict(scope=__doc__, source_sha256=c.sha, retired_tracks=sorted(retired),
    candidates=rows, rejections=dict(reject), grid_mm=.5, search_bounds_mm=[1.5, 1.5, 68.5, 33.5],
    native_board_modified=False, simultaneous_routes='NOT_TESTED', manufacturer_and_assembly='NOT_TESTED', adopted=False), indent=2) + '\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == source_sha
print(json.dumps(dict(poses=len(rows), rejections=dict(reject), best=rows[:8])), flush=True)
