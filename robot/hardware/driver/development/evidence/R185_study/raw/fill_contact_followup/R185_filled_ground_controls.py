"""Check actual two-plane fill contacts; simulate orphaned vias in memory only."""
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import Copper, Point, uid, xy

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
out = b / 'R185-filled-ground-controls.json'
assert not out.exists()
via_id = '2e7f36fc-97b4-4bdc-ac9d-b6a6321965ed'
rows = []
boards = []
for name, path, audit_path in [
    ('R181C', dev / 'native/MORI_Interface_C3.kicad_pcb', dev / 'evidence/R181C/regression.json'),
    ('R185I', b / 'R185I/MORI_Interface_C3.kicad_pcb', b / 'R185I-audit.json'),
]:
    c = Copper(path)
    boards.append(c)
    old = json.loads(audit_path.read_text())
    assert old['board_sha256'] == c.sha
    grounds = c.ground_reference_anchors
    ground_ids = {uid(g) for g in grounds}
    ground_vias = [v for v in c.vias if v.GetNetname() == 'GND']
    assert len(ground_vias) == 114 and all(uid(v) in ground_ids for v in ground_vias)
    changes = []
    for transition in old['reference_transitions']:
        nearest = min((Point(transition['position_mm']).distance(Point(xy(g.GetPosition())))
                       for g in grounds), default=None)
        status = ('NOT_APPLICABLE' if len(transition['reference_layers']) <= 1 else
                  ('PASS' if nearest is not None and nearest <= 2 else 'FAIL'))
        if nearest is None or abs(nearest - transition['nearest_ground_mm']) > 1e-9 or status != transition['status']:
            changes.append(dict(uuid=transition['uuid'], nearest_ground_mm=nearest, status=status))
    assert not changes
    rows.append(dict(name=name + '_actual_fill_contacts', status='PASS', board_sha256=c.sha,
                     eligible_ground_anchors=len(grounds), ground_vias_with_both_contacts=len(ground_vias),
                     moved_via_contact_mm2=c.ground_reference_contacts(c.by_id[via_id]),
                     transition_changes=changes, transition_flags=sum(r['status'] == 'FAIL' for r in old['reference_transitions'])))

c = boards[-1]
c.copper  # Retain full copper, including the via itself, to expose the old false positive.
for missing in [('In1.Cu',), ('In4.Cu',), ('In1.Cu', 'In4.Cu')]:
    trial = copy.copy(c)
    trial.fills = [(net, ly, shape.difference(c.shapes[via_id, ly].buffer(.05))
                    if net == 'GND' and ly in missing else shape) for net, ly, shape in c.fills]
    trial.__dict__.pop('reference_ground_fills', None)
    trial.__dict__.pop('ground_reference_anchors', None)
    old_proxy = all(trial.shapes[via_id, ly].intersects(trial.copper['GND', ly])
                    for ly in ['In1.Cu', 'In4.Cu'])
    contacts = trial.ground_reference_contacts(trial.by_id[via_id])
    assert old_proxy and all(contacts[ly] == 0 for ly in missing)
    assert via_id not in {uid(g) for g in trial.ground_reference_anchors}
    rows.append(dict(name='reject_missing_' + '_'.join(missing), status='PASS',
                     legacy_self_contact_proxy_would_pass=old_proxy, actual_fill_contact_mm2=contacts,
                     orphan_rejected=True, mutation='Geometry-only in memory; no PCB saved.'))

assert all(hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == c.sha for c in boards)
out.write_text(json.dumps(dict(scope=__doc__, status='PASS', checks=rows, boards_saved=False,
                              limits='Zone-contact geometry only; native connectivity, return impedance and physical qualification remain separate.'), indent=2) + '\n')
print(json.dumps(dict(status='PASS', checks=len(rows))))
