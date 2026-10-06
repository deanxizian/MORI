"""Give J9 four thermal spokes room without relaxing native rules."""
import pcbnew as k
import json
from layout_P3R1 import track, pt, B
from helpers_P4 import paths
from geometry_guard_P3R1 import Guard
_, d, p, r = paths('power')
b = k.LoadBoard(str(p))
k.SaveBoard(str(r/'before_widen_J9.kicad_pcb'), b)
def remove(uid):
    t = next(t for t in b.GetTracks() if t.m_Uuid.AsString() == uid)
    b.Delete(t)
remove('a517fa1a-0d3a-4973-a63f-cf20f7310020')
jobs = [('/W_SENSE', [(60,21.4),(59.225,21.4),(59,21.175)])]
for uid in ['17803469-7dce-4d16-a183-551632ca9135',
            'a4accb7c-9b01-44bb-bade-dcf2d3b66ecd',
            '1c403249-c879-4512-a859-150ea198cfb8']:
    remove(uid)
jobs.append(('/CHG_N', [(71.5,53.3),(53.35,53.3),(49,48.95),(53.05,44.9),(54.1,44.9)]))
for net, points in jobs:
    guard = Guard(b, net)
    assert all(guard.line_clear(a,z,B) for a,z in zip(points,points[1:]))
    track(b,net,points,.2,B)
f = next(f for f in b.GetFootprints() if f.GetReference() == 'J12')
for g in f.GraphicalItems():
    if hasattr(g,'GetText') and g.GetText() == '+':
        g.SetPosition(pt(71,51.5))
k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(p), b)
(r/'widen_J9.json').write_text(json.dumps(dict(routes=jobs,thermal_rule_changed=False),indent=2)+'\n')
