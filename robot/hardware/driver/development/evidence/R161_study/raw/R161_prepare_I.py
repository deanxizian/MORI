"""Use one 45-degree VDD escape and preserve native land/via clearances.
H already retained all power/reference checks; two measured local conflicts
are corrected here without relaxing any native rule or altering ground vias.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161I-plan.json';assert not out.exists()
p=json.loads((b/'R161H-plan.json').read_text());p['revision']='R161I';p['scope']+='\n'+__doc__
r=next(r for r in p['translations'] if r['reference']=='C1301');r['delta_mm']=[24.125,1.65]
p['routes'][2]['points_mm']=[[66.3375,27.9],[66.825,27.9],[68.225,26.5],[68.8,26.5],[68.8,27.125]]
p['routes'][21]['points_mm'][-1]=[65.65,28.275]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
