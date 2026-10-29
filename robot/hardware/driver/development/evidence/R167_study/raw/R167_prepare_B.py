"""Compare U1702 rotated 90 degrees with the same courtyard-correct Q1701 pose.

U1702 is F (57.75,15.25), 90 degrees. The native placement screen reports
38 possible ports and 1.755393 mm nominal VDD-to-C1702 spacing. This is only
an incomplete placement comparison; every source via and component value stays.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R167B-plan.json';assert not out.exists()
p=json.loads((b/'R167A-plan.json').read_text())
screen=json.loads((b/'R167-joint-pose-screen.json').read_text())
pose=next(r for r in screen['poses'] if r['position_mm']==[57.75,15.25] and r['rotation_deg']==90)
assert pose['legal_port_grid_points']==38 and not pose['requires_old_ACT_via_relocation']
u=next(t for t in p['translations'] if t['reference']=='U1702')
u.update(delta_mm=[.25,-.5],rotation_deg=90)
p.update(revision='R167B',scope=__doc__)
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
