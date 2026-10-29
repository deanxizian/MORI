"""Native preparation for the courtyard-screened Q1701 orientation.

Q1701 moves (+0.25,-0.25) mm and rotates from 180 to 90 degrees. C1702 stays.
Retain the six explicit input-lead removals for reconstruction. The rejected C
FAULT lead and through hole are not present; choose any new port from all-layer
native geometry after this independent preparation is refilled.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R166D-plan.json';assert not out.exists()
p=json.loads((b/'R166C-plan.json').read_text());s=json.loads((b/'R166-placement-screen-v2.json').read_text())
assert s['source_sha256']==p['board_sha256'] and s['native_R166C_courtyard_rejection_reproduced']
assert any(r['Q1701']['position_mm']==[57,14] and r['Q1701']['rotation_deg']==90 and r['C1702']['position_mm']==[59.5,13.2] and r['C1702']['rotation_deg']==90 for r in s['combined_poses'])
p.update(revision='R166D',scope=__doc__,translations=[dict(reference='Q1701',from_mm=[56.75,14.25],delta_mm=[.25,-.25],rotation_deg=90)],routes=[],vias=[],placement_comparison='R166-placement-screen-v2.json')
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
