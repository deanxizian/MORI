"""Keep the R1307 ground bridge outside the native J401 slotted-pad thermal gaps.
Do not waive the complete-reference gate for ground traces; reroute the bridge
to retain its explicit path while respecting the unchanged native plane shape.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161Q-plan.json';assert not out.exists()
p=json.loads((b/'R161P-plan.json').read_text());p['revision']='R161Q';p['scope']+='\n'+__doc__
p['routes'][1]['points_mm']=[[62.2,17.125],[62.2,17.3],[61.5,17.7],[60.325,18.0]]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
