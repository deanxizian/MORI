"""Bring the declared U1501 OV transfer within the existing return-distance screen.
Use the unchanged nearby ground stitch; all original ground holes and mounting
guards stay fixed. The exact new non-ground via and three tails are rechecked.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161R-plan.json';assert not out.exists()
p=json.loads((b/'R161Q-plan.json').read_text());p['revision']='R161R';p['scope']+='\n'+__doc__
pos=[64.45,31.275]
for v in p['move_vias']:
 if v['uuid']=='ed145f08-9ec4-48e7-acaf-aabdac5dea88':v['position_mm']=pos
p['routes'][14]['points_mm'][-1]=pos
p['routes'][15]['points_mm'][0]=pos
p['routes'][16]['points_mm'][-1]=pos
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
