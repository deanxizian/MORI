"""Joint LIMIT-corner and UPS-hole clearance candidate, preserving all ground holes.
G removes the mounted-face nominal body clip but its diagonal intersects the
nearby UPS via's In4 reference void. Move that existing UPS hole 0.075 mm up,
retain its diameter/drill and F feed width, then refill and check all layers.
"""
import json
from pathlib import Path
b = Path('robot/.state/c3-completion/trials')
p = json.loads((b / 'R159G-plan.json').read_text())
p['revision'] = 'R159H'
p['scope'] = __doc__
v = next(v for v in p['move_vias'] if v['uuid'] == '4150016a-d870-4d6e-beae-177f9b3cdd3a')
assert v['position_mm'] == [45.29, 10.125]
v['position_mm'] = [45.29, 10.05]
v['reason'] = 'Jointly clear the mounted-face U1701 Fab corner and its LIMIT reference corridor. Keep the original UPS transfer at full diameter/drill and preserve every old supply and signal reference after native refill.'
r = next(r for r in p['routes'] if r['net'] == '/UPS_BAT' and r['layer'] == 'F.Cu')
assert r['points_mm'][-1] == [45.29, 10.125]
r['points_mm'][-1] = [45.29, 10.05]
with (b / 'R159H-plan.json').open('x') as f:
    json.dump(p, f, indent=2)
    f.write('\n')
print('R159H plan written; F/G unchanged')
