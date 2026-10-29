import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
from plan_existing_copper import groups
p=Planner('robot/.state/c3-completion/trials/R137D/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','In2.Cu','F.Cu'],.5)
c=p.c;n='/07 {slash} CAM_Protection_Start/CAM_BAT_OUT';free,vf,blocked,allowed=p.geometry(n);gs=groups(c,n)
rows=[]
for pos in [(15.5,17),(15.7,17),(15.5,17.2),(15.4,17),(19.9,15.35),(15.85,17.85),(16.95,17.85),(16.4,16.5)]:
 pt=Point(pos);row={'point':pos,'layers':[]}
 for i,ly in enumerate(p.layers):
  hits=[]
  for (u,l),s in c.shapes.items():
   if l==ly and c.by_id[u].GetNetname()!=n and s.distance(pt)<.455:
    o=c.by_id[u];hits.append({'uuid':u,'net':o.GetNetname(),'kind':type(o).__name__,'id':c.pad_name(o) if isinstance(o,pcb.PAD) else u,'distance':s.distance(pt)})
  row['layers'].append({'layer':ly,'groups':[g['pads'] for g in gs if ly in g['layers'] and g['layers'][ly].intersects(pt)],'blocked':blocked[i].intersects(pt),'allowed':allowed[i].covers(pt),'ground_distance':p.ground[REFERENCE[ly]].distance(pt),'near_ground_boundary':p.ground[REFERENCE[ly]].boundary.distance(pt),'hits':hits})
 rows.append(row)
Path('robot/.state/c3-completion/trials/R137D-cam-transfer-points.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
