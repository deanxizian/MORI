"""Read-only D1601 placement comparison using both complete connected groups.

Optimistic access on unchanged copper is only a screen; the inserted pads/body,
both routes, refill and all regression gates must pass on a native candidate.
"""
import ast, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely import contains_xy, intersects_xy
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
from shapely.strtree import STRtree
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner, mask

b=Path('robot/.state/c3-completion/trials')
out=b/'R145-D1601-placement.json'
assert not out.exists()
p=Planner('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',.05,['F.Cu','In3.Cu','B.Cu'],.2)
c=p.c
assert c.sha=='f783cf5dfad0ff8020aac8906f12dd018287af6a6d548600d4776fb3603225a5'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
f=next(f for f in c.footprints if f.GetReference()=='D1601')
origin=xy(f.GetPosition()); angle0=f.GetOrientationDegrees(); pads=list(f.Pads()); mine={uid(q) for q in pads}
tail='ae430a96-d266-4760-a4f5-e03c1def3b59'
nets={'1':'Net-(D1601-K)','2':'/01 {slash} Core/ARMED'}
seeds={nets['1']:'U1601.1',nets['2']:'U901.5'}
bodies={}
for ly in ['F.Cu','B.Cu']:
 ss=[]
 for q in c.footprints:
  if c.board.GetLayerName(q.GetLayer())!=ly or q.GetReference()=='D1601':continue
  g=fab(q)
  if q.GetReference() in ['L701','L901']:
   x,y=xy(q.GetPosition());g=translate(rotate(box(-4.6,-4.25,4.6,4.25),-q.GetOrientationDegrees(),origin=(0,0)),xoff=x,yoff=y)
  ss.append(g)
 bodies[ly]=unary_union(ss)
access={};targets={};metrics=[]
for net,seed in seeds.items():
 gs=p.routing_groups(net); group=next(g for g in gs if seed in g['pads'])
 targets[net]=group['layers']['F.Cu'].difference(c.shapes.get((uid(pads[1]),'F.Cu'),GeometryCollection()))
 _,vf,blocked,allowed=p.geometry(net)
 for i,ly in enumerate(p.layers):
  if ly in bodies:
   lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
   blocked[i]=unary_union([blocked[i],bodies[ly].buffer(.102).difference(lands.buffer(-.001))])
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 labs=[];count=0
 for ff in free:
  lab,n=ndimage.label(ff,np.ones((3,3)));lab[lab>0]+=count;labs.append(lab);count+=n
 parents=list(range(count+1))
 def root(k):
  while parents[k]!=k:parents[k]=parents[parents[k]];k=parents[k]
  return k
 for i in range(len(p.layers)):
  for j in range(i+1,len(p.layers)):
   vm=vf&free[i]&free[j]
   if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:vm&=p.ground_near
   for a,z in np.unique(np.column_stack((labs[i][vm],labs[j][vm])),axis=0):parents[root(int(a))]=root(int(z))
 rm=np.array([root(k) for k in range(count+1)]);sr=set()
 for i,ly in enumerate(p.layers):
  if ly not in group['layers']:continue
  m=mask(group['layers'][ly],p.xx,p.yy)&free[i]
  sr.update(int(z) for z in np.unique(rm[labs[i][m]]) if z)
 access[net]=np.isin(rm[labs[0]],list(sr))&free[0]
 metrics.append({'net':net,'seed_group':group['pads'],'reachable_front_cells':int(access[net].sum())})
 print(json.dumps(metrics[-1]),flush=True)
