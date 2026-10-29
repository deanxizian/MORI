"""Read-only diagnosis: rank existing signal-track barriers, never a valid route.

Native pads, vias, holes, keepouts, power copper and strict reference coverage
remain hard obstacles. Thin existing signal tracks can be crossed with a large
search cost ONLY to identify objects that would require separate redesign.
No board is saved and no design constraint is waived for adoption.
"""
import heapq,json,math,sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask,simplify

base=Path('robot/.state/c3-completion/trials')
out=base/'R137D-cam-soft-obstacle'
out.mkdir(exist_ok=False)
p=Planner(str(base/'R137D/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','In2.Cu','F.Cu'],.5)
c=p.c
power={'GND','MOTION_3V3','CAM_3V3_REF','/UPS_BAT','/WHEEL_VM','/HEAD_VM','/HEAD_6V_RAW','/ACT_BAT_SWITCHED',
 '/01 {slash} Core/MOTION_5V','/06 {slash} CAM_Buck/UPS_5V','/06 {slash} CAM_Buck/CAM_REG_3V87',
 '/07 {slash} CAM_Protection_Start/CAM_BAT_OUT','/09 {slash} Head_Buck/HEAD_BUCK_IN',
 '/16 {slash} Actuator_Direct_Switch/ACT_FET_SOURCE','Net-(U701-SW)','Net-(U901-SW)','Net-(Q1401-D)'}
soft={uid(t):t for t in c.segments if t.GetWidth()/1e6<=.201 and t.GetNetname() not in power}
rows=[]
for net in ['/07 {slash} CAM_Protection_Start/CAM_BAT_OUT']:
 oldfree,vf,oldblocked,allowed=p.geometry(net)
 hard,free,penalty=[],[],[]
 for i,ly in enumerate(p.layers):
  obs=[s.buffer(.205+p.width/2) for (u,l),s in c.shapes.items() if l==ly and c.by_id[u].GetNetname()!=net and u not in soft]
  obs += [k['shape'].buffer(p.width/2+.005) for k in c.keepouts if ly in k['layers'] and k['tracks']]
  obs += [point.buffer(rad+.305+p.width/2) for point,rad in p.holes if not any(point.distance(Point(xy(a.GetPosition())))<1e-7 for a in c.anchors(net))]
  ob=unary_union(obs);hard.append(ob)
  free.append(~mask(ob,p.xx,p.yy)&mask(allowed[i],p.xx,p.yy,True))
  sm=unary_union([c.shapes[(u,ly)].buffer(.205+p.width/2) for u,t in soft.items() if c.board.GetLayerName(t.GetLayer())==ly and t.GetNetname()!=net])
  penalty.append(mask(sm,p.xx,p.yy))
 free=np.array(free);penalty=np.array(penalty)
 gs=p.routing_groups(net);assert len(gs)==2
 starts=[];targets=np.zeros(free.shape,dtype=bool)
 for i,ly in enumerate(p.layers):
  if ly in gs[0]['layers']:
   starts.extend((i,int(y),int(x)) for y,x in zip(*np.where(mask(gs[0]['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i])))
  if ly in gs[1]['layers']:
   targets[i]=mask(gs[1]['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i]
 print(json.dumps({'net':net,'starts':len(starts),'targets':int(targets.sum()),'phase':'search'}),flush=True)
 via={}
 for i in range(len(p.layers)):
  for j in range(i+1,len(p.layers)):
   vm=vf&free[i]&free[j]
   if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:vm&=p.ground_near
   via[i,j]=vm;via[j,i]=vm
 hd=ndimage.distance_transform_edt(~targets.any(axis=0))*p.grid
 costs={k:0. for k in starts};prev={};queue=[];seq=0
 for k in starts:heapq.heappush(queue,(hd[k[1:]],seq,0.,k));seq+=1
 found=None;expanded=0
 dirs=[(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]
 hp=[prep(x) for x in hard];ap=[prep(x) for x in allowed]
 while queue and expanded<900000:
  _,_,co,k=heapq.heappop(queue)
  if co!=costs[k]:continue
  if targets[k]:found=k;break
  expanded+=1;l,y,x=k
  for dy,dx in dirs:
   ny,nx=y+dy,x+dx
   if not(0<=ny<free.shape[1] and 0<=nx<free.shape[2] and free[l,ny,nx]):continue
   nk=(l,ny,nx);dist=p.grid*(math.sqrt(2) if dy and dx else 1)
   nc=co+dist*(1+100*max(int(penalty[k]),int(penalty[nk])))
   if nc>=costs.get(nk,math.inf):continue
   line=LineString([p.point(k),p.point(nk)])
   if hp[l].intersects(line) or not ap[l].covers(line):continue
   costs[nk]=nc;prev[nk]=k;heapq.heappush(queue,(nc+hd[ny,nx],seq,nc,nk));seq+=1
  for j in range(len(p.layers)):
   if j==l or not via[l,j][y,x]:continue
   nk=(j,y,x);nc=co+8
   if nc<costs.get(nk,math.inf):
    costs[nk]=nc;prev[nk]=k;heapq.heappush(queue,(nc+hd[y,x],seq,nc,nk));seq+=1
 row={'net':net,'source_sha256':c.sha,'scope':__doc__,'expanded':expanded,'status':'NO_DIAGNOSTIC_PATH' if found is None else 'INVALID_SOFT_OBSTACLE_PATH'}
 if found is not None:
  keys=[found]
  while keys[-1] in prev:keys.append(prev[keys[-1]])
  keys.reverse();routes=[];vias=[];cur=[p.point(keys[0])];layer=keys[0][0]
  for k in keys[1:]:
   if k[0]!=layer:
    if len(cur)>1:routes.append({'layer':p.layers[layer],'points_mm':simplify(cur)})
    vias.append(p.point(k));cur=[p.point(k)];layer=k[0]
   else:cur.append(p.point(k))
  if len(cur)>1:routes.append({'layer':p.layers[layer],'points_mm':simplify(cur)})
  hits=[]
  for u,t in soft.items():
   ly=c.board.GetLayerName(t.GetLayer())
   if t.GetNetname()==net:continue
   collisions=[]
   for r in routes:
    if r['layer']!=ly:continue
    gap=LineString(r['points_mm']).intersection(c.shapes[(u,ly)].buffer(.205+p.width/2))
    if not gap.is_empty:collisions.append({'bounds_mm':gap.bounds,'length_mm':gap.length})
   if collisions:hits.append({'uuid':u,'net':t.GetNetname(),'layer':ly,'width_mm':t.GetWidth()/1e6,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'collisions':collisions})
  row.update({'routes':routes,'vias_mm':vias,'crossed_existing_segments':hits,'weighted_cost':costs[found]})
 rows.append(row);(out/'diagnosis.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps({k:v for k,v in row.items() if k not in ['scope','routes']}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
