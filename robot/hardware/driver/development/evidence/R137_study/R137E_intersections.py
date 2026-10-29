import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
p=Planner('robot/.state/c3-completion/trials/R137C/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
plan=json.loads(Path('robot/.state/c3-completion/trials/R137E-plan.json').read_text());rows=[]
for r in plan['routes']:
 for a,b in zip(r['points_mm'],r['points_mm'][1:]):
  l=LineString([a,b]);hits=[]
  for (u,ly),s in c.shapes.items():
   if ly==r['layer'] and c.by_id[u].GetNetname()!=r['net'] and s.buffer(.305).intersects(l):
    hits.append({'id':c.pad_name(c.by_id[u]),'net':c.by_id[u].GetNetname(),'bounds':l.intersection(s.buffer(.305)).bounds,'distance':l.distance(s)})
  for k in c.keepouts:
   if k['tracks'] and r['layer'] in k['layers'] and k['shape'].buffer(.105).intersects(l):hits.append({'keepout':k['name'],'distance':l.distance(k['shape'])})
  for pt,rad in p.holes:
   if pt.distance(l)<rad+.405:hits.append({'hole':pt.coords[:],'distance':pt.distance(l),'radius':rad})
  if hits:rows.append({'layer':r['layer'],'a':a,'b':b,'hits':hits})
Path('robot/.state/c3-completion/trials/R137E-intersections.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