court=polyset(f.GetCourtyard(pcb.F_CrtYd)); body=fab(f)
others=[polyset(q.GetCourtyard(pcb.F_CrtYd)) for q in c.footprints if q.GetReference()!='D1601']
others=[g for g in others if not g.is_empty]
others += [s for (u,ly),s in c.shapes.items() if ly=='F.Cu' and isinstance(c.by_id[u],pcb.PAD) and max(xy(c.by_id[u].GetDrillSize()))>0]
others += [k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'F.Cu' in k['layers']]
via=prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly=='F.Cu' and isinstance(c.by_id[u],pcb.PCB_VIA)]))
obs={net:prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly=='F.Cu' and u not in mine and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net])) for net in seeds}
tracks=[t for t in c.segments if t.GetLayer()==pcb.F_Cu and uid(t)!=tail]
shapes=[c.shapes[uid(t),'F.Cu'] for t in tracks];tree=STRtree(shapes)
def access_count(g,net,centre):
 a,d,z,e=g.bounds
 x0,x1=max(0,int((a-.8)/p.grid)-1),min(p.xx.shape[1],int((z-.8)/p.grid)+2)
 y0,y1=max(0,int((d-.8)/p.grid)-1),min(p.xx.shape[0],int((e-.8)/p.grid)+2)
 xx,yy=p.xx[y0:y1,x0:x1],p.yy[y0:y1,x0:x1];vx,vy=g.centroid.x-centre[0],g.centroid.y-centre[1]
 return int((contains_xy(g,xx,yy)&access[net][y0:y1,x0:x1]&((xx-g.centroid.x)*vx+(yy-g.centroid.y)*vy>=0)).sum())
xs,ys=np.arange(24,38.501,.1),np.arange(14,29.201,.1);xx,yy=np.meshgrid(xs,ys);rows=[]
for angle in [0,90,180,270]:
 r=rotate(court,-(angle-angle0),origin=origin);x0,y0,x1,y1=r.bounds;hx,hy=(x1-x0)/2+.015,(y1-y0)/2+.015
 ob=unary_union([box(a-hx,d-hy,z+hx,e+hy) for a,d,z,e in [g.bounds for g in others]])
 free=~intersects_xy(ob,xx,yy);n=0
 for yi,xi in zip(*np.where(free)):
  x,y=float(xs[xi]),float(ys[yi])
  def tr(g):return translate(rotate(g,-(angle-angle0),origin=origin),xoff=x-origin[0],yoff=y-origin[1])
  pp=[(q,tr(c.shapes[uid(q),'F.Cu'])) for q in pads]
  if any(obs[q.GetNetname()].intersects(g) or via.intersects(g) for q,g in pp):continue
  bg=tr(body);hits={int(j) for j in tree.query(bg) if shapes[j].intersects(bg)}
  for q,g in pp:
   gg=g.buffer(.205);hits.update(int(j) for j in tree.query(gg) if tracks[j].GetNetname()!=q.GetNetname() and shapes[j].intersects(gg))
  if len(hits)>2 or any(tracks[j].GetNetname()!=nets['1'] for j in hits):continue
  counts={q.GetNumber():access_count(g,q.GetNetname(),(x,y)) for q,g in pp}
  if not all(counts.values()):continue
  gaps={q.GetNumber():g.distance(targets[q.GetNetname()]) for q,g in pp}
  rows.append({'position_mm':[round(x,4),round(y,4)],'angle_deg':angle,'pads_mm':{q.GetNumber():[round(g.centroid.x,6),round(g.centroid.y,6)] for q,g in pp},'gaps_mm':gaps,'optimistic_outward_access_cells':counts,'impacted_EN_tracks':[uid(tracks[j]) for j in sorted(hits)],'score':sum(gaps.values())+8*len(hits)})
  n+=1
 print(json.dumps({'angle':angle,'passing_preliminary_positions':n}),flush=True)
rows.sort(key=lambda r:r['score']);chosen=[]
for r in rows:
 if all(math.dist(r['position_mm'],q['position_mm'])>.65 or r['angle_deg']!=q['angle_deg'] for q in chosen):chosen.append(r)
 if len(chosen)==24:break
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'metrics':metrics,'candidate_count':len(rows),'chosen':chosen},indent=2)+'\n')
print(json.dumps({'candidate_count':len(rows),'chosen':chosen[:6]},indent=2),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
