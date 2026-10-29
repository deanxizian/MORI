"""Prepare the more constrained current-filter route before rebuilding the OV branch.

Retain C912/C913; use the original ARMED X coordinate to clear the front pad.
The known HEAD_VM width loss must be repaired explicitly, not waived.
The removed OV branch is not counted as complete until it is reconstructed.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R151D-plan.json';assert not out.exists()
p=json.loads((b/'R151B-plan.json').read_text());p.update(revision='R151D',scope=__doc__)
next(v for v in p['move_vias'] if v['uuid']=='b049d7c8-9984-50be-a63c-ab8f19b37c43')['position_mm']=[32.86,16.0]
p['routes'][-2]['points_mm']=[[32.86,14.69],[32.86,16.0]]
p['routes'][-1]['points_mm']=[[32.86,16.0],[31.75,16.0],[31.75,18.2]]
ov='Net-(U1301-INB-_{slash}_OV)'
p['routes']=[r for r in p['routes'] if r['net']!=ov]
p['vias']=[v for v in p['vias'] if v['net']!=ov]
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
