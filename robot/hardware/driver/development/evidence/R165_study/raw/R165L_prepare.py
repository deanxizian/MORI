"""Restore the existing FAULT connection through the jointly opened lower corridor."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');net='/FAULT_N'
p=Planner(str(b/'R165K/MORI_Interface_C3.kicad_pcb'),.05,['In3.Cu'],.2);c=p.c
free,vf,blocked,allowed=p.geometry(net)
s=json.loads((b/'R165K-power-spine.json').read_text());assert s['source_sha256']==c.sha
sp=LineString(s['points_mm']).buffer(.24);obs=blocked[0].union(sp.buffer(p.internal_clearance+.102))
points=[[67.45,28.35],[66.25,29.55],[66.25,30.55],[64.05,32.75],[55.2,32.75],[54.7,32.25],[54.1,32.25],[53.6,32.75],[53.6,33.45],[54.3,33.9]]
line=LineString(points)
check={'source_sha256':c.sha,'points_mm':points,'length_mm':line.length,'obstacle_intersection_mm':line.intersection(obs).length,'outside_reference_mm':line.difference(allowed[0]).length}
with (b/'R165L-route-preflight.json').open('x') as f:json.dump(check,f,indent=2);f.write('\n')
print(check)
assert check['obstacle_intersection_mm']<1e-8 and check['outside_reference_mm']<1e-8
plan=json.loads((b/'R165K-plan.json').read_text());plan['revision']='R165L';plan['scope']=__doc__+' Every canonical original pad link, power width, ground identity, reference and native DRC gate must pass before considering adoption.'
plan['routes'].append({'net':net,'layer':'In3.Cu','width_mm':.2,'points_mm':points})
plan['unfinished_connections']=['all remaining canonical connections except the connected OV divider group; see fresh native DRC']
with (b/'R165L-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
