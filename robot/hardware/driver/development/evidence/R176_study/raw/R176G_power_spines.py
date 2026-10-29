"""Read-only 0.48 mm supply corridor reservations from refilled R176G.

Reservations constrain subsequent route proposals. They do not change native
rules, demonstrate current capacity, or replace native refill and all 50 width
checks. R176G is an unadopted placement reference, not the accepted PCB.
"""
import hashlib, heapq, json, math, sys, time
from pathlib import Path
import numpy as np
from shapely.prepared import prep
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import mask, simplify

b=Path('robot/.state/c3-completion/trials')
out=b/'R176G-power-spines.json'
assert not out.exists()
c=Copper(str(b/'R176G/MORI_Interface_C3.kicad_pcb'))
requests=[
 ('ups_central','/UPS_BAT','In2.Cu',(45.29,10.05),(51.35,6.2),(44,2,64,14)),
 ('ups_right','/UPS_BAT','In2.Cu',(51.35,6.2),(59.9,10.35),(49,4,62,15)),
 ('3v3_upper','MOTION_3V3','In3.Cu',(47.15,10.55),(46.3,11.85),(43,7,54,18)),
 ('3v3_lower','MOTION_3V3','In3.Cu',(46.3,11.85),(47.775,14.1),(43,7,54,18)),
]
rows=[]
for name,net,layer,a,z,bounds in requests:
 started=time.monotonic(); grid=.01; width=.48
 native=c.copper[(net,layer)]; g=native.buffer(-width/2)
 xs=np.arange(bounds[0],bounds[2]+grid/2,grid)
 ys=np.arange(bounds[1],bounds[3]+grid/2,grid)
 xx,yy=np.meshgrid(xs,ys); free=mask(g,xx,yy,True)
 terminals=[]; terminal_uuids=[]
 for coord in (a,z):
  candidates=[v for v in c.vias if v.GetNetname()==net and math.dist(xy(v.GetPosition()),coord)<1e-7]
  assert len(candidates)==1,(name,coord,len(candidates))
  terminal_uuids.append(uid(candidates[0]))
  land=c.shapes[uid(candidates[0]),layer]
  terminals.append(set(zip(*np.where(free & mask(land,xx,yy,True)))))
 row=dict(name=name,net=net,layer=layer,preserved_width_mm=width,
          erosion_mm=width/2,grid_mm=grid,bounds_mm=bounds,
          terminal_via_uuids=terminal_uuids,terminal_centres_mm=[a,z],
          terminal_grid_counts=[len(s) for s in terminals],adopted=False)
 if not all(terminals):
  row.update(status='NO_GRID_TERMINAL'); rows.append(row)
  print(json.dumps({k:v for k,v in row.items() if k!='points_mm'}),flush=True); continue
 point=lambda k:(float(xs[k[1]]),float(ys[k[0]]))
 prepared=prep(g); cost={k:0 for k in terminals[0]}; previous={}
 q=[(max(0,math.dist(point(k),z)-.26),0,k) for k in terminals[0]]
 heapq.heapify(q); end=None; expanded=0
 while q:
  _,v,k=heapq.heappop(q)
  if v!=cost[k]:continue
  if k in terminals[1]:end=k;break
  expanded+=1
  for dy,dx in [(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]:
   n=(k[0]+dy,k[1]+dx)
   if not(0<=n[0]<free.shape[0] and 0<=n[1]<free.shape[1]) or not free[n]:continue
   nv=v+grid*(math.sqrt(2) if dx and dy else 1)
   if nv>=cost.get(n,math.inf):continue
   if not prepared.covers(LineString([point(k),point(n)])):continue
   cost[n]=nv;previous[n]=k
   heapq.heappush(q,(nv+max(0,math.dist(point(n),z)-.26),nv,n))
 if end is None:
  row.update(status='NO_BOUNDED_GRID_PATH',expanded=expanded)
 else:
  path=[end]
  while path[-1] not in terminals[0]:path.append(previous[path[-1]])
  points=[[round(x,6),round(y,6)] for x,y in simplify([point(k) for k in reversed(path)])]
  spine=LineString(points).buffer(width/2)
  outside=spine.difference(native).area
  assert outside<1e-7,(name,outside)
  row.update(status='RESERVATION',points_mm=points,length_mm=LineString(points).length,
             outside_native_copper_mm2=outside,expanded=expanded)
 row['elapsed_seconds']=time.monotonic()-started; rows.append(row)
 out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,results=rows),indent=2)+'\n')
 print(json.dumps({k:v for k,v in row.items() if k!='points_mm'}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
