"""Move the LIMIT diagonal outward by 0.065 mm in X+Y after exact nominal Fab review.
R159F native DRC passes, but its 0.20 mm LIMIT trace clips the U1701 nominal
B-side Fab corner by 0.000494 mm2. Preserve F and all native constraints;
retain both endpoints and the route width while moving only its two elbows.
"""
import json
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
p = json.loads((b / 'R159F-plan.json').read_text())
p['revision'] = 'R159G'
p['scope'] = __doc__
route = next(r for r in p['routes'] if r['net'] == 'Net-(U1701-LIMIT)')
assert route['points_mm'] == [[46.45, 9.7], [46.45, 10.04], [45.59, 10.9], [44.025, 10.9], [44.025, 11.3]]
route['points_mm'] = [[46.45, 9.7], [46.45, 9.975], [45.525, 10.9], [44.025, 10.9], [44.025, 11.3]]
out = b / 'R159G-plan.json'
with out.open('x') as f:
    json.dump(p, f, indent=2)
    f.write('\n')
print('R159G plan written; F unchanged')
