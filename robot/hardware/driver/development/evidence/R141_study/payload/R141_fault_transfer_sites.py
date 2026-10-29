"""Read-only local FAULT transfer diagnostics with explicit own-tail review.

Foreign reference copper remains protected. Potential holes under same-net
B-face tails are reported with exact old track UUIDs for explicit replacement;
no source board or formal checker is changed and no candidate is accepted here.
Sites affecting own traces on another layer are rejected in this limited study.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-fault-transfer-sites');out.mkdir(exist_ok=False)
p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.025,['B.Cu','In3.Cu'],.2);c=p.c;net='/FAULT_N'
free,_,blocked,allowed=p.geometry(net)
physical=[s.buffer(.457) for (u,l),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD) or c.by_id[u].GetNetname()!=net]
physical += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
physical += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias]
physical += [Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0]
guard=[]
for t in c.segments:
 ly=c.board.GetLayerName(t.GetLayer())
 if ly in REFERENCE and t.GetNetname() not in ['GND',net]:
  guard.append(c.shapes[(uid(t),ly)].intersection(p.ground[REFERENCE[ly]]))
physical=unary_union(physical);foreign_ref=unary_union(guard).buffer(.657)
own=[t for t in c.segments if t.GetNetname()==net and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
rows=[]
for label,bounds,old_end in [('left',[17.8,26.1,19.4,27.55],[19.15,27.15]),('right',[20.9,29.2,23.,30.3],[21.4,29.4])]:
 xs=np.arange(bounds[0],bounds[2]+.001,.025);ys=np.arange(bounds[1],bounds[3]+.001,.025);xx,yy=np.meshgrid(xs,ys)
 good=~mask(physical,xx,yy)&~mask(foreign_ref,xx,yy)
 # Require prospective B/In3 centre access against existing physical copper
 # and reference coverage, while separately allowing the declared own escape.
 for ob,al in zip(blocked,allowed):good &= ~mask(ob,xx,yy)&mask(al,xx,yy,True)
 sites=[]
 for iy,ix in zip(*np.where(good)):
  pt=[round(float(xs[ix]),6),round(float(ys[iy]),6)];disk=Point(pt).buffer(.655)
  affected=[t for t in own if c.shapes[(uid(t),c.board.GetLayerName(t.GetLayer()))].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]).intersects(disk)]
  if any(t.GetLayer()!=pcb.B_Cu for t in affected):continue
  power=[{'net':n,'layer':ly,'cut_mm2':disk.intersection(s).area} for n,ly,s in c.fills if n not in [net,'GND'] and disk.intersects(s)]
  sites.append({'position_mm':pt,'own_B_tracks_requiring_review':[uid(t) for t in affected],'foreign_power_fill_overlaps':power,'distance_to_old_end_mm':Point(pt).distance(Point(old_end))})
 sites.sort(key=lambda r:(len(r['own_B_tracks_requiring_review']),sum(v['cut_mm2'] for v in r['foreign_power_fill_overlaps'])+.5*r['distance_to_old_end_mm']))
 row={'region':label,'bounds_mm':bounds,'grid_mm':.025,'sites':sites};rows.append(row)
 print(json.dumps({'region':label,'count':len(sites),'top':sites[:8]}),flush=True)
(out/'result.json').write_text(json.dumps({'source_sha256':c.sha,'scope':__doc__,'regions':rows},indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
