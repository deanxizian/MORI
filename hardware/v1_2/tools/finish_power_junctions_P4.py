"""Final local P4 power edits; preserve load conductors and source rules.

UUID-targeted one-shot edit. Native ERC/DRC must be run after execution.
"""
import json
import pcbnew as k
from helpers_P4 import paths
from geometry_guard_P3R1 import Guard
from layout_P3R1 import track, pt, F, B

_, d, p, r = paths('power')
b = k.LoadBoard(str(p))
k.SaveBoard(str(r / 'before_final_junctions.kicad_pcb'), b)
log = []

def remove(uid):
    t = next(t for t in b.GetTracks() if t.m_Uuid.AsString() == uid)
    b.Delete(t)

remove('bca69b49-546f-4a23-a2e4-6a9018bf4214')
branches = [[(42.35, 30.35), (41.05, 31.65)],
            [(40.2, 30.8), (41.05, 31.65)],
            [(39.05, 30.35), (39.4, 30.0)]]
g = Guard(b, '/H_GATE_LOW')
assert all(g.line_clear(a, z, F) for a, z in branches)
for points in branches:
    track(b, '/H_GATE_LOW', points, .2, F)
log.append(dict(net='/H_GATE_LOW', action='perpendicular_T_branches', points=branches))

# J1 already has native four-spoke plane connections. Remove the redundant
# thin jumper that intersects a ground stitch at an acute angle; recheck opens.
remove('d10851f9-04e7-4088-a59e-a59a7932de62')
log.append(dict(net='/GND', action='remove_redundant_J1_thin_ground_jumper'))

for uid in ['33c41bcf-6400-4a0f-a2f2-b97b94ee34eb',
            '6485415c-10c7-4652-8e02-f641e1de016a',
            'b096833c-db4f-4f1c-af6a-eba8f796f146']:
    remove(uid)
points = [(54.4, 53.3), (50.05, 48.95), (54.1, 44.9)]
g = Guard(b, '/CHG_N')
assert all(g.line_clear(a, z, B) for a, z in zip(points, points[1:]))
track(b, '/CHG_N', points, .2, B)
log.append(dict(net='/CHG_N', action='clear_J9_thermal_without_short_jog', points=points))

t = next(t for t in b.GetTracks() if t.m_Uuid.AsString() == 'a517fa1a-0d3a-4973-a63f-cf20f7310020')
t.SetEnd(pt(59.15, 20.25))
log.append(dict(net='/W_SENSE', action='center_track_on_existing_via'))
k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(p), b)
(r / 'final_junctions.json').write_text(json.dumps(log, indent=2) + '\n')
