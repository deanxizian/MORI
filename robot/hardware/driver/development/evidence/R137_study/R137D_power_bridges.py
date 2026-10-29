"""Read-only 0.50 mm same-layer power repair proposals using existing anchors.

No new vias, no In2 policy additions, no PCB save. Every proposal still requires
native refill and all-net width/reference regression; short does not prove safe.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner

base=Path('robot/.state/c3-completion/trials');out=base/'R137D-power-bridges';out.mkdir(exist_ok=False)
p=Planner(str(base/'R137D/MORI_Interface_C3.kicad_pcb'),.05,['In2.Cu','In3.Cu'],.5);c=p.c;rows=[]
for net in ['MOTION_3V3','/07 {slash} CAM_Protection_Start/CAM_BAT_OUT']:
 gs=p.routing_groups(net);main=max(range(len(gs)),key=lambda i:len(gs[i]['pads']))
 for ly in p.layers:
  represented=unary_union([g['layers'].get(ly,GeometryCollection()) for g in gs])
  missing=c.copper.get((net,ly),GeometryCollection()).difference(represented.buffer(.00001))
  for n,g in enumerate(parts(missing)):
   if g.area>.005:gs.append({'pads':['UNANCHORED_'+ly+'_'+str(n)],'layers':{ly:g}})
 free,vf,blocked,allowed=p.geometry(net);vf=np.zeros(vf.shape,dtype=bool)
 print(json.dumps({'net':net,'main':main,'groups':[g['pads'] for g in gs]}),flush=True)
 for i,g in enumerate(gs):
  if i==main:continue
  result=p.solve(gs[main],g,(free,vf,blocked,allowed),400000)
  row={'net':net,'source_sha256':c.sha,'source_groups':[gs[main]['pads'],g['pads']],'scope':__doc__,'result':result}
  rows.append(row);(out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(json.dumps({'net':net,'group':i,**{k:v for k,v in result.items() if k not in ['routes','activate_pth_layers']}}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
