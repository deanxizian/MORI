"""Keep the J401 ground thermal unobstructed by taking OV down the existing In2 rail.
Use K's lower exit, omit its F-face slit and the now-redundant new transfer.
Exact In2 allow-list and all power/ground/reference checks remain unchanged.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161L-plan.json';assert not out.exists()
p=json.loads((b/'R161K-plan.json').read_text());p['revision']='R161L';p['scope']+='\n'+__doc__
assert p['routes'][22]['layer']=='F.Cu'
p['routes'][22]={'net':p['routes'][22]['net'],'layer':'In2.Cu','width_mm':.2,'points_mm':[[60.9,19.35],[60.9,22.9],[61.0,23.0]]}
p['vias']=[v for v in p['vias'] if v['position_mm']!=[61.0,23.0]]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
