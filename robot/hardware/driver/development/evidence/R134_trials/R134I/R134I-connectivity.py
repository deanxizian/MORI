import sys,json,numpy as np
from scipy import ndimage
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from plan_layered_route import Planner,mask
from copper_geometry import REFERENCE
p=Planner('robot/.state/c3-completion/trials/R134I/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','F.Cu'],.2);net='Net-(U401-2Y)';free,via,blocked,allowed=p.geometry(net)
labels=[];count=0
for f in free:
 l,n=ndimage.label(f,np.ones((3,3)));l[l>0]+=count;count+=n;labels.append(l)
parent=list(range(count+1))
def root(k):
 while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
 return k
def join(a,b):parent[root(int(a))]=root(int(b))
for i in range(len(p.layers)):
 for j in range(i+1,len(p.layers)):
  vm=via&free[i]&free[j]
  if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:vm &= p.ground_near
  for a,b in np.unique(np.column_stack([labels[i][vm],labels[j][vm]]),axis=0):join(a,b)
roots=[np.asarray([root(k) if k else 0 for k in range(count+1)])[l] for l in labels];rows=[];reachable=[]
for g in p.routing_groups(net):
 rr=set()
 for i,ly in enumerate(p.layers):
  if ly in g['layers']:rr.update(int(k) for k in np.unique(roots[i][mask(g['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i]]))
 masks=[np.isin(r,list(rr))&f for r,f in zip(roots,free)];reachable.append(masks);row={'pads':g['pads'],'roots':sorted(rr),'layers':[]}
 for i,m in enumerate(masks):
  ys,xs=np.where(m);row['layers'].append({'layer':p.layers[i],'regions':np.unique(labels[i][m]).tolist(),'cells':int(m.sum()),'bounds':None if len(xs)==0 else [float(p.xs[xs.min()]),float(p.ys[ys.min()]),float(p.xs[xs.max()]),float(p.ys[ys.max()])]})
 rows.append(row)
closest=[]
for i,ly in enumerate(p.layers):
 a,b=reachable[0][i],reachable[1][i]
 if not a.any() or not b.any():continue
 dist,nearest=ndimage.distance_transform_edt(~a,return_indices=True);dy,dx=np.unravel_index(np.where(b,dist,np.inf).argmin(),b.shape);sy,sx=nearest[:,dy,dx];closest.append({'layer':ly,'gap_mm':float(dist[dy,dx]*p.grid),'source_xy':[float(p.xs[sx]),float(p.ys[sy])],'target_xy':[float(p.xs[dx]),float(p.ys[dy])]})
report={'groups':rows,'closest_same_layer':closest};Path('robot/.state/c3-completion/trials/R134I-connectivity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
