"""Bounded read-only ground-via screening for isolated R1031 on R152D."""
import sys,json
from pathlib import Path
import numpy as np
from shapely import contains_xy,intersects_xy
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R152D/MORI_Interface_C3.kicad_pcb')
ob=[s.buffer(.457) for (i,ly),s in c.shapes.items() if isinstance(c.by_id[i],pcb.PAD) or c.by_id[i].GetNetname()!='GND']
ob += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
ob += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias]
ob += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0]
blocked=unary_union(ob)
ground=c.copper['GND','In1.Cu'].intersection(c.copper['GND','In4.Cu']).buffer(-.251)
xx,yy=np.meshgrid(np.arange(42.5,47.501,.05),np.arange(27,32.501,.05))
valid=~intersects_xy(blocked,xx,yy)
points=[]
for x,y in zip(xx[valid],yy[valid]):
 pt=Point(float(x),float(y)); row={'point_mm':[round(float(x),4),round(float(y),4)],'distance_R1031_ground_mm':pt.distance(Point(45.325,27.75))}
 row['ground_reference_overlap_mm2']={ly:pt.buffer(.25).intersection(c.copper['GND',ly]).area for ly in ['In1.Cu','In4.Cu']};points.append(row)
points.sort(key=lambda r:r['distance_R1031_ground_mm'])
result={'source_sha256':c.sha,'scope':__doc__,'grid_mm':.05,'candidates':points,'limits':'Candidate geometry only. Native clearance, power continuity, route and field/thermal review still required.'}
(b/'R152-ground-sites-physical.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'candidates':len(points),'nearest':points[:12]}))
