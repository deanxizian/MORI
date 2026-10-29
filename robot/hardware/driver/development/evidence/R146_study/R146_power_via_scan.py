"""Find real MOTION_5V plane landing sites without adding forbidden In2 tracks."""
import json,sys,math
from pathlib import Path
import numpy as np
from shapely import intersects_xy,contains_xy
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R146C-motion-via-sites.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R146C/MORI_Interface_C3.kicad_pcb')
net='/01 {slash} Core/MOTION_5V';old='c9ef7bb5-bef9-48b7-b4cf-23501fe0a859'
plane=unary_union([g for n,ly,g in a.fills if n==net and ly=='In2.Cu'])
physical=[s.buffer(.455) for (u,ly),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD)]
physical += [s.buffer(.455) for (u,ly),s in c.shapes.items() if not isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net]
physical += [k['shape'].buffer(.255) for k in c.keepouts if k['vias']]
physical += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.305) for v in c.vias if uid(v)!=old]
physical += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.555) for p in c.pads if max(xy(p.GetDrillSize()))>0]
block=unary_union(physical);xs=np.arange(30,52,.05);ys=np.arange(2,20,.05);xx,yy=np.meshgrid(xs,ys)
free=contains_xy(plane.buffer(-.1),xx,yy)&~intersects_xy(block,xx,yy)
ground={ly:c.copper.get(('GND',ly),GeometryCollection()) for ly in ['In1.Cu','In4.Cu']}
anchors=[v for v in c.anchors('GND') if all((uid(v),ly) in c.shapes and c.shapes[uid(v),ly].intersects(ground[ly]) for ly in ground)]
rows=[]
for yi,xi in zip(*np.where(free)):
 pos=[round(float(xs[xi]),4),round(float(ys[yi]),4)];pt=Point(pos);void=pt.buffer(.655);hits=[]
 for t in c.segments:
  ly=c.board.GetLayerName(t.GetLayer())
  if t.GetNetname() in ['GND',net] or ly not in REFERENCE:continue
  loss=c.shapes[uid(t),ly].intersection(ground[REFERENCE[ly]]).intersection(void).area
  if loss>1e-6:hits.append({'uuid':uid(t),'net':t.GetNetname(),'layer':ly,'reference_loss_mm2':loss})
 near=min((math.dist(pos,xy(v.GetPosition())) for v in anchors),default=100)
 rows.append({'position_mm':pos,'nearest_ground_mm':near,'reference_hits':hits,'score':math.dist(pos,[44.5,10.25])+15*len(hits)+20*(near>2)})
rows.sort(key=lambda x:x['score']);chosen=[]
for r in rows:
 if all(math.dist(r['position_mm'],q['position_mm'])>.35 for q in chosen):chosen.append(r)
 if len(chosen)>=16:break
result={'argv':[sys.executable,*sys.argv],'canonical_sha256':a.sha,'candidate_sha256':c.sha,'source_plane_bounds':[list(g.bounds) for g in parts(plane)],'physical_sites':len(rows),'chosen':chosen,'scope':__doc__}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
