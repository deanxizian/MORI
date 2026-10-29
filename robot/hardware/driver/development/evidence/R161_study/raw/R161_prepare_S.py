"""Escape C1303 ground outward before turning toward the retained ground stitch.
Remove the measured mounted-face Fab overlap outside the actual rounded land;
native keepouts, the complete-reference gate and original ground vias remain.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161S-plan.json';assert not out.exists()
p=json.loads((b/'R161R-plan.json').read_text());p['revision']='R161S';p['scope']+='\n'+__doc__
p['routes'][19]['points_mm']=[[68.8,28.675],[68.2,28.675],[68.2,28.2],[67.875,27.75]]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
