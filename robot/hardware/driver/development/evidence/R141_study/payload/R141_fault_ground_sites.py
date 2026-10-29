"""Screen real ground stitch sites for the new FAULT In2/In3 transition.

No acceptance exemption. Both native reference pours must be present, all pad
physical spacing, non-ground copper and native via keepouts stay protected.
Power antipad projection is ranked; refill/power/ground checks remain required.
"""
import json
import math
import sys
from pathlib import Path
from shapely.geometry import box
from shapely.prepared import prep
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1]
c=Copper(b/rev/'MORI_Interface_C3.kicad_pcb')
v=c.by_id['f2307f60-c4ef-5ffa-9957-65a1a34d8f3a'];centre=xy(v.GetPosition())
obstacles=[]
for (u,ly),s in c.shapes.items():
 o=c.by_id[u]
 if isinstance(o,pcb.PAD) or o.GetNetname()!='GND':obstacles.append(s.buffer(.457))
 elif isinstance(o,pcb.PCB_VIA):obstacles.append(Point(xy(o.GetPosition())).buffer(.707))
for pad in c.pads:
 drill=max(xy(pad.GetDrillSize()))
 if drill>0:obstacles.append(Point(xy(pad.GetPosition())).buffer(drill/2+.557))
for via in c.vias:obstacles.append(Point(xy(via.GetPosition())).buffer(via.GetDrillValue()/2e6+.557))
obstacles += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
blocked=prep(unary_union(obstacles))
ground=prep(c.copper['GND','In1.Cu'].intersection(c.copper['GND','In4.Cu']).buffer(-.257).intersection(box(.757,.757,69.243,34.243)))
power=unary_union([s for n,l,s in c.fills if n!='GND'])
rows=[]
x,y=centre
for ix in range(math.ceil((x-1.95)*40),math.floor((x+1.95)*40)+1):
 for iy in range(math.ceil((y-1.95)*40),math.floor((y+1.95)*40)+1):
  pt=(ix/40,iy/40);distance=math.dist(pt,centre);q=Point(pt)
  if not .71<=distance<=1.95 or blocked.intersects(q) or not ground.contains(q):continue
  rows.append({'position_mm':list(pt),'distance_mm':distance,'power_antipad_projection_mm2':q.buffer(.655).intersection(power).area})
rows.sort(key=lambda r:(r['power_antipad_projection_mm2'],r['distance_mm']))
report={'scope':__doc__,'source_sha256':c.sha,'signal_uuid':uid(v),'signal_position_mm':centre,'candidate_count':len(rows),'candidates':rows[:60]}
with (b/(rev+'-fault-ground-sites.json')).open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({**report,'candidates':rows[:5]},indent=2))
if rows:
 plan={'revision':'R141D','board_sha256':c.sha,'purpose':'Add nearby native ground stitch for reused FAULT In2/In3 transfer; independent trial, no qualification.','routes':[],'vias':[{'net':'GND','position_mm':rows[0]['position_mm'],'diameter_mm':.5,'drill_mm':.3}]}
 with (b/'R141D-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
