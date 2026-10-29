"""Clear the remaining exact native reference sliver without changing its threshold."""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161P-plan.json';assert not out.exists()
p=json.loads((b/'R161O-plan.json').read_text());p['revision']='R161P';p['scope']+='\n'+__doc__
p['routes'][23]['points_mm']=[[61.0,23.0],[61.23,23.0],[62.68,24.45],[63.65,24.45],[64.8,25.6]]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
