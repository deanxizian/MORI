"""Source-bound geometry for coordinated reset/clamp/charge-pump/gate-RC study.

Planning only. Enumerated terminal tracks and three non-ground vias are omitted
from obstacle geometry; no board is saved. All ground vias, fixed interfaces,
source native rules and eventual restoration requirements remain unchanged.
"""
import ast, collections, hashlib, json, math, sys
from pathlib import Path
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

b = Path('robot/.state/c3-completion/trials')
c = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha == '13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
for name, fn in [('fab', 'R138_joint_search.py'), ('outline', 'R167_joint_pose_screen.py')]:
    node = next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), name, 'exec'))
prior = json.loads((b/'R183-clamp-cap-D1602-pose-screen.json').read_text())
assert prior['source_sha256'] == c.sha
retired = set(prior['prospective_retired_tracks'])
released_vias = set(prior['prospective_released_non_ground_vias'])
rc = json.loads((b/'R184-gate-RC-inventory.json').read_text())
assert rc['source_sha256'] == c.sha
retired.update(r['uuid'] for r in rc['tracks'] if r['net'] == 'Net-(C1603-~-Pad1)')
retired.update({
    '0f653977-4c14-55db-8a01-9f9bf9b291ac',
    'd911e2ac-e25e-5630-a995-8605fe736ccd',
    '8e35b6ed-a6d6-434a-9abd-edb9e740bbac',
    '953e253f-2ff4-45f0-b26c-bc55efacd3e2',
})
assert len(retired) == 36
assert all(u in c.by_id and isinstance(c.by_id[u], pcb.PCB_TRACK) and not isinstance(c.by_id[u], pcb.PCB_VIA) for u in retired)
assert all(isinstance(c.by_id[u], pcb.PCB_VIA) and c.by_id[u].GetNetname() != 'GND' for u in released_vias)
released_refs = {'D301', 'D1602', 'C1602', 'R1601', 'C1603'}
mine = {uid(p) for f in c.footprints if f.GetReference() in released_refs for p in f.Pads()}
replacement = LineString([(32.1, 13.15), (32.1, 13.85)]).buffer(.1)
footprints = {f.GetReference(): f for f in c.footprints}
pads = {c.pad_name(p): p for p in c.pads}
bodies = unary_union([fab(f) for f in c.footprints if f.GetLayer() == pcb.B_Cu and f.GetReference() not in released_refs])
yards = unary_union([outline(f, pcb.B_CrtYd) for f in c.footprints if f.GetLayer() == pcb.B_Cu and f.GetReference() not in released_refs])
mounts = unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'B.Cu' in k['layers']])
pth = unary_union([s for (u, ly), s in c.shapes.items() if ly == 'B.Cu' and isinstance(c.by_id[u], pcb.PAD) and c.by_id[u].GetAttribute() == pcb.PAD_ATTRIB_PTH])
holes = unary_union([Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize())) > 0])
vias = unary_union([s for (u, ly), s in c.shapes.items() if ly == 'B.Cu' and isinstance(c.by_id[u], pcb.PCB_VIA) and u not in released_vias])
tracks = unary_union([s for (u, ly), s in c.shapes.items() if ly == 'B.Cu' and isinstance(c.by_id[u], pcb.PCB_TRACK) and not isinstance(c.by_id[u], pcb.PCB_VIA) and u not in retired]+[replacement])

def geometry(ref, row):
    f = pcb.FOOTPRINT(footprints[ref])
    f.SetOrientationDegrees(row['rotation_deg'])
    old = xy(f.GetPosition()); pos = row['position_mm']
    f.Move(pcb.VECTOR2I(round((pos[0]-old[0])*1e6), round((pos[1]-old[1])*1e6)))
    return dict(row=row, body=fab(f), yard=outline(f, pcb.B_CrtYd),
                pads={p.GetNumber(): (p.GetNetname(), shape(p, c.ids['B.Cu']), xy(p.GetPosition())) for p in f.Pads()})

def compatible(a, z):
    if a['yard'].intersection(z['yard']).area > 1e-8 or a['body'].intersection(z['body']).area > 1e-8:
        return False
    return not any(s.distance(g) < .1999996-1e-9 for n,s,pt in a['pads'].values() for m,g,qt in z['pads'].values() if n != m)
