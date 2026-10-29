"""Joint fine adjustment of U1702 and all three local signal ports.

E's left FAULT port conflicts with the shifted U1702 guard. F keeps Q1701,
C1702 and the original right 3V3 transfer, and explicitly coordinates U1702
(57.85,15.25)/90, the original left/right ACT transfers and the new FAULT
port. The INA+ diagonal is centered between the actual ACT/WHEEL reference
voids; all tolerances and filled-board checks remain unchanged.
No adopted result is claimed by this trial plan.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R168F-plan.json';assert not out.exists()
p=json.loads((b/'R168E-plan.json').read_text())
next(t for t in p['translations'] if t['reference']=='U1702')['delta_mm']=[.35,-.5]
next(m for m in p['move_vias'] if m['uuid']=='4312a4e0-e664-44e0-a44a-716dd81b836a')['position_mm']=[59.55,14.575]
next(m for m in p['move_vias'] if m['uuid']=='74c0d925-81e9-4f8b-8224-202391f21e26')['position_mm']=[55.675,15.425]
port=[56.175,14.9];p['vias'][0]['position_mm']=port
p['routes'][1]['points_mm']=[[56.9,16.3875],[56.6375,16.3875],[55.675,15.425]]
p['routes'][3]['points_mm']=[[58.775,14.775],[59.35,14.775],[59.55,14.575]]
p['routes'][4]['points_mm']=[[55.675,15.425],[55.675,15.65],[56.025,16],[57.7,16],[58.3,15.4],[58.775,15.4]]
p['routes'][5]['points_mm']=[[59.925,12.575],[59.925,13.825],[60.3,14.2],[60.3,14.925],[58.8375,16.3875],[58.8,16.3875]]
p['routes'][6]['points_mm']=[[57.85,14.1125],[57.85,13.35],[57.6,13.1],[56.3,13.1],[55.6,13.8],[55.4,13.8]]
p['routes'][8]['points_mm']=[[57.85,16.3875],[57.85,17.825],[57.475,18.2]]
p['routes'][9]['points_mm']=[[57.125,14.9375],port]
p['routes'][10]['points_mm']=[[59.55,14.575],[60.575,14.575],[61.5,15.5]]
p.update(revision='R168F',scope=__doc__,adoption_prohibited=True)
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
