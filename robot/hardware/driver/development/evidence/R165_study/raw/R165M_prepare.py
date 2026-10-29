"""Restore FAULT with verified exact-centre escapes; preserve rejected L preflight."""
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
original=json.loads((b/'R165K-short-fault-search.json').read_text())['result']['routes'][0]['points_mm']
variants=[('centres_with_via_land_join',[[67.45,28.35]]+original+[[54.3,33.9]]),('right_centre_direct',[[67.45,28.35]]+original[1:]+[[54.3,33.9]])]
rows=[]
for name,points in variants:
 line=LineString(points);rows.append({'name':name,'points_mm':points,'length_mm':line.length,'obstacle_intersection_mm':line.intersection(obs).length,'outside_reference_mm':line.difference(allowed[0]).length})
with (b/'R165M-route-preflight.json').open('x') as f:json.dump({'source_sha256':c.sha,'variants':rows},f,indent=2);f.write('\n')
valid=[r for r in rows if r['obstacle_intersection_mm']<1e-8 and r['outside_reference_mm']<1e-8];assert valid
best=min(valid,key=lambda r:(len(r['points_mm']),r['length_mm']));print(best)
plan=json.loads((b/'R165K-plan.json').read_text());plan['revision']='R165M';plan['scope']=__doc__+' All original pad links, power widths, ground identities, native rules and references require full verification. Left terminal lead centreline lies within the existing via land.'
plan['routes'].append({'net':net,'layer':'In3.Cu','width_mm':.2,'points_mm':best['points_mm']})
plan['unfinished_connections']=['See fresh native DRC; original FAULT restoration proposed and requires verification.']
with (b/'R165M-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
