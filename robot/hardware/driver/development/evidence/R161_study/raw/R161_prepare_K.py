"""Test only the power-aware OV proposal on J; other independent paths omitted.
Snap transfers to native centres and retain the original design-rule set.
Native refill must decide whether the diagnosed power cuts are acceptable.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161K-plan.json';assert not out.exists()
p=json.loads((b/'R161J-plan.json').read_text());p['revision']='R161K';p['scope']+='\n'+__doc__
q=json.loads((b/'R161J-power-aware-search-v2/ov_upstream-plan.json').read_text())
q['routes'][0]['points_mm'][0]=[60.55,17.0]
q['routes'][-1]['points_mm'][-1]=[67.7,25.55]
p['routes'].extend(q['routes']);p['vias'].extend(q['vias'])
p['unfinished_connections']=[x for x in p['unfinished_connections'] if not x.startswith('U1301 OV')]
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
