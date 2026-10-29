"""Read-only local geometry/coupling screens for the independent R181C trial.

Nominal copper/Fab geometry and continuity are not noise or thermal qualification.
"""
import ast
import hashlib
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

b = Path('robot/.state/c3-completion/trials')
source = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c = Copper(b / 'R181C/MORI_Interface_C3.kicad_pcb')
plan = json.loads((b / 'R181C-plan.json').read_text())
audit = json.loads((b / 'R181C-checks/regression.json').read_text())
inspection = json.loads((b / 'R181C-inspection.json').read_text())
assert source.sha == plan['board_sha256']
node = next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'fab')
exec(compile(ast.Module(body=[node], type_ignores=[]), 'fab', 'exec'))
old_ids = set(plan['delete_copper'])
new = [t for t in c.segments if uid(t) not in source.by_id]
net = 'Net-(U1001-S2_{slash}_WHEEL_sense)'
assert len(new) == 13 and all(t.GetNetname() == net and t.GetLayer() == c.ids['F.Cu'] for t in new)
stroke = unary_union([c.shapes[uid(t), 'F.Cu'] for t in new])
ground = c.copper['GND', 'In1.Cu']
body_rows = []
for f in c.footprints:
    if f.GetLayer() != c.ids['B.Cu']:
        continue
    overlap = stroke.intersection(fab(f))
    if overlap.area > 1e-8:
        body_rows.append(dict(component=f.GetReference(), face='B.Cu', overlap_mm2=overlap.area, unshielded_by_In1_mm2=overlap.difference(ground).area))
projection_rows = []
for layer in ['In2.Cu', 'In3.Cu', 'B.Cu']:
    nets = sorted({c.by_id[u].GetNetname() for u, ly in c.shapes if ly == layer} | {n for n, ly, _ in c.fills if ly == layer})
    for other in nets:
        if other in [net, 'GND', '']:
            continue
        shape_ = c.copper.get((other, layer), GeometryCollection())
        overlap = stroke.intersection(shape_)
        if overlap.area > 1e-8:
            projection_rows.append(dict(net=other, layer=layer, overlap_mm2=overlap.area, unshielded_by_In1_mm2=overlap.difference(ground).area))
nearby = []
for (u, layer), geom in c.shapes.items():
    if layer != 'F.Cu' or c.by_id[u].GetNetname() in [net, 'GND', '']:
        continue
    d = stroke.distance(geom)
    if d < 1.5:
        obj = c.by_id[u]
        nearby.append(dict(uuid=u, net=obj.GetNetname(), kind=type(obj).__name__, pad=c.pad_name(obj) if isinstance(obj, pcb.PAD) else None, copper_edge_distance_mm=d))
nearby.sort(key=lambda r: r['copper_edge_distance_mm'])
retained_vias = [v for v in source.vias if uid(v) in c.by_id]
assert len(retained_vias) == 324
assert all(via_snapshot(source.board, v) == via_snapshot(c.board, c.by_id[uid(v)]) for v in retained_vias)
transfers = [r for r in audit['reference_transitions'] if r['uuid'] in ['6523d16f-5960-4140-95e5-2e28808a78f2', '03d1a50a-992f-43e2-b601-01d0aa0ad6e3']]
result = dict(
    scope=__doc__, source_sha256=source.sha, candidate_sha256=c.sha,
    removed_centerline_length_mm=sum(source.by_id[u].GetLength()/1e6 for u in old_ids),
    new_centerline_length_mm=sum(t.GetLength()/1e6 for t in new),
    removed_segment_count=len(old_ids), added_segment_count=len(new),
    track_counts=dict(before=len(source.segments), after=len(c.segments)),
    via_counts=dict(before=len(source.vias), after=len(c.vias)), new_holes=0,
    retained_vias_unchanged=324, original_ground_vias_preserved=inspection['source_ground_vias_preserved'],
    source_retired_via=plan['remove_obsolete_vias'], source_power_checks_pass=sum(r['status']=='PASS' for r in audit['power_width']),
    source_critical_adjacency_checks_pass=sum(r['status']=='PASS' for r in audit['critical_placement']),
    old_connection_changes=audit['lost_pad_connections'], old_reference_losses=audit['retained_trace_reference_loss'],
    same_face_nominal_body_hits=inspection['same_face_nominal_body_hits'],
    opposite_body_projection_review=body_rows, foreign_copper_projection_review=projection_rows,
    nearby_same_face_foreign_copper=nearby, reused_transfer_return_review=transfers,
    local_coupling_scope='In1 ground covers the recorded opposite/internal projections. Same-face separation is reported, not treated as a measured crosstalk or thermal margin. MOSFET and CAM regulator adjacency remain part of full-board electrical qualification.',
    manufacturer_sources=[
        dict(url='https://www.ti.com/lit/gpn/TMUX1511', revision='SCDS390B March 2025', sections='10.1-10.2, printed pages 27-28', applied='Keep the branch short, remove the superseded stub/transfer, retain continuous ground and review analog/digital crossings. These checks do not establish noise immunity.'),
        dict(url='https://www.ti.com/lit/ds/symlink/lm74502.pdf', revision='SNOSDE5A May 2022', sections='11.1, printed page 19', applied='The neighboring devices form the reverse-polarity/high-side switch. Its native MOSFET power and gate traces are not changed; all original power width and placement checks remain mandatory.')],
    noise_transient_thermal_qualification='NOT_TESTED', whole_board_visual='NOT_TESTED', physical='NOT_TESTED', manufacturing_release=False)
out = b / 'R181C-geometry-review.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['removed_centerline_length_mm','new_centerline_length_mm','track_counts','via_counts','same_face_nominal_body_hits','opposite_body_projection_review','reused_transfer_return_review']}, indent=2))
print('same-face nearest', json.dumps(nearby[:8]))
print('foreign unshielded', json.dumps([r for r in projection_rows if r['unshielded_by_In1_mm2'] > 1e-8]))
assert hashlib.sha256(Path(source.path).read_bytes()).hexdigest() == source.sha
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == c.sha
