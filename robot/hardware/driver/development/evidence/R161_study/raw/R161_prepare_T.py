"""Shift C1303 right 0.1 mm to provide an outward, fully referenced ground escape.
Preserve the fixed ground and signal holes and the existing 0.30 mm ground
width. Restore both 3V3 branches at their new common corner without an acute T.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161T-plan.json';assert not out.exists()
p=json.loads((b/'R161S-plan.json').read_text());p['revision']='R161T';p['scope']+='\n'+__doc__
r=next(x for x in p['translations'] if x['reference']=='C1303');r['delta_mm']=[26.0,4.4]
p['routes'][2]['points_mm']=[[66.3375,27.9],[66.825,27.9],[68.225,26.5],[68.9,26.5],[68.9,27.125]]
p['routes'][3]['points_mm']=[[69.15,26.15],[68.9,26.5]]
p['routes'][19]['points_mm']=[[68.9,28.675],[68.3,28.675],[68.3,28.2],[67.875,27.75]]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
