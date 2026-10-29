"""Diagnose exact raster endpoint regions; no PCB mutations or routability claim."""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from plan_layered_route import Planner,mask
import numpy as np
from scipy import ndimage
from copper_geometry import *
p=Planner('robot/.state/c3-completion/trials/R136A/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','F.Cu'],.2)
net='/01 {slash} Core/ACT_CURRENT_ADC';free,vf,blocked,allowed=p.geometry(net)
labels=[];count=0
for f in free:
 lab,n=ndimage.label(f,np.ones((3,3)));lab[lab>0]+=count;labels.append(lab);count+=n
parent=list(range(count+1))
def root(k):
 while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
 return k
for i in range(len(p.layers)):
 for j in range(i+1,len(p.layers)):
  vm=vf&free[i]&free[j]
  if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:vm&=p.ground_near
  for u,v in np.unique(np.column_stack((labels[i][vm],labels[j][vm])),axis=0):parent[root(int(u))]=root(int(v))
roots=np.array([root(k) for k in range(count+1)])
rows=[]
for group in p.routing_groups(net):
 endpoint_roots=set()
 for i,ly in enumerate(p.layers):
  if ly in group['layers']:
   m=mask(group['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i]
   endpoint_roots.update(int(x) for x in np.unique(roots[labels[i][m]]) if x)
 row={'pads':group['pads'],'root_ids':sorted(endpoint_roots),'layers':[]}
 for i,ly in enumerate(p.layers):
  m=np.isin(roots[labels[i]],list(endpoint_roots))&free[i]
  ys,xs=np.where(m);pos=[(float(p.xs[x]),float(p.ys[y])) for y,x in zip(ys,xs)]
  bounds=[min(x for x,y in pos),min(y for x,y in pos),max(x for x,y in pos),max(y for x,y in pos)] if pos else None
  row['layers'].append({'layer':ly,'cell_count':int(m.sum()),'approx_area_mm2':float(m.sum())*p.grid*p.grid,'bounds_mm':bounds,'eligible_new_via_cells':int((m&vf).sum())})
 rows.append(row)
out=Path('robot/.state/c3-completion/trials/R136A-mcu-endpoint-regions.json');assert not out.exists();out.write_text(json.dumps({'source_sha256':p.c.sha,'grid_mm':p.grid,'scope':'Diagnostic regions of the constrained finite raster only; not a global feasibility proof.','groups':rows},indent=2)+'\n');print(json.dumps(rows,indent=2),flush=True)
