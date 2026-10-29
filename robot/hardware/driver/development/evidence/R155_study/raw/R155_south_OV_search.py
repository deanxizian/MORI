"""Bounded read-only OV route to its retained southern transfer, avoiding the northern VM regions.

Native refill, power continuity/width, all reference regressions and complete UV
restoration remain mandatory. Existing via centre endpoints are explicit.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials')
rev,name=sys.argv[1:3];layers=sys.argv[3:]
out=b/(name+'.json');assert not out.exists()
p=Planner(b/rev/'MORI_Interface_C3.kicad_pcb',.05,layers,.2)
net='Net-(U1301-INB-_{slash}_OV)'
ends=[(40.75,26.8),(64.275,28.8)]
gs=[{'pads':[],'layers':{ly:Point(pt).buffer(.12) for ly in layers}} for pt in ends]
print(json.dumps({'source':rev,'layers':layers,'endpoint_centres_mm':ends}),flush=True)
r=p.solve(gs[0],gs[1],p.geometry(net),1200000)
out.write_text(json.dumps({'scope':__doc__,'source_sha256':p.c.sha,'net':net,'endpoint_centres_mm':ends,'layers':layers,'result':r,'adopted':False},indent=2)+'\n')
print(json.dumps(r),flush=True)
