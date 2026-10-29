"""Preserve a source 0.48 mm MOTION_3V3 In2 corridor during signal search.
This derives an explicit planning obstacle from native filled copper. It does
not change a PCB, create a power trace, or replace the 50 native regressions.
"""
import heapq,json,math,sys
from pathlib import Path
import numpy as np
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import mask,simplify
b=Path('robot/.state/c3-completion/trials');out=b/'R162-power-spine.json';assert not out.exists()
c=Copper(str(b/'R162C/MORI_Interface_C3.kicad_pcb'));g=c.copper[('MOTION_3V3','In2.Cu')].buffer(-.245)
grid=.05;xs=np.arange(50,69.501,grid);ys=np.arange(24,34.501,grid);xx,yy=np.meshgrid(xs,ys)
free=mask(g,xx,yy,True);prepared=prep(g)
start=(int(round((31-24)/grid)),int(round((54.4-50)/grid)))
end=(int(round((26.15-24)/grid)),int(round((69.15-50)/grid)))
point=lambda k:(float(xs[k[1]]),float(ys[k[0]]))
assert free[start] and free[end]
cost={start:0};previous={};q=[(0,0,start)];expanded=0
while q:
 _,v,k=heapq.heappop(q)
 if v!=cost[k]:continue
 if k==end:break
 expanded+=1
 for dy,dx in [(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]:
  n=(k[0]+dy,k[1]+dx)
  if not(0<=n[0]<free.shape[0] and 0<=n[1]<free.shape[1]) or not free[n]:continue
  nv=v+grid*(math.sqrt(2) if dx and dy else 1)
  if nv>=cost.get(n,math.inf):continue
  if not prepared.covers(LineString([point(k),point(n)])):continue
  cost[n]=nv;previous[n]=k;heapq.heappush(q,(nv+math.dist(point(n),point(end)),nv,n))
assert end in cost,'No protected source power corridor found in this bounded region'
path=[end]
while path[-1]!=start:path.append(previous[path[-1]])
points=[[round(x,6),round(y,6)] for x,y in simplify([point(k) for k in reversed(path)])]
spine=LineString(points).buffer(.24)
assert spine.difference(c.copper[('MOTION_3V3','In2.Cu')]).area<1e-6
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'layer':'In2.Cu','net':'MOTION_3V3','preserved_width_mm':.48,'erosion_mm':.245,'grid_mm':grid,'points_mm':points,'length_mm':LineString(points).length,'expanded':expanded,'adopted':False},indent=2)+'\n')
print(json.dumps({'length_mm':LineString(points).length,'points':points,'expanded':expanded}))
