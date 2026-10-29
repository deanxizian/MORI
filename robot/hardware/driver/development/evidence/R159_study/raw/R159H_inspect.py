"""Read-only nominal body and new supply corridor inspection; not physical qualification."""
import ast
import json
import sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

b = Path('robot/.state/c3-completion/trials')
out = b / 'R159H-inspection.json'
assert not out.exists()
a = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c = Copper(b / 'R159H/MORI_Interface_C3.kicad_pcb')
assert a.sha == '83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
assert c.sha == 'bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
node = next(n for n in ast.parse((b / 'R138_joint_search.py').read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'fab')
exec(compile(ast.Module(body=[node], type_ignores=[]), 'fab', 'exec'))
pa = {a.pad_name(p): p for p in a.pads}
pc = {c.pad_name(p): p for p in c.pads}
fps = {f.GetReference(): f for f in c.footprints}
fab_shapes = [(f, fab(f)) for f in c.footprints]
lands = {(net, ly): unary_union([s for (u, l), s in c.shapes.items()
          if l == ly and isinstance(c.by_id[u], pcb.PAD) and c.by_id[u].GetNetname() == net])
          for net, ly in {(t.GetNetname(), c.board.GetLayerName(t.GetLayer()))
                         for t in c.segments if uid(t) not in a.by_id}}
new = []
for t in c.segments:
    if uid(t) in a.by_id:
        continue
    ly = c.board.GetLayerName(t.GetLayer())
    outside = c.shapes[uid(t), ly].difference(lands[t.GetNetname(), ly])
    projections = []
    for f, body in fab_shapes:
        area = outside.intersection(body).area
        if area > 1e-6:
            projections.append({'reference': f.GetReference(),
                'mounted_layer': c.board.GetLayerName(f.GetLayer()),
                'same_face': f.GetLayer() == t.GetLayer(), 'area_mm2': area})
    new.append({'uuid': uid(t), 'net': t.GetNetname(), 'layer': ly,
        'width_mm': t.GetWidth()/1e6, 'start_mm': xy(t.GetStart()), 'end_mm': xy(t.GetEnd()),
        'length_mm': LineString([xy(t.GetStart()), xy(t.GetEnd())]).length,
        'nominal_body_projections': projections})

new_vias = [v for v in c.vias if uid(v) not in a.by_id]
assert len(new_vias) == 1 and xy(new_vias[0].GetPosition()) == (51.35, 6.2)
new_ups = uid(new_vias[0])
old_ups = '4150016a-d870-4d6e-beae-177f9b3cdd3a'
checks = []
def pair(net, width, first, second, required, label):
    result = tuple(sorted([first, second])) in c.connected_pairs(net, width)
    checks.append({'label': label, 'net': net, 'width_mm': width,
        'from_uuid': first, 'to_uuid': second, 'connected': result, 'required': required})

ups_net = pc['R1001.1'].GetNetname()
for width in [0, .18, .28, .33, .48]:
    pair(ups_net, width, new_ups, old_ups, width <= .33, 'new UPS via to retained UPS supply via')
    pair(ups_net, width, uid(pc['R1001.1']), old_ups, width <= .33, 'R1001 input to main UPS supply')
for width in [0, .18]:
    pair('MOTION_3V3', width, uid(pc['C505.1']), uid(pc['C1701.1']), True, 'C505 supply to existing local supply')
    for dest in ['R1707.1', 'R1101.2', 'R1702.1']:
        pair('/WHEEL_VM', width, uid(pc['R1002.1']), uid(pc[dest]), True, 'R1002 input to ' + dest)

local = []
vias = ['9fc6be27-25b2-4bce-8f44-98f39ccd1aa1',
        'aa3ea505-081f-4d12-a9a9-b7d9b2cf4e57', 'c89d9b75-62b7-4bdc-8fe8-09516366b58c']
for width in [0, .18, .28, .33, .48]:
    row = {'width_mm': width}
    for name, obj, pads in [('source', a, pa), ('candidate', c, pc)]:
        pairs = obj.connected_pairs('MOTION_3V3', width)
        row[name] = {v: {p: tuple(sorted([v, uid(pads[p])])) in pairs
                       for p in ['C1701.1', 'U1701.4', 'U1701.9', 'R1310.2']} for v in vias}
    local.append(row)
local_preserved = all(not r['source'][v][p] or r['candidate'][v][p]
                      for r in local for v in vias for p in ['C1701.1', 'U1701.4', 'U1701.9', 'R1310.2'])
via_ids = vias + [old_ups, 'c9ef7bb5-bef9-48b7-b4cf-23501fe0a859', new_ups]
same_face = [dict(track=t['uuid'], net=t['net'], layer=t['layer'], **p)
             for t in new for p in t['nominal_body_projections'] if p['same_face']]
d = {'scope': __doc__, 'source_sha256': a.sha, 'candidate_sha256': c.sha,
     'counts': {'segments': len(c.segments), 'vias': len(c.vias), 'footprints': len(c.footprints),
                'new_segments': len(new)},
     'new_tracks': new, 'same_face_nominal_body_hit_count': len(same_face), 'same_face_hits': same_face,
     'new_supply_corridor_checks': checks,
     'required_new_supply_corridors_pass': all(r['connected'] for r in checks if r['required']),
     'local_MOTION_3V3_width_pairs': local, 'source_local_pair_widths_preserved': local_preserved,
     'via_snapshots': [{'uuid': v, 'source': via_snapshot(a.board, a.by_id[v]) if v in a.by_id else None,
                       'candidate': via_snapshot(c.board, c.by_id[v]),
                       'candidate_native_contact_layers': via_contact_layers(c.board, c.by_id[v])} for v in via_ids],
     'wheel_groups': c.pad_groups()['/WHEEL_VM'],
     'R1702_R1703_courtyard_gap_mm': polyset(fps['R1702'].GetCourtyard(pcb.F_CrtYd)).distance(
                                           polyset(fps['R1703'].GetCourtyard(pcb.F_CrtYd))),
     'candidate_middle_node_length_mm': sum(t['length_mm'] for t in new if t['net'] == 'Net-(R1702-~-Pad2)'),
     'limits': ['Fab polygons are nominal library bodies, not measured installed component envelopes.',
                'Width erosion checks corridor continuity, not current capacity or via ampacity.',
                'Opposite-face/internal projections require individual reference/coupling/thermal review.',
                'Sampling branches are not the main actuator feed; no load current rating is inferred.'],
     'physical': 'NOT_TESTED', 'manufacturing_release': False}
out.write_text(json.dumps(d, indent=2) + '\n')
print(json.dumps({k: d[k] for k in ['candidate_sha256', 'counts', 'same_face_nominal_body_hit_count',
    'same_face_hits', 'required_new_supply_corridors_pass', 'source_local_pair_widths_preserved',
    'wheel_groups', 'R1702_R1703_courtyard_gap_mm', 'candidate_middle_node_length_mm']}))
print(json.dumps({'new_supply_checks': checks,
    'projection_refs': sorted({p['reference'] for t in new for p in t['nominal_body_projections']})}))
