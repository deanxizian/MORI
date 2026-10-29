"""Read-only joint current-ADC resistor placement using native geometry."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely import intersects_xy
from shapely.prepared import prep
from shapely.strtree import STRtree
import numpy as np
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
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
poses={};xs=np.arange(29,47.001,.1);ys=np.arange(5,29.301,.1);xx,yy=np.meshgrid(xs,ys)
for ref in refs:
 f=fps[ref];orig=xy(f.GetPosition());angle0=f.GetOrientationDegrees();pads=list(f.Pads());own=polyset(f.GetCourtyard(pcb.B_CrtYd));body=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')])
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
   body_new=tr(body);hit_ids=set()
   for j in route_tree.query(body_new):
    if route_shapes[j].intersects(body_new):hit_ids.add(int(j))
   for pad,shape in new:
    grown=shape.buffer(.205)
    for j in route_tree.query(grown):
     if route_items[j].GetNetname()!=pad.GetNetname() and route_shapes[j].intersects(grown):hit_ids.add(int(j))
   if len(hit_ids)>3:continue
   hits=[{'uuid':uid(route_items[j]),'net':route_items[j].GetNetname(),'width_mm':route_items[j].GetWidth()/1e6,'start_mm':xy(route_items[j].GetStart()),'end_mm':xy(route_items[j].GetEnd())} for j in sorted(hit_ids)]
   res.append({'position_mm':[round(x,4),round(y,4)],'angle_deg':angle,'pads':{p.GetNumber():[round(s.centroid.x,6),round(s.centroid.y,6)] for p,s in new},'courtyard_bounds_mm':tr(own).bounds,'tracks_needing_explicit_review':hits,'pad_shapes':{p.GetNumber():s for p,s in new}})
 res.sort(key=lambda a:(len(a['tracks_needing_explicit_review']),min(a['pad_shapes']['1'].distance(mcu_pos),a['pad_shapes']['2'].distance(mcu_pos))))
 poses[ref]=res[:300];print(ref,len(res),'retained',len(poses[ref]),flush=True)
pairs=[]
for a in poses['R1003']:
 gap=a['pad_shapes']['1'].distance(source_shape)
 if gap>40:continue
 for b in poses['R1033']:
  if box(*a['courtyard_bounds_mm']).buffer(.015).intersects(box(*b['courtyard_bounds_mm'])):continue
  if any(sa.buffer(.205).intersects(sb) for pa,sa in a['pad_shapes'].items() for pb,sb in b['pad_shapes'].items() if not(pa=='2' and pb=='2')):continue
  series=a['pad_shapes']['2'].distance(b['pad_shapes']['2'])
  mcu_gap=min(a['pad_shapes']['2'].distance(mcu_pos),b['pad_shapes']['2'].distance(mcu_pos))
  pairs.append({'R1003':{k:v for k,v in a.items() if k!='pad_shapes'},'R1033':{k:v for k,v in b.items() if k!='pad_shapes'},'source_gap_mm':gap,'ADC_interconnect_gap_mm':series,'MCU_distance_mm':mcu_gap,'score':5*len({x['uuid'] for x in a['tracks_needing_explicit_review']+b['tracks_needing_explicit_review']})+.35*gap+series+.4*mcu_gap})
pairs.sort(key=lambda r:r['score']);chosen=[]
for row in pairs:
 if all(sum(math.dist(row[r]['position_mm'],x[r]['position_mm']) for r in refs)>.65 or any(row[r]['angle_deg']!=x[r]['angle_deg'] for r in refs) for x in chosen):chosen.append(row)
 if len(chosen)>=16:break
p=Path(__file__).with_suffix('.json');assert not p.exists();p.write_text(json.dumps({'source_sha256':c.sha,'scope':'Joint nominal pad/via/courtyard comparison. Up to three existing B tracks per footprint are reported as potential explicit replacements, not silently deleted. At most 300 poses per component are retained by copper impact and MCU distance. No PCB saved or electrical/physical qualification.','excluded_tracks':sorted(delete),'pose_counts':{k:len(v) for k,v in poses.items()},'pair_count':len(pairs),'chosen':chosen},indent=2)+'\n');print(json.dumps({'pair_count':len(pairs),'chosen':chosen[:4]},indent=2),flush=True)
