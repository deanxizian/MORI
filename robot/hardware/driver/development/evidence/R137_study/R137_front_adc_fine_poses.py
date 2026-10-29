"""Read-only front-face ADC pair screening with explicit optimistic access.

Neither PCB nor acceptance rules are saved. Native opposite-face mirroring is
performed only in a second, unsaved board instance to derive real pad numbers.
The old-layout route masks are optimistic and must be recomputed after placement.
"""
import json,math,sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely import intersects_xy,contains_xy
from shapely.prepared import prep
from shapely.strtree import STRtree
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask

path='robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb'
p=Planner(path,.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
assert c.sha=='0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
out=Path(__file__).with_suffix('.json');assert not out.exists()
metrics=[]
def reachable(net,seed):
 free,vf,blocked,allowed=p.geometry(net);labs=[];n=0
 for f in free:
  l,k=ndimage.label(f,np.ones((3,3)));l[l>0]+=n;labs.append(l);n+=k
 parents=list(range(n+1))
 def root(k):
  while parents[k]!=k:parents[k]=parents[parents[k]];k=parents[k]
  return k
 for i in range(3):
  for j in range(i+1,3):
   vm=vf&free[i]&free[j]
   if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:vm &= p.ground_near
   for a,b in np.unique(np.column_stack((labs[i][vm],labs[j][vm])),axis=0):parents[root(int(a))]=root(int(b))
 rootmap=np.array([root(k) for k in range(n+1)])
 q=next(q for q in c.pads if c.pad_name(q)==seed);sr=set()
 for i,ly in enumerate(p.layers):
  g=c.shapes.get((uid(q),ly))
  if g is not None:
   m=mask(g,p.xx,p.yy)&free[i];sr.update(int(z) for z in np.unique(rootmap[labs[i][m]]) if z)
 m=np.isin(rootmap[labs[2]],list(sr))&free[2]
 ys,xs=np.where(m)
 metrics.append({'net':net,'seed':seed,'front_cell_count':int(m.sum()),'bounds_mm':[float(p.xs[xs.min()]),float(p.ys[ys.min()]),float(p.xs[xs.max()]),float(p.ys[ys.max()])] if len(xs) else None})
 return m
source_access=reachable('Net-(U1001-D3_{slash}_current_ADC)','U1001.8')
mcu_access=reachable('/01 {slash} Core/ACT_CURRENT_ADC','J101.7')
print(json.dumps(metrics),flush=True)
def access_count(shp,m,centre):
 a,b,d,e=shp.bounds;x0=max(0,int((a-.8)/p.grid)-1);x1=min(m.shape[1],int((d-.8)/p.grid)+2)
 y0=max(0,int((b-.8)/p.grid)-1);y1=min(m.shape[0],int((e-.8)/p.grid)+2)
 xx=p.xx[y0:y1,x0:x1];yy=p.yy[y0:y1,x0:x1]
 vx,vy=shp.centroid.x-centre[0],shp.centroid.y-centre[1]
 return int((contains_xy(shp,xx,yy)&m[y0:y1,x0:x1]&((xx-shp.centroid.x)*vx+(yy-shp.centroid.y)*vy>=0)).sum())

refs=['R1003','R1033'];mine={uid(q) for f in c.footprints if f.GetReference() in refs for q in f.Pads()}
others=[polyset(f.GetCourtyard(pcb.F_CrtYd)) for f in c.footprints if f.GetReference() not in refs]
others=[g for g in others if not g.is_empty]
others += [g for (u,ly),g in c.shapes.items() if ly=='F.Cu' and isinstance(c.by_id[u],pcb.PAD) and max(xy(c.by_id[u].GetDrillSize()))>0]
others += [k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'F.Cu' in k['layers']]
vias=prep(unary_union([g.buffer(.205) for (u,ly),g in c.shapes.items() if ly=='F.Cu' and isinstance(c.by_id[u],pcb.PCB_VIA)]))
tracks=[t for t in c.segments if t.GetLayer()==pcb.F_Cu];shapes=[c.shapes[uid(t),'F.Cu'] for t in tracks];tree=STRtree(shapes)
templates=pcb.LoadBoard(path);fps={f.GetReference():f for f in templates.GetFootprints()}
source=Point(xy(next(q for q in c.pads if c.pad_name(q)=='U1001.8').GetPosition()))
mcu=Point(xy(next(q for q in c.pads if c.pad_name(q)=='J101.7').GetPosition()))
xs=np.arange(3,67.001,.1);ys=np.arange(6.2,29.301,.1);xx,yy=np.meshgrid(xs,ys);poses={};all_counts={}
for ref in refs:
 f=fps[ref];origin=xy(f.GetPosition());f.Flip(f.GetPosition(),pcb.FLIP_DIRECTION_TOP_BOTTOM);f.SetOrientationDegrees(0)
 assert f.GetLayer()==pcb.F_Cu
 own=polyset(f.GetCourtyard(pcb.F_CrtYd));assert not own.is_empty
 pads=[(q,shape(q,pcb.F_Cu)) for q in f.Pads()]
 fab=[g for g in f.GraphicalItems() if isinstance(g,pcb.PCB_SHAPE) and g.GetLayer()==pcb.F_Fab]
 assert len(fab)==1 and fab[0].GetShape()==pcb.SHAPE_T_RECT
 a,b=xy(fab[0].GetStart()),xy(fab[0].GetEnd());body=box(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))
 obs={q.GetNetname():prep(unary_union([g.buffer(.205) for (u,ly),g in c.shapes.items() if ly=='F.Cu' and u not in mine and c.by_id[u].GetNetname()!=q.GetNetname() and isinstance(c.by_id[u],(pcb.PAD,pcb.PCB_VIA))])) for q,g in pads}
 res=[]
 for angle in [0,90,180,270]:
  rotated=rotate(own,-angle,origin=origin);x0,y0,x1,y1=rotated.bounds;hx=(x1-x0)/2+.015;hy=(y1-y0)/2+.015
  obstacle=unary_union([box(a-hx,b-hy,d+hx,e+hy) for a,b,d,e in [g.bounds for g in others]])
  free=~intersects_xy(obstacle,xx,yy)
  for yi,xi in zip(*np.where(free)):
   x,y=float(xs[xi]),float(ys[yi]);dx,dy=x-origin[0],y-origin[1]
   def tr(g):return translate(rotate(g,-angle,origin=origin),xoff=dx,yoff=dy)
   new=[(q,tr(g)) for q,g in pads]
   if any(obs[q.GetNetname()].intersects(g) or vias.intersects(g) for q,g in new):continue
   access={q.GetNumber():access_count(g,source_access if ref=='R1003' and q.GetNumber()=='1' else mcu_access,(x,y)) for q,g in new if ref=='R1003' or q.GetNumber()=='2'}
   if not all(access.values()):continue
   hits=set();bg=tr(body)
   for j in tree.query(bg):
    if shapes[j].intersects(bg):hits.add(int(j))
   for q,g in new:
    grown=g.buffer(.205)
    for j in tree.query(grown):
     if tracks[j].GetNetname()!=q.GetNetname() and shapes[j].intersects(grown):hits.add(int(j))
   if len(hits)>3:continue
   impacted=[{'uuid':uid(tracks[j]),'net':tracks[j].GetNetname(),'width_mm':tracks[j].GetWidth()/1e6,'start_mm':xy(tracks[j].GetStart()),'end_mm':xy(tracks[j].GetEnd())} for j in sorted(hits)]
   res.append({'position_mm':[round(x,4),round(y,4)],'angle_deg':angle,'face':'F.Cu','pads':{q.GetNumber():[round(g.centroid.x,6),round(g.centroid.y,6)] for q,g in new},'courtyard_bounds_mm':tr(own).bounds,'nominal_fab_bounds_mm':bg.bounds,'optimistic_outward_access_cells':access,'tracks_needing_explicit_review':impacted,'pad_shapes':{q.GetNumber():g for q,g in new}})
 res.sort(key=lambda a:(len(a['tracks_needing_explicit_review']),a['pad_shapes']['2'].distance(mcu)))
 all_counts[ref]=len(res);poses[ref]=res[:500];print(ref,len(res),'retained',len(poses[ref]),flush=True)
