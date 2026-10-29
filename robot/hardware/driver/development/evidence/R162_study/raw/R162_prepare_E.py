"""Place FAULT on permitted In2 to keep In3 available to both UV links.
Uses the C layout, not D's In3 restoration. Rules and source copper remain
unchanged; power-plane continuity must pass native refill regression.
"""
import copy,json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R162E-plan.json';assert not out.exists()
p=json.loads((b/'R162C-plan.json').read_text());p['revision']='R162E';p['scope']+='\n'+__doc__
rows=json.loads((b/'R162C-power-aware-search-in2-fault-v1/searches.json').read_text())['results']
r=next(r for r in rows if r['result']['status']=='PROPOSAL');routes=copy.deepcopy(r['result']['routes'])
routes[0]['points_mm'][0]=[67.45,28.35]
p['routes'] += [{**x,'net':r['net']} for x in routes]
p['vias'] += [{**x,'net':r['net']} for x in r['result']['vias']]
p['unfinished_connections']=p['unfinished_connections'][1:]
p['proposed_restoration_requires_native_verification']='U1301.6 to existing FAULT group through permitted In2'
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
