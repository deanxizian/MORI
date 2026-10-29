"""Read-only local layer-transfer diagnosis around the CAM power corridor."""
import json,sys
from pathlib import Path
import numpy as np
from scipy import ndimage
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
p=Planner('robot/.state/c3-completion/trials/R137C/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','F.Cu'],.2)
c=p.c;net='Net-(U1001-D3_{slash}_current_ADC)'
free,vf,blocked,allowed=p.geometry(net)
window=(p.xx>=14)&(p.xx<=19)&(p.yy>=15)&(p.yy<=20)
rows=[]
for i,ly in enumerate(p.layers):
 if ly=='In3.Cu':continue
 vm=vf&free[i]&free[1]&window
 if REFERENCE[ly]!=REFERENCE['In3.Cu']:vm&=p.ground_near
 lab,n=ndimage.label(vm,np.ones((3,3)));regions=[]
 for idx in range(1,n+1):
  yy,xx=np.where(lab==idx);coords=list(zip(p.xs[xx],p.ys[yy]))
  regions.append({'n':len(coords),'bounds':[min(x[0] for x in coords),min(x[1] for x in coords),max(x[0] for x in coords),max(x[1] for x in coords)],'near_top':min(coords,key=lambda x:Point(x).distance(Point(16.4,16.5))),'near_bottom':min(coords,key=lambda x:Point(x).distance(Point(16.4,19)))})
 rows.append({'layer':ly,'regions':regions})
for pos in [(16.4,16.5),(16.4,16.9),(16.4,17.3),(15.5,17.1),(16.4,18.9),(17,18.9),(16.4,19.2),(15.4,18.7),(17.5,18.7)]:
 pt=Point(pos);issues=[]
 for (u,ly),s in c.shapes.items():
  ob=c.by_id[u]
  if isinstance(ob,pcb.PAD):
   if s.distance(pt)<.457:issues.append({'type':'PAD','id':c.pad_name(ob),'layer':ly,'distance':s.distance(pt)})
  elif ob.GetNetname()!=net and s.distance(pt)<.457:issues.append({'type':type(ob).__name__,'id':u,'net':ob.GetNetname(),'layer':ly,'distance':s.distance(pt)})
 for k in c.keepouts:
  if k['vias'] and k['shape'].distance(pt)<.257:issues.append({'type':'KEEPOUT','name':k['name'],'distance':k['shape'].distance(pt)})
 for t in c.segments:
  ly=c.board.GetLayerName(t.GetLayer())
  if t.GetNetname()!='GND' and ly in REFERENCE:
   g=c.shapes[(uid(t),ly)].intersection(p.ground[REFERENCE[ly]])
   if g.distance(pt)<.657:issues.append({'type':'REFERENCE','id':uid(t),'net':t.GetNetname(),'layer':ly,'distance':g.distance(pt)})
 rows.append({'position':pos,'issues':issues})
out=Path('robot/.state/c3-completion/trials/R137C-local-transfer-diagnosis.json');out.write_text(json.dumps({'source_sha256':c.sha,'scope':__doc__,'rows':rows},indent=2)+'\n')
print(json.dumps(rows),flush=True)
