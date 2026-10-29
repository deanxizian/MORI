"""Resolve G courtyard/land clearance and separate OV from the mid-node antipad.
Keep the source fixed ground holes and mount keepout; move only the declared
non-ground transfer and restore all its native layer branches explicitly.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161H-plan.json';assert not out.exists()
p=json.loads((b/'R161G-plan.json').read_text());p['revision']='R161H';p['scope']+='\n'+__doc__
r=next(r for r in p['translations'] if r['reference']=='C1301');r['delta_mm']=[24.225,1.65];r['rotation_deg']=90
for v in p['move_vias']:
 if v['uuid']=='fe2d0371-b479-48d2-a727-17898dd668f7':v['position_mm']=[67.45,28.35]
pts={
 2:[[66.3375,27.9],[66.825,27.9],[66.825,27.7],[68.025,26.5],[68.8,26.5],[68.8,27.125]],
 11:[[64.2,30.6],[63.4,30.6],[63.4,28.35],[67.45,28.35]],
 12:[[67.45,28.35],[67.2,28.1],[67.2,27.0],[67.4,26.8],[68.4,26.8],[68.9,27.3],[68.9,27.675]],
 13:[[68.9,29.325],[68.3,29.175],[66.6,29.175],[66.35,29.025],[65.05,29.025],[65.0,29.95]],
 21:[[64.2,26.1],[64.2,27.875],[64.6,28.275],[65.75,28.275]],
}
for i,v in pts.items():p['routes'][i]['points_mm']=v
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
