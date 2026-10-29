"""Read-only diagnosis of the FAULT escape reachable from Q1701.3.

Use the same full native/reference/body graph as route search. Report actual
reachable regions and obstacles to through-via placement, not a global
impossibility claim. No routing rule or source geometry is changed.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-fault-endpoint-diagnostics.json');assert not out.exists()
p=Planner(b/rev/'MORI_Interface_C3.kicad_pcb',.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2);c=p.c;net='/FAULT_N'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
free,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 if ly not in ['B.Cu','F.Cu']:continue
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
 lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked[i]=blocked[i].union(bodies.buffer(.102).difference(lands.buffer(-.001)))
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
labels=[];count=0
for f in free:
 lab,n=ndimage.label(f,np.ones((3,3)));lab[lab>0]+=count;labels.append(lab);count+=n
parent=list(range(count+1))
def root(k):
 while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
 return k
for i in range(len(p.layers)):
 for j in range(i+1,len(p.layers)):
  vm=vf & free[i] & free[j]
  if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:vm &= p.ground_near
  for a,z in np.unique(np.column_stack((labels[i][vm],labels[j][vm])),axis=0):parent[root(int(a))]=root(int(z))
pad=next(a for a in c.pads if c.pad_name(a)=='Q1701.3');starts=mask(c.shapes[uid(pad),'B.Cu'].buffer(-.001),p.xx,p.yy,True)&free[0]
roots={root(int(k)) for k in np.unique(labels[0][starts])};reached=[];summaries=[]
for i,ly in enumerate(p.layers):
 ids=[n for n in np.unique(labels[i]) if n and root(int(n)) in roots]
 region=np.isin(labels[i],ids);reached.append(region);ys,xs=np.where(region)
 summaries.append(dict(layer=ly,raster_points=len(xs),area_mm2=len(xs)*p.grid**2,bounds_mm=[float(p.xs[xs.min()]),float(p.ys[ys.min()]),float(p.xs[xs.max()]),float(p.ys[ys.max()])] if len(xs) else None,via_free_points=int(np.sum(region&vf))))
ys,xs=np.where(reached[0]);xx=p.xx[ys,xs];yy=p.yy[ys,xs];blockers=[]
for (u,ly),s in c.shapes.items():
 obj=c.by_id[u]
 if not isinstance(obj,pcb.PAD):continue
 n=int(mask(s.buffer(.457),xx,yy).sum())
 if n:blockers.append(dict(kind='physical_via_to_pad',pad=c.pad_name(obj),net=obj.GetNetname(),layer=ly,blocked_reachable_B_points=n))
for k in c.keepouts:
 if k['vias']:
  n=int(mask(k['shape'].buffer(.257),xx,yy).sum())
  if n:blockers.append(dict(kind='native_via_keepout',name=k.get('name',k.get('uuid')),layers=k['layers'],blocked_reachable_B_points=n))
blockers.sort(key=lambda x:x['blocked_reachable_B_points'],reverse=True)
result=dict(scope=__doc__,source_sha256=c.sha,revision=rev,endpoint='Q1701.3',position_mm=list(xy(pad.GetPosition())),grid_mm=p.grid,start_points=int(starts.sum()),reachable_layers=summaries,reference_guard_blocked_B_points=int(mask(p.reference_guard,xx,yy).sum()),through_via_obstacles=blockers,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(revision=rev,reachable=summaries,top_obstacles=blockers[:8],reference_guard_B_points=result['reference_guard_blocked_B_points'])),flush=True)
