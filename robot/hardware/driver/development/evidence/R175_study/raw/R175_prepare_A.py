"""Rebuild the full placement with supply-reserved IN- and explicit ground.

Uses R168G as the actual build source. Unchanged tested local paths come from
unadopted R174D; replace its two causal supply failures with R175 proposals.
All generated geometry still requires native refill, DRC and regression.
"""
import copy,json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
out=b/'R175A-plan.json';assert not out.exists()
p=json.loads((b/'R174D-plan.json').read_text())
s=json.loads((b/'R174B-R175-guarded-loops/searches.json').read_text())
byname={r['name']:r for r in s['results']}
minus=byname['ina_input_minus'];ground=byname['rlimit_direct_gnd']
assert minus['result']['status']==ground['result']['status']=='PROPOSAL'
assert p['routes'][2]['net']==p['routes'][3]['net']==minus['net']
p['routes'][2:4]=[dict(r,net=minus['net']) for r in minus['result']['routes']]
p['vias']=[dict(v,net=minus['net']) for v in minus['result']['vias']]
route=next(copy.deepcopy(r) for r in ground['result']['routes'] if r['layer']=='In3.Cu')
assert route['points_mm'][0]==[50.5,10.875]
route['points_mm'][0]=[50.5,10.87]
assert p['routes'][6]['net']=='GND' and p['routes'][6]['layer']=='In3.Cu'
p['routes'][6]=dict(route,net='GND')
p.update(revision='R175A',scope=__doc__)
out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps(dict(revision=p['revision'],routes=len(p['routes']),vias=p['vias'])))
