"""Joint MID transfer/branch change to open an outward U1301 FAULT escape.

Independent continuation of R161T. The source canonical, both clamps, every
ground via and all native design rules stay unchanged. This is a diagnostic
candidate, not an adopted or manufacturable board; all four old links remain
unfinished until their actual circuit groups are joined and verified.
"""
import json
from pathlib import Path

b=Path('robot/.state/c3-completion/trials')
out=b/'R162A-plan.json'
assert not out.exists()
p=json.loads((b/'R161T-plan.json').read_text())
p['revision']='R162A'
p['scope']+='\n'+__doc__
m=next(x for x in p['move_vias'] if x['uuid']=='fe2d0371-b479-48d2-a727-17898dd668f7')
m['position_mm']=[67.1,25.1]
m['reason']=__doc__
p['routes'][11]['points_mm']=[[64.2,30.6],[63.4,30.6],[63.4,28.35],[66.7,28.35],[66.7,27.3],[67.1,26.9],[67.1,25.1]]
p['routes'][12]['points_mm']=[[67.1,25.1],[67.1,26.5],[67.4,26.8],[68.4,26.8],[68.9,27.3],[68.9,27.675]]
p['routes'][24]['points_mm']=[[64.8,25.6],[65.1,25.9],[67.6,25.9]]
p['routes'][5]['points_mm']=[[67.6,25.9],[67.85,26.2]]
p['vias'].append({'net':'/FAULT_N','position_mm':[67.45,28.35],'diameter_mm':.5,'drill_mm':.3})
p['routes'].append({'net':'/FAULT_N','layer':'B.Cu','width_mm':.2,'points_mm':[[66.3375,28.85],[67.0,28.85],[67.45,28.35]]})
out.write_text(json.dumps(p,indent=2)+'\n')
print(p['revision'])
