"""Keep the OV branch outside the MID transfer's actual reference-plane void.
Preserve outward FAULT escape and all native widths/clearances/ground holes.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R162C-plan.json';assert not out.exists()
p=json.loads((b/'R162B-plan.json').read_text());p['revision']='R162C';p['scope']+='\n'+__doc__
p['routes'][24]['points_mm']=[[64.8,25.6],[65.0,25.4],[66.75,25.4],[67.15,25.8],[67.15,26.3]]
p['routes'][5]['points_mm']=[[67.15,26.3],[67.45,26.6]]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
