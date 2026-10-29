"""Diagnose actual lower UV path barriers without changing native rules."""
import json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import nearest_points
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R165I-corridor-diagnostic.json';assert not out.exists()
p=Planner(str(b/'R165I/MORI_Interface_C3.kicad_pcb'),.05,['In3.Cu'],.2);c=p.c;net='/13 {slash} Head_Fault_Delay/HEAD_UV_N'
free,vf,blocked,allowed=p.geometry(net);window=box(44,28.4,64.6,34.2)
s=json.loads((b/'R165I-power-spine.json').read_text());sp=LineString(s['points_mm']).buffer(.24)
original=allowed[0].difference(blocked[0]).intersection(window)
restricted=original.difference(sp.buffer(p.internal_clearance+.102))
polys=sorted(parts(restricted),key=lambda x:x.area,reverse=True)
rows={'source_sha256':c.sha,'regions':[{'area':g.area,'bounds':g.bounds} for g in polys],'close_parts':[]}
for ia,a in enumerate(polys):
 for iz,z in enumerate(polys[ia+1:],ia+1):
  if a.area<.01 or z.area<.01:continue
  x,y=nearest_points(a,z);rows['close_parts'].append({'indices':[ia,iz],'distance':x.distance(y),'points':[list(x.coords)[0],list(y.coords)[0]]})
rows['nearby_vias']=[]
for v in c.vias:
 x,y=xy(v.GetPosition())
 if 52.5<x<56 and 29<y<34.5:
  rows['nearby_vias'].append({'uuid':uid(v),'net':v.GetNetname(),'position':[x,y],'tracks':[{'uuid':uid(t),'layer':c.board.GetLayerName(t.GetLayer()),'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'width':t.GetWidth()/1e6} for t in c.segments if t.GetNetname()==v.GetNetname() and (Point(xy(t.GetStart())).distance(Point(x,y))<.3 or Point(xy(t.GetEnd())).distance(Point(x,y))<.3)]})
# Independent shortest proposed UV route to expose the precise power repair need.
gs=p.routing_groups(net);a=next(g for g in gs if 'U1301.1' in g['pads']);z=next(g for g in gs if 'Q1301.2' in g['pads'])
allowed[0]=allowed[0].intersection(window)
free=np.array([~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)])
rows['without_power_reservation_proposal']=p.solve(a,z,(free,np.zeros(vf.shape,dtype=bool),blocked,allowed),600000)
with out.open('x') as f:json.dump(rows,f,indent=2);f.write('\n')
print(json.dumps(rows,ensure_ascii=False))
