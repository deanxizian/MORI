"""Read-only R301 relocation screen to free two independent ADC escape lanes.

DIAGNOSTIC v3 adds full mounted-face nominal body avoidance and bounded same-face grid travel distances. Diagonal grid adjacency is only a preliminary metric, not exact vector clearance. Adds outward pad overlap with existing-layout same-face reachable regions for both CLR main and MOTION. These regions omit candidate-body effects and are not a route certificate. Original circuits and all fixed interfaces are preserved. Full native courtyards,
pad/via physical spacing and mounted-face body obstacles are screened; <=2 old
thin signal segments may be identified, never silently removed. No CAD saved.
"""
import json,sys,math,heapq,ast
from shapely.ops import polygonize
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.prepared import prep
from shapely.strtree import STRtree
from shapely import intersects_xy, contains_xy
from scipy import ndimage
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R138A/MORI_Interface_C3.kicad_pcb')
f=next(f for f in c.footprints if f.GetReference()=='R301');orig=xy(f.GetPosition());a0=f.GetOrientationDegrees();pads=list(f.Pads());mine={uid(p) for p in pads}
delete={'230cb21f-4911-4036-aae2-57aff98a573f','1ede06b9-41c1-4310-a17c-0e306d5bfab5','d1ec54fc-e170-433e-836a-1f6be3a0dd1e'}
others=[polyset(q.GetCourtyard(pcb.B_CrtYd)) for q in c.footprints if q.GetReference()!='R301'];others=[g for g in others if not g.is_empty]
others += [s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and max(xy(c.by_id[u].GetDrillSize()))>0]
others += [k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'B.Cu' in k['layers']]
court=polyset(f.GetCourtyard(pcb.B_CrtYd));fab=[x for x in f.GraphicalItems() if isinstance(x,pcb.PCB_SHAPE) and x.GetLayer()==pcb.B_Fab]
assert len(fab)==1 and fab[0].GetShape()==pcb.SHAPE_T_RECT
aa,bb=xy(fab[0].GetStart()),xy(fab[0].GetEnd());body=box(min(aa[0],bb[0]),min(aa[1],bb[1]),max(aa[0],bb[0]),max(aa[1],bb[1]))
via=prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PCB_VIA)]))
obs={p.GetNetname():prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly=='B.Cu' and u not in mine and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=p.GetNetname()])) for p in pads}
targets={net:unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and u not in mine|delete and c.by_id[u].GetNetname()==net]+[g for n,ly,g in c.fills if n==net and ly=='B.Cu']) for net in ['/CLR_N','MOTION_3V3']}
tracks=[t for t in c.segments if t.GetLayer()==pcb.B_Cu and uid(t) not in delete];shapes=[c.shapes[uid(t),'B.Cu'] for t in tracks];tree=STRtree(shapes)
planner=Planner(c.path,.05,['B.Cu'],.2)
access={};geodesic={}
tree_=ast.parse((b/'R138_joint_search.py').read_text());node_=next(n for n in tree_.body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node_],type_ignores=[]),'fab_helper','exec'),globals())
full_bodies=unary_union([fab(q) for q in c.footprints if q.GetLayer()==pcb.B_Cu and q.GetReference()!='R301'])
for net in ['/CLR_N','MOTION_3V3']:
 free,_,blocked,allowed=planner.geometry(net)
 own=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked[0]=unary_union([blocked[0],full_bodies.buffer(.102).difference(own.buffer(-.001))])
 free[0]=~mask(blocked[0],planner.xx,planner.yy)&mask(allowed[0],planner.xx,planner.yy,True)
 labs,_=ndimage.label(free[0],np.ones((3,3)))
 gg=next(g for g in groups(c,net) if ('J102.4' if net=='/CLR_N' else 'C301.1') in g['pads'])
 seeds=mask(gg['layers']['B.Cu'],planner.xx,planner.yy)&free[0]
 labels=set(int(x) for x in np.unique(labs[seeds]) if x)
 access[net]=np.isin(labs,list(labels))&free[0]
 dist=np.full(free[0].shape,np.inf);queue=[]
 for y_,x_ in zip(*np.where(seeds)):dist[y_,x_]=0;queue.append((0.,int(y_),int(x_)))
 heapq.heapify(queue);h,w=dist.shape
 while queue:
  v,y_,x_=heapq.heappop(queue)
  if v!=dist[y_,x_]:continue
  for dy_,dx_ in [(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]:
   Y,X=y_+dy_,x_+dx_
   if 0<=Y<h and 0<=X<w and free[0,Y,X]:
    z=v+.05*(math.sqrt(2) if dy_ and dx_ else 1)
    if z<dist[Y,X]:dist[Y,X]=z;heapq.heappush(queue,(z,Y,X))
 geodesic[net]=dist
 print(json.dumps({'net':net,'same_face_reachable_cells':int(access[net].sum())}),flush=True)
def accessible_shape(g,net,centre):
 x0,y0,x1,y1=g.bounds;ix0=max(0,int((x0-.8)/.05)-1);ix1=min(planner.xx.shape[1],int((x1-.8)/.05)+2);iy0=max(0,int((y0-.8)/.05)-1);iy1=min(planner.xx.shape[0],int((y1-.8)/.05)+2)
 xx_=planner.xx[iy0:iy1,ix0:ix1];yy_=planner.yy[iy0:iy1,ix0:ix1]
 vx,vy=g.centroid.x-centre[0],g.centroid.y-centre[1]
 outward=(xx_-g.centroid.x)*vx+(yy_-g.centroid.y)*vy>=0
 mm=contains_xy(g,xx_,yy_)&access[net][iy0:iy1,ix0:ix1]&outward
 return (int(mm.sum()),float(geodesic[net][iy0:iy1,ix0:ix1][mm].min()) if mm.any() else math.inf)
xs=np.arange(6,29.001,.1);ys=np.arange(6,23.001,.1);xx,yy=np.meshgrid(xs,ys);rows=[]
for a in [0,90,180,270]:
 rotated=rotate(court,-(a-a0),origin=orig);x0,y0,x1,y1=rotated.bounds;hx=(x1-x0)/2+.015;hy=(y1-y0)/2+.015
 ob=unary_union([box(x-hx,y-hy,X+hx,Y+hy) for x,y,X,Y in [g.bounds for g in others]])
 free=~intersects_xy(ob,xx,yy);n=0
 for yi,xi in zip(*np.where(free)):
  x,y=float(xs[xi]),float(ys[yi]);dx,dy=x-orig[0],y-orig[1]
  if 26<x<29 and 8<y<13:continue # This is the corridor to be freed, not a useful relocation.
  def tr(g):return translate(rotate(g,-(a-a0),origin=orig),xoff=dx,yoff=dy)
  pp=[(p,tr(c.shapes[uid(p),'B.Cu'])) for p in pads]
  if any(obs[p.GetNetname()].intersects(g) or via.intersects(g) for p,g in pp):continue
  body_new=tr(body);hits=set()
  for j in tree.query(body_new):
   if shapes[j].intersects(body_new):hits.add(int(j))
  for p,g in pp:
   grown=g.buffer(.205)
   for j in tree.query(grown):
    if tracks[j].GetNetname()!=p.GetNetname() and shapes[j].intersects(grown):hits.add(int(j))
  if len(hits)>2 or any(tracks[j].GetWidth()/1e6>.201 or tracks[j].GetNetname() in ['GND','MOTION_3V3'] for j in hits):continue
  counts={p.GetNetname():accessible_shape(g,p.GetNetname(),(x,y)) for p,g in pp}
  if not all(v[0] for v in counts.values()):continue
  gaps={p.GetNetname():g.distance(targets[p.GetNetname()]) for p,g in pp}
  row={'position_mm':[round(x,4),round(y,4)],'angle_deg':a,'pads_mm':{p.GetNumber():[round(g.centroid.x,6),round(g.centroid.y,6)] for p,g in pp},'gaps_mm':gaps,'impacted_tracks':[{'uuid':uid(tracks[j]),'net':tracks[j].GetNetname(),'start_mm':xy(tracks[j].GetStart()),'end_mm':xy(tracks[j].GetEnd())} for j in sorted(hits)],'optimistic_same_face_access_cells':counts,'score':sum(v[1] for v in counts.values())+8*len(hits)+.05*math.dist((x,y),orig)}
  rows.append(row);n+=1
 print(json.dumps({'angle':a,'valid_positions':n}),flush=True)
rows.sort(key=lambda r:r['score']);chosen=[]
for row in rows:
 if all(math.dist(row['position_mm'],q['position_mm'])>.7 or row['angle_deg']!=q['angle_deg'] for q in chosen):chosen.append(row)
 if len(chosen)==20:break
p=b/'R139_pullup_geodesic_placement.json';assert not p.exists();p.write_text(json.dumps({'source_sha256':c.sha,'scope':__doc__,'grid_mm':.1,'candidate_count':len(rows),'source_tracks_to_replace':sorted(delete),'chosen':chosen},indent=2)+'\n')
print(json.dumps({'chosen':chosen[:6]},indent=2),flush=True)
