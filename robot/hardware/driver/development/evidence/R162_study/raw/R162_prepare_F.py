"""Counterfactual only: isolate the In2 FAULT tail's power-width effect.
Remove only the vertical (55.9,30.2)-(55.9,33.9) section from E. This deliberately
breaks FAULT and cannot be adopted; it distinguishes the vertical tail from the
remaining horizontal/diagonal path as the source of the MOTION_3V3 narrowing.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R162F-plan.json';assert not out.exists()
p=json.loads((b/'R162E-plan.json').read_text());p['revision']='R162F';p['scope']+='\n'+__doc__
assert p['routes'][-2]['points_mm'][-2:]==[[55.9,30.2],[55.9,33.9]]
p['routes'][-2]['points_mm']=p['routes'][-2]['points_mm'][:-1]
p['control_not_for_adoption']=True
p['unfinished_connections'].insert(0,'FAULT intentionally cut for power-width causal control')
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