pairs=[]
for a in poses['R1003']:
 for b in poses['R1033']:
  if box(*a['courtyard_bounds_mm']).buffer(.015).intersects(box(*b['courtyard_bounds_mm'])):continue
  if any(sa.buffer(.205).intersects(sb) for pa,sa in a['pad_shapes'].items() for pb,sb in b['pad_shapes'].items() if not(pa=='2' and pb=='2')):continue
  dg=a['pad_shapes']['1'].distance(source);series=a['pad_shapes']['2'].distance(b['pad_shapes']['2']);mc=min(a['pad_shapes']['2'].distance(mcu),b['pad_shapes']['2'].distance(mcu))
  pairs.append({'R1003':{k:v for k,v in a.items() if k!='pad_shapes'},'R1033':{k:v for k,v in b.items() if k!='pad_shapes'},'source_distance_mm':dg,'ADC_interconnect_gap_mm':series,'MCU_distance_mm':mc,'score':5*len({z['uuid'] for z in a['tracks_needing_explicit_review']+b['tracks_needing_explicit_review']})+.35*dg+series+.4*mc})
pairs.sort(key=lambda row:row['score']);chosen=[]
for row in pairs:
 if all(sum(math.dist(row[r]['position_mm'],other[r]['position_mm']) for r in refs)>.65 or any(row[r]['angle_deg']!=other[r]['angle_deg'] for r in refs) for other in chosen):chosen.append(row)
 if len(chosen)>=20:break
result={'source_sha256':c.sha,'scope':__doc__,'native_template_flip':'TOP_BOTTOM at original centre, then native 0-degree orientation; only unsaved second board changed.','route_region_grid_mm':.05,'placement_grid_mm':.1,'region_metrics':metrics,'all_pose_counts':all_counts,'retained_pose_counts':{r:len(a) for r,a in poses.items()},'pair_count':len(pairs),'chosen':chosen}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pair_count':len(pairs),'chosen':chosen[:2]},indent=2),flush=True)
assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==c.sha
