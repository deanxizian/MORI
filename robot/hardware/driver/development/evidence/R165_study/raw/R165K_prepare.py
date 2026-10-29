"""Connect the UV output through the newly freed referenced In3 corridor."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');net='/13 {slash} Head_Fault_Delay/HEAD_UV_N'
p=Planner(str(b/'R165J/MORI_Interface_C3.kicad_pcb'),.05,['In3.Cu'],.2);c=p.c
free,vf,blocked,allowed=p.geometry(net)
s=json.loads((b/'R165J-power-spine.json').read_text());assert s['source_sha256']==c.sha
sp=LineString(s['points_mm']).buffer(.24);obs=blocked[0].union(sp.buffer(p.internal_clearance+.102))
points=[[64.2,29.7],[56.8,29.7],[54.7,31.8],[49.8,31.8],[47.4,29.4],[46.65,29.4],[46.3,29.65]]
line=LineString(points)
check={'source_sha256':c.sha,'points_mm':points,'length_mm':line.length,'obstacle_intersection_mm':line.intersection(obs).length,'outside_reference_mm':line.difference(allowed[0]).length}
with (b/'R165K-route-preflight.json').open('x') as f:json.dump(check,f,indent=2);f.write('\n')
print(check)
assert check['obstacle_intersection_mm']<1e-8 and check['outside_reference_mm']<1e-8
plan=json.loads((b/'R165J-plan.json').read_text());plan['revision']='R165K';plan['scope']=__doc__+' Based on the joint OV/FAULT transfer arrangement. Every original power/ground/reference check remains required; FAULT restoration is still unfinished.'
plan['routes'].append({'net':net,'layer':'In3.Cu','width_mm':.2,'points_mm':points})
with (b/'R165K-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
