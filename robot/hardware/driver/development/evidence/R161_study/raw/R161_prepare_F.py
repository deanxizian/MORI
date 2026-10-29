"""Combine four E geometry proposals in an independent trial.
Endpoints are snapped to native pad/via/track centres. Joint refill and native
DRC remain authoritative; raster proposals alone are not accepted connections.
"""
import copy,json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
out=b/'R161F-plan.json';assert not out.exists()
p=json.loads((b/'R161E-plan.json').read_text())
p['revision']='R161F';p['scope']+='\n'+__doc__
rows=json.loads((b/'R161E-restore-search/searches.json').read_text())['results']
for row in rows:
 if row['status']!='PROPOSAL':continue
 routes=copy.deepcopy(row['routes']);vias=copy.deepcopy(row['vias'])
 if row['request']=='uv_divider':
  routes[0]['points_mm'][0]=[56.65,34.1375]
  routes[0]['points_mm'][-1]=[62.75,25.25]
 if row['request']=='ov_upstream':
  routes[0]['points_mm'][0]=[60.9,19.35]
  routes[0]['points_mm'][-1]=[67.7,25.55]
 if row['request']=='fault_restore':
  routes[0]['points_mm']=[[66.3375,28.85],[66.95,28.85],[67.4,29.3],[67.8,29.3],[67.9,29.2]]
 if row['request']=='uv_output':
  routes[0]['points_mm'][0]=[64.2,29.85]
  routes[-1]['points_mm'][-1]=[44.6,28.8]
 for r in routes:r['net']=row['net'];p['routes'].append(r)
 for v in vias:v['net']=row['net'];p['vias'].append(v)
p['unfinished_connections']=[p['unfinished_connections'][2],p['unfinished_connections'][5]]
p['proposed_restorations_requiring_native_verification']=[r['request'] for r in rows if r['status']=='PROPOSAL']
out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':p['revision'],'routes':len(p['routes']),'vias':len(p['vias'])}))
