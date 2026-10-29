"""Coordinate ARMED and C912 instead of narrowing HEAD_VM or touching the front GND pad.

C912 moves 0.18 mm toward its converter, with both original input connections
retained. Its actual courtyard remains clear of C913 in the source geometry.
All filled power, ground and reference effects remain subject to native checks.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R151C-plan.json';assert not out.exists()
p=json.loads((b/'R151B-plan.json').read_text());p.update(revision='R151C',scope=__doc__)
p['translations'].append(dict(reference='C912',from_mm=[31.5,17.25],delta_mm=[-.18,0]))
next(v for v in p['move_vias'] if v['uuid']=='b049d7c8-9984-50be-a63c-ab8f19b37c43')['position_mm']=[32.68,15.98]
p['routes'][-2]['points_mm']=[[32.86,14.69],[32.86,15.8],[32.68,15.98]]
p['routes'][-1]['points_mm']=[[32.68,15.98],[31.75,15.98],[31.75,18.2]]
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
