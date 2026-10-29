import json,sys,math
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely import intersects_xy,contains_xy
from shapely.prepared import prep
import numpy as np
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');f=next(f for f in c.footprints if f.GetReference()=='D301');orig=xy(f.GetPosition());oldangle=f.GetOrientationDegrees();mine={uid(p) for p in f.Pads()};pads=list(f.Pads());own=polyset(f.GetCourtyard(pcb.B_CrtYd));delete={'a64ead90-f8fb-47e5-9d8d-700e6f43096f'}
others=[polyset(g.GetCourtyard(pcb.B_CrtYd)) for g in c.footprints if g.GetReference()!='D301'];others=[g for g in others if not g.is_empty]
others += [s for (i,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[i],pcb.PAD) and max(xy(c.by_id[i].GetDrillSize()))>0]
others += [k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'B.Cu' in k['layers']]
body=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_D301_')])
ob={p.GetNetname():prep(unary_union([s.buffer(.205) for (i,ly),s in c.shapes.items() if ly=='B.Cu' and i not in mine|delete and c.by_id[i].GetNetname()!=p.GetNetname()])) for p in pads}
via=prep(unary_union([s.buffer(.205) for (i,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[i],pcb.PCB_VIA)]))
tracks=prep(unary_union([s for (i,ly),s in c.shapes.items() if ly=='B.Cu' and i not in delete and not isinstance(c.by_id[i],pcb.PAD)] + [LineString([(32.1,13.15),(32.1,13.85)]).buffer(.1)]))
targets={p.GetNetname():unary_union([s for (i,ly),s in c.shapes.items() if ly=='B.Cu' and i not in mine|delete and c.by_id[i].GetNetname()==p.GetNetname()]) for p in pads}
res=[];xs=np.arange(28,40.001,.1);ys=np.arange(13.5,31.001,.1);xx,yy=np.meshgrid(xs,ys)
for angle in [0,90,180,270]:
 pc=rotate(own,-(angle-oldangle),origin=orig);x0,y0,x1,y1=pc.bounds;hx=(x1-x0)/2+.015;hy=(y1-y0)/2+.015
 obstacles=unary_union([box(a-hx,b-hy,d+hx,e+hy) for a,b,d,e in [g.bounds for g in others]])
 free=~intersects_xy(obstacles,xx,yy)
 print('angle',angle,'courtyard candidates',int(free.sum()),flush=True)
 for yi,xi in zip(*np.where(free)):
  x,y=float(xs[xi]),float(ys[yi]);dx,dy=x-orig[0],y-orig[1]
  def tr(s):return translate(rotate(s,-(angle-oldangle),origin=orig),xoff=dx,yoff=dy)
  new=[(p,tr(c.shapes[uid(p),'B.Cu'])) for p in pads]
  if any(ob[p.GetNetname()].intersects(s) or via.intersects(s) for p,s in new):continue
  if tracks.intersects(tr(body)):continue
  gaps={p.GetNetname():s.distance(targets[p.GetNetname()]) for p,s in new}
  res.append({'position_mm':[round(x,3),round(y,3)],'angle_deg':angle,'pads':{p.GetNumber():[round(s.centroid.x,5),round(s.centroid.y,5)] for p,s in new},'net_gaps_mm':gaps,'score':sum(gaps.values())})
res.sort(key=lambda r:r['score']);chosen=[]
for row in res:
 if all(row['angle_deg']!=x['angle_deg'] or math.dist(row['position_mm'],x['position_mm'])>=1.0 for x in chosen):chosen.append(row)
 if len(chosen)==12:break
Path('robot/.state/c3-completion/trials/R132-d301-poses.json').write_text(json.dumps({'board_sha256':c.sha,'scope':'Nominal native courtyard/copper pose screening only; no PCB change or qualification','candidate_count':len(res),'chosen':chosen},indent=2)+'\n')
print(json.dumps({'count':len(res),'chosen':chosen},indent=2))
