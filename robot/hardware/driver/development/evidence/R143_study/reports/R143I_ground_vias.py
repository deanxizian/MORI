"""Read-only physical/reference screening for a direct C1403 ground stitch.
No blanket signal-reference exclusion is applied to a GND via, which joins the
reference planes. Actual refill must still preserve every power corridor.
"""
import json,sys,math
from pathlib import Path
import numpy as np
from shapely import contains_xy,intersects_xy
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');out=b/'R143I-ground-via-sites.json';assert not out.exists()
c=Copper(str(b/'R143G/MORI_Interface_C3.kicad_pcb'))
g=next(g for g in groups(c,'GND') if g['pads']==['C1403.2'])['layers']['B.Cu']
obs=[]
for (u,ly),s in c.shapes.items():
 o=c.by_id[u]
 if isinstance(o,pcb.PAD) or o.GetNetname()!='GND':obs.append(s.buffer(.457))
for k in c.keepouts:
 if k['vias']:obs.append(k['shape'].buffer(.257))
for v in c.vias:obs.append(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307))
for p in c.pads:
 if max(xy(p.GetDrillSize()))>0:obs.append(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557))
obs=unary_union(obs)
xs=np.arange(24,30.51,.05);ys=np.arange(14.5,18.81,.05);xx,yy=np.meshgrid(xs,ys)
m=contains_xy(g,xx,yy)&~intersects_xy(obs,xx,yy)
for ly in ['In1.Cu','In4.Cu']:m &= contains_xy(c.copper['GND',ly],xx,yy)
rows=[]
for yi,xi in zip(*np.where(m)):
 p=[round(float(xs[xi]),4),round(float(ys[yi]),4)];rows.append({'position_mm':p,'distance_to_pad_mm':math.dist(p,[28.825,15.725])})
rows.sort(key=lambda r:r['distance_to_pad_mm']);chosen=[]
for r in rows:
 if all(math.dist(r['position_mm'],q['position_mm'])>.3 for q in chosen):chosen.append(r)
 if len(chosen)==12:break
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'count':len(rows),'chosen':chosen},indent=2)+'\n')
print(json.dumps({'count':len(rows),'chosen':chosen},indent=2))
