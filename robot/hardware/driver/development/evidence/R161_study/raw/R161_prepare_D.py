"""Refine C from measured native keepout polygons and DRC, not inferred radii.
The detector's six unfinished upstream/output/filter links remain incomplete.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161D-plan.json';assert not out.exists()
p=json.loads((b/'R161C-plan.json').read_text());p['revision']='R161D';p['scope']+='\n'+__doc__
for row in p['move_vias']:
 if row['uuid']=='7bd5c3f2-f767-42af-b113-c3a4bc91e615':
  row['position_mm']=[64.95,29.55];row['reason']+=' Native MOUNT_H4 polygon excludes the C position; D uses the left opening and preserves pad/hole spacing.'
for row in p['vias']:row['position_mm'][0]=64.2
pts={
 0:[[64.0625,27.9],[63.5,27.9],[62.95,27.3],[62,27.3]],
 5:[[67.8,25.55],[68.15,25.9]],
 7:[[64.0625,28.85],[63.35,28.85],[63.35,29.35],[64.2,29.85]],
 10:[[62.9,30.325],[63.55,30.325],[64.2,30.6]],
 11:[[64.2,30.6],[63.4,30.6],[63.4,28.5],[67.6,28.5]],
 13:[[65.75,28.825],[64.95,29.55]],
 14:[[64.95,29.55],[64.975,30.65],[64.2,31.5]],
}
for i,row in pts.items():p['routes'][i]['points_mm']=row
p['routes'].append({'net':'GND','layer':'B.Cu','width_mm':.3,'points_mm':[[68.8,28.675],[67.875,27.75]]})
out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':'R161D','changed_routes':len(pts),'ground_return_added':True,'unfinished_connections':len(p['unfinished_connections'])}))
