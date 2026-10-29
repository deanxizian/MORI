"""Read-only joint current-ADC resistor placement using native geometry."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely import intersects_xy, contains_xy
from scipy import ndimage
from plan_layered_route import Planner,mask
from shapely.prepared import prep
from shapely.strtree import STRtree
import numpy as np
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
# Optimistic endpoint access in the existing layout. Native checks after placing
# the two bodies are still required; the masks are not a route certificate.
planner=Planner(c.path,.05,['B.Cu','In3.Cu','F.Cu'],.2)
def accessible(net,seed):
 free,vf,blocked,allowed=planner.geometry(net)
 labs=[];n=0
 for f in free:
  l,k=ndimage.label(f,np.ones((3,3)));l[l>0]+=n;labs.append(l);n+=k
 parents=list(range(n+1))
 def root(k):
  while parents[k]!=k:parents[k]=parents[parents[k]];k=parents[k]
  return k
 for i in range(3):
  for j in range(i+1,3):
   vm=vf&free[i]&free[j]
   if REFERENCE[planner.layers[i]]!=REFERENCE[planner.layers[j]]:vm &= planner.ground_near
   for a,b in np.unique(np.column_stack((labs[i][vm],labs[j][vm])),axis=0):parents[root(int(a))]=root(int(b))
 rootmap=np.array([root(k) for k in range(n+1)])
 pad=next(q for q in planner.c.pads if planner.c.pad_name(q)==seed);sr=set()
 for i,ly in enumerate(planner.layers):
  shp=planner.c.shapes.get((uid(pad),ly))
  if shp is not None:
   m=mask(shp,planner.xx,planner.yy)&free[i]
   sr.update(int(z) for z in np.unique(rootmap[labs[i][m]]) if z)
 m=np.isin(rootmap[labs[0]],list(sr))&free[0]
 ys,xs=np.where(m);print(json.dumps({'net':net,'route_grid_mm':planner.grid,'reachable_cells':int(m.sum()),'bounds_mm':[float(planner.xs[xs.min()]),float(planner.ys[ys.min()]),float(planner.xs[xs.max()]),float(planner.ys[ys.max()])] if len(xs) else None}),flush=True)
 return m
source_access=accessible('Net-(U1001-D3_{slash}_current_ADC)','U1001.8')
mcu_access=accessible('/01 {slash} Core/ACT_CURRENT_ADC','J101.7')
def access_count(shp,m,centre):
 a,b,d,e=shp.bounds
 x0=max(0,int((a-.8)/planner.grid)-1);x1=min(m.shape[1],int((d-.8)/planner.grid)+2)
 y0=max(0,int((b-.8)/planner.grid)-1);y1=min(m.shape[0],int((e-.8)/planner.grid)+2)
 xx=planner.xx[y0:y1,x0:x1];yy=planner.yy[y0:y1,x0:x1]
 vx,vy=shp.centroid.x-centre[0],shp.centroid.y-centre[1]
 outward=(xx-shp.centroid.x)*vx+(yy-shp.centroid.y)*vy>=0
 return int((contains_xy(shp,xx,yy)&m[y0:y1,x0:x1]&outward).sum())
print('endpoint regions ready',flush=True)

refs=['R1003','R1033'];fps={f.GetReference():f for f in c.footprints};mine={uid(p) for ref in refs for p in fps[ref].Pads()}
delete={'a3bd846a-f816-4a29-a3b8-1fa46647bbda'}
others=[polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in c.footprints if f.GetReference() not in refs]
others=[g for g in others if not g.is_empty]
others += [s for (i,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[i],pcb.PAD) and max(xy(c.by_id[i].GetDrillSize()))>0]
others += [k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'B.Cu' in k['layers']]
tracks=prep(unary_union([s for (i,ly),s in c.shapes.items() if ly=='B.Cu' and i not in delete and not isinstance(c.by_id[i],pcb.PAD)]))
via=prep(unary_union([s.buffer(.205) for (i,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[i],pcb.PCB_VIA)]))
source=next(p for p in c.pads if c.pad_name(p)=='U1001.8');mcu=next(p for p in c.pads if c.pad_name(p)=='J101.7')
source_shape=c.shapes[uid(source),'B.Cu'];mcu_pos=Point(xy(mcu.GetPosition()))
route_items=[t for t in c.segments if t.GetLayer()==pcb.B_Cu and uid(t) not in delete]
route_shapes=[c.shapes[uid(t),'B.Cu'] for t in route_items]
route_tree=STRtree(route_shapes)
poses={};xs=np.arange(20,40.001,.1);ys=np.arange(5.8,17.001,.1);xx,yy=np.meshgrid(xs,ys)
for ref in refs:
 f=fps[ref];orig=xy(f.GetPosition());angle0=f.GetOrientationDegrees();pads=list(f.Pads());own=polyset(f.GetCourtyard(pcb.B_CrtYd));fab=[g for g in f.GraphicalItems() if isinstance(g,pcb.PCB_SHAPE) and g.GetLayer()==pcb.B_Fab];assert len(fab)==1 and fab[0].GetShape()==pcb.SHAPE_T_RECT;aa,bb=xy(fab[0].GetStart()),xy(fab[0].GetEnd());body=box(min(aa[0],bb[0]),min(aa[1],bb[1]),max(aa[0],bb[0]),max(aa[1],bb[1]))
 ob={p.GetNetname():prep(unary_union([s.buffer(.205) for (i,ly),s in c.shapes.items() if ly=='B.Cu' and i not in mine|delete and c.by_id[i].GetNetname()!=p.GetNetname() and isinstance(c.by_id[i],(pcb.PAD,pcb.PCB_VIA))])) for p in pads}
 res=[]
 for angle in [0,90,180,270]:
  pc=rotate(own,-(angle-angle0),origin=orig);x0,y0,x1,y1=pc.bounds;hx=(x1-x0)/2+.015;hy=(y1-y0)/2+.015
  obstacles=unary_union([box(a-hx,b-hy,d+hx,e+hy) for a,b,d,e in [g.bounds for g in others]])
  free=~intersects_xy(obstacles,xx,yy)
  for yi,xi in zip(*np.where(free)):
   x,y=float(xs[xi]),float(ys[yi]);dx,dy=x-orig[0],y-orig[1]
   def tr(s):return translate(rotate(s,-(angle-angle0),origin=orig),xoff=dx,yoff=dy)
   new=[(p,tr(c.shapes[uid(p),'B.Cu'])) for p in pads]
   if any(ob[p.GetNetname()].intersects(s) or via.intersects(s) for p,s in new):continue
   access={p.GetNumber():access_count(s,source_access if ref=='R1003' and p.GetNumber()=='1' else mcu_access,(x,y)) for p,s in new if p.GetNumber()=='2' or ref=='R1003'}
   if ref=='R1003':
    if not access['1']:continue
   elif False:continue  # Do not require unchanged-layout MCU access for a layout comparison.
   body_new=tr(body);hit_ids=set()
   for j in route_tree.query(body_new):
    if route_shapes[j].intersects(body_new):hit_ids.add(int(j))
   for pad,shape in new:
    grown=shape.buffer(.205)
    for j in route_tree.query(grown):
     if route_items[j].GetNetname()!=pad.GetNetname() and route_shapes[j].intersects(grown):hit_ids.add(int(j))
   if len(hit_ids)>3:continue
   hits=[{'uuid':uid(route_items[j]),'net':route_items[j].GetNetname(),'width_mm':route_items[j].GetWidth()/1e6,'start_mm':xy(route_items[j].GetStart()),'end_mm':xy(route_items[j].GetEnd())} for j in sorted(hit_ids)]
   res.append({'position_mm':[round(x,4),round(y,4)],'angle_deg':angle,'pads':{p.GetNumber():[round(s.centroid.x,6),round(s.centroid.y,6)] for p,s in new},'courtyard_bounds_mm':tr(own).bounds,'tracks_needing_explicit_review':hits,'optimistic_outward_access_cells':access,'pad_shapes':{p.GetNumber():s for p,s in new}})
 res.sort(key=lambda a:((a['pad_shapes']['1'].distance(source_shape)+1.5*len(a['tracks_needing_explicit_review'])) if ref=='R1003' else min(a['pad_shapes']['1'].distance(mcu_pos),a['pad_shapes']['2'].distance(mcu_pos))))
 poses[ref]=res[:40] if ref=='R1003' else res;print(ref,len(res),'retained',len(poses[ref]),flush=True)
pairs=[]
for a in poses['R1003']:
 gap=a['pad_shapes']['1'].distance(source_shape)
 if gap>40:continue
 for b in poses['R1033']:
  if math.dist(a['position_mm'],b['position_mm'])>6:continue
  if box(*a['courtyard_bounds_mm']).buffer(.015).intersects(box(*b['courtyard_bounds_mm'])):continue
  if any(sa.buffer(.205).intersects(sb) for pa,sa in a['pad_shapes'].items() for pb,sb in b['pad_shapes'].items() if not(pa=='2' and pb=='2')):continue
  series=a['pad_shapes']['2'].distance(b['pad_shapes']['2'])
  mcu_gap=min(a['pad_shapes']['2'].distance(mcu_pos),b['pad_shapes']['2'].distance(mcu_pos))
  pairs.append({'R1003':{k:v for k,v in a.items() if k!='pad_shapes'},'R1033':{k:v for k,v in b.items() if k!='pad_shapes'},'source_gap_mm':gap,'ADC_interconnect_gap_mm':series,'MCU_distance_mm':mcu_gap,'score':1.5*len({x['uuid'] for x in a['tracks_needing_explicit_review']+b['tracks_needing_explicit_review']})+gap+series+.15*mcu_gap})
pairs.sort(key=lambda r:r['score']);chosen=[]
for row in pairs:
 if all(sum(math.dist(row[r]['position_mm'],x[r]['position_mm']) for r in refs)>.65 or any(row[r]['angle_deg']!=x[r]['angle_deg'] for r in refs) for x in chosen):chosen.append(row)
 if len(chosen)>=24:break
p=Path(__file__).with_suffix('.json');assert not p.exists();p.write_text(json.dumps({'source_sha256':c.sha,'route_region_grid_mm':.05,'placement_grid_mm':.1,'own_body_screen':'full nominal B.Fab rectangle, not only narrow native BODY stripe','scope':'DIAGNOSTIC joint ranking now weights source gap 1, interconnect gap 1, MCU distance 0.15 and each affected old segment 1.5. DIAGNOSTIC prioritizes source gap plus 1.5 mm per explicitly affected old segment, not zero-edit positions first; source-side access only for R1003; R1033 MCU access is diagnostic only; MCU-side access may be zero and requires explicit rerouting or new return stitches. Joint nominal geometry and source/MCU raster-region metrics. Old fixed layout masks do not yet include candidate bodies, and are not a route certificate. Up to 3 affected B segments reported, never automatically removed. Retain 40 source-priority R1003 poses and all R1033 poses; pair only within 6 mm centre distance, avoiding density bias from a global per-part cap. No CAD saved.','excluded_tracks':sorted(delete),'pose_counts':{k:len(v) for k,v in poses.items()},'pair_count':len(pairs),'chosen':chosen,'retained_individual_poses':{ref:[{k:v for k,v in row.items() if k!='pad_shapes'} for row in values] for ref,values in poses.items()}},indent=2)+'\n');print(json.dumps({'pair_count':len(pairs),'chosen':chosen[:4]},indent=2),flush=True)
