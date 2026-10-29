"""Leave the lower J401 ground-spoke outlet open and clear the measured PTH reference void.
The F-side OV rail stays farther left through the ground-pad channel; its In2
diagonal moves 0.05 mm around the existing plated-hole reference boundary.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161N-plan.json';assert not out.exists()
p=json.loads((b/'R161M-plan.json').read_text());p['revision']='R161N';p['scope']+='\n'+__doc__
p['routes'][22]['points_mm']=[[60.55,17],[59.65,17],[59.65,17.325],[59.4,17.3],[58.875,17.725],[58.8,18.2],[58.8,18.8],[59.075,19.075],[60.3,19.075],[60.5,19.275],[60.5,20.15],[60.9,20.55],[60.9,22.9],[61,23]]
p['routes'][23]['points_mm']=[[61.0,23.0],[61.35,23.0],[62.85,24.5],[63.7,24.5],[64.8,25.6]]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
