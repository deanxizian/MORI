"""Refine D using actual native keepouts and localized reference-gap geometry.
All six unfinished links remain open and no acceptance is implied.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161E-plan.json';assert not out.exists()
p=json.loads((b/'R161D-plan.json').read_text());p['revision']='R161E';p['scope']+='\n'+__doc__
for row in p['move_vias']:
 if row['uuid']=='7bd5c3f2-f767-42af-b113-c3a4bc91e615':row['position_mm']=[65.0,29.95]
 if row['uuid']=='fcd6ec6b-0145-4092-9c84-0765c014a1fa':row['position_mm']=[64.2,33.1]
 if row['uuid']=='4235992b-10c1-49b9-b6d7-b3df51cada3c':row['position_mm']=[67.7,25.55]
points={
 2:[[66.3375,27.9],[67.1,27.9],[67.1,27.6],[68.2,26.5],[68.8,26.5],[68.8,27.125]],
 5:[[67.7,25.55],[68.1,25.95]],
 10:[[62.9,30.325],[64.2,30.6]],
 13:[[65.75,28.825],[65.3,28.825],[65.0,29.125],[65.0,29.95]],
 14:[[65.0,29.95],[65.0,28.9],[63.4,28.9],[63.4,31.5],[64.2,31.5]],
 15:[[64.2,31.5],[64.2,33.1]],
 17:[[64.2,33.1],[63.75,33.3],[62.4,33.3]],
}
for i,pts in points.items():p['routes'][i]['points_mm']=pts
out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':'R161E','changed_routes':len(points),'unfinished':len(p['unfinished_connections'])}))
