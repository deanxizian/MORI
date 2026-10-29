"""Apply only the FAULT restoration proposal, with an exact via-centre start.
The UV proposals are intentionally not combined; their mutual compatibility
and power-plane effects are unproven. Native refill is required for this trial.
"""
import copy,json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R162D-plan.json';assert not out.exists()
p=json.loads((b/'R162C-plan.json').read_text());p['revision']='R162D';p['scope']+='\n'+__doc__
rows=json.loads((b/'R162C-power-aware-search-restore-v1/searches.json').read_text())['results']
r=next(r for r in rows if r['request']=='fault_restore' and r['result']['status']=='PROPOSAL')
routes=copy.deepcopy(r['result']['routes']);routes[0]['points_mm'][0]=[67.45,28.35]
p['routes'] += [{**x,'net':r['net']} for x in routes]
p['vias'] += [{**x,'net':r['net']} for x in r['result']['vias']]
p['unfinished_connections']=p['unfinished_connections'][1:]
p['proposed_restoration_requires_native_verification']='U1301.6 to existing FAULT group'
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
