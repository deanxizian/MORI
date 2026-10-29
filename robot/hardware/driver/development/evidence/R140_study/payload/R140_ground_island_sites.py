"""Read-only through-GND-via placement screening for the R140P surface island.

A GND via does not require a signal anti-pad in its own reference planes, so
that signal-only reference proxy is omitted. Every physical pad/track/drill and
native via keepout remains. Foreign power fill overlaps are reported, never
treated as accepted. Actual native refill and full power/reference checks follow.
"""
import sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
from plan_layered_route import mask
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R140P/MORI_Interface_C3.kicad_pcb')
gs=groups(c,'GND');g=next(g for g in gs if set(g['pads'])=={'C503.2','R1407.1'})
island=g['layers']['B.Cu'];obs=[]
obs.extend(s.buffer(.457) for (u,l),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD) or c.by_id[u].GetNetname()!='GND')
obs.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
obs.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias)
obs.extend(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0)
ob=unary_union(obs)
xs=np.arange(12.,18.001,.05);ys=np.arange(15.5,19.001,.05);xx,yy=np.meshgrid(xs,ys)
good=mask(island.buffer(-.255),xx,yy,True)&~mask(ob,xx,yy)
rows=[]
for iy,ix in zip(*np.where(good)):
 pt=[round(float(xs[ix]),6),round(float(ys[iy]),6)];disk=Point(pt).buffer(.655)
 cuts=[{'net':n,'layer':ly,'area_mm2':disk.intersection(s).area} for n,ly,s in c.fills if n!='GND' and disk.intersects(s)]
 rows.append({'position_mm':pt,'foreign_power_fill_overlaps':cuts,'distance_to_C503_GND_mm':Point(pt).distance(Point(14.55,16.8375))})
rows.sort(key=lambda r:(bool(r['foreign_power_fill_overlaps']),sum(x['area_mm2'] for x in r['foreign_power_fill_overlaps']),r['distance_to_C503_GND_mm']))
f=b/'R140P-ground-sites.json';assert not f.exists();f.write_text(json.dumps({'source_sha256':c.sha,'scope':__doc__,'bounds_mm':[12.,15.5,18.,19.],'grid_mm':.05,'count':len(rows),'sites':rows},indent=2)+'\n')
print(json.dumps({'count':len(rows),'top':rows[:8]}),flush=True)
