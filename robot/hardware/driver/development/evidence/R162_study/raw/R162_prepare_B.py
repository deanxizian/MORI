"""Use actual rotated D1803 pad bounds and preserve the original ground via.

A failed: the proposed MID hole overlapped the rotated clamp pad and the OV
branch touched the source GND via at (66.5,26.125). Rebuild from canonical
through the explicit plan, never from A's shorted/reassigned saved board.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R162B-plan.json';assert not out.exists()
p=json.loads((b/'R162A-plan.json').read_text());p['revision']='R162B';p['scope']+='\n'+__doc__
next(x for x in p['move_vias'] if x['uuid']=='fe2d0371-b479-48d2-a727-17898dd668f7')['position_mm']=[67.65,25.15]
p['routes'][11]['points_mm']=[[64.2,30.6],[63.4,30.6],[63.4,28.35],[66.65,28.35],[66.65,27.15],[67.65,26.15],[67.65,25.15]]
p['routes'][12]['points_mm']=[[67.65,25.15],[67.65,26.5],[67.95,26.8],[68.4,26.8],[68.9,27.3],[68.9,27.675]]
p['routes'][24]['points_mm']=[[64.8,25.6],[66.3,25.6],[66.6,25.45],[67.05,25.45],[67.1,25.5],[67.1,26.25]]
p['routes'][5]['points_mm']=[[67.1,26.25],[67.45,26.6]]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
