"""Read-only 0.48 mm supply corridors from actual native In2 copper.

These corridors are additional proposal reservations, not an ampacity claim or
a substitute for full native regression. They address observed VM splits.
"""
import heapq,json,math,sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import mask,simplify
b=Path('robot/.state/c3-completion/trials');out=b/'R155-power-spines.json';assert not out.exists()
c=Copper(b/'R155F/MORI_Interface_C3.kicad_pcb')
grid=.05;xs=np.arange(.8,69.201,grid);ys=np.arange(.8,34.201,grid);xx,yy=np.meshgrid(xs,ys)
rows=[]
cases=[('/HEAD_VM',(31.95,21.8),(51.7,25.65)),('/WHEEL_VM',(47.8,18),(44.5,22.55)),('/WHEEL_VM',(47.8,18),(49.75,24.25)),('/09 {slash} Head_Buck/HEAD_BUCK_IN',(31.15,20.25),(45.48,29.1))]
for net,start,end in cases:
 g=c.copper[(net,'In2.Cu')].buffer(-.24);pg=prep(g);free=mask(g,xx,yy,True)
 ix=lambda pt:(int(round((pt[1]-.8)/grid)),int(round((pt[0]-.8)/grid)))
 pt=lambda key:(round(float(xs[key[1]]),6),round(float(ys[key[0]]),6))
 a,z=ix(start),ix(end);row={'net':net,'start_mm':start,'end_mm':end,'width_mm':.48}
 if not free[a] or not free[z]:row['status']='ENDPOINT_NOT_ON_GRID_ERODED_COPPER';rows.append(row);continue
 lab,n=ndimage.label(free,np.ones((3,3)))
 if lab[a]!=lab[z]:row['status']='NO_SINGLE_LAYER_ERODED_PATH';rows.append(row);continue
 queue=[(math.dist(start,end),0.,a)];cost={a:0.};prev={};found=False;expanded=0
 while queue:
  _,dist,u=heapq.heappop(queue)
  if cost[u]!=dist:continue
  if u==z:found=True;break
  expanded+=1
  for dy,dx in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
   v=(u[0]+dy,u[1]+dx)
   if not(0<=v[0]<free.shape[0] and 0<=v[1]<free.shape[1]) or not free[v]:continue
   nd=dist+grid*math.hypot(dy,dx)
   if nd>=cost.get(v,math.inf) or not pg.covers(LineString([pt(u),pt(v)])):continue
   cost[v]=nd;prev[v]=u;heapq.heappush(queue,(nd+math.dist(pt(v),end),nd,v))
 if found:
  rev=[z]
  while rev[-1]!=a:rev.append(prev[rev[-1]])
  points=simplify([pt(u) for u in reversed(rev)])
  row.update(status='RESERVED_PROPOSAL_CORRIDOR',points_mm=points,length_mm=LineString(points).length,expanded=expanded)
 else:row.update(status='NO_CONTINUOUS_ERODED_PATH',expanded=expanded)
 rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='points_mm'}),flush=True)
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'layer':'In2.Cu','rows':rows,'adopted':False},indent=2)+'\n')
