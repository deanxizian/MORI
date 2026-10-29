"""Read-only power repair with foreign non-ground fills reserved as hard obstacles.

This deliberately conservative proposal search avoids cutting other power fields.
A no-route result is bounded, not a proof of physical unroutability. Native rules,
full own-face Fab avoidance, reference screening and the 2 mm transition screen
remain unchanged. No board is saved.
"""
import json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
base=Path('robot/.state/c3-completion/trials');out=base/('R139B-power-'+sys.argv[1]);out.mkdir(exist_ok=False)
p=Planner(str(base/'R139B/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','In2.Cu','F.Cu'],.5);c=p.c
net={'ups':'/06 {slash} CAM_Buck/UPS_5V','cam':'/07 {slash} CAM_Protection_Start/CAM_BAT_OUT','motion':'MOTION_3V3'}[sys.argv[1]];free,vf,blocked,allowed=p.geometry(net)
def fab(f):
 ly=pcb.F_Fab if f.GetLayer()==pcb.F_Cu else pcb.B_Fab;lines=[];polys=[]
 for g in f.GraphicalItems():
  if not isinstance(g,pcb.PCB_SHAPE) or g.GetLayer()!=ly:continue
  a,b=xy(g.GetStart()),xy(g.GetEnd())
  if g.GetShape()==pcb.SHAPE_T_SEGMENT:lines.append(LineString([a,b]))
  elif g.GetShape()==pcb.SHAPE_T_RECT:polys.append(box(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])))
  elif g.GetShape()==pcb.SHAPE_T_POLY:polys.append(polyset(g.GetPolyShape()))
 return unary_union(polys+list(polygonize(unary_union(lines))))
bodies={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]) for ly in ['F.Cu','B.Cu']}
reserved={ly:unary_union([g for n,l,g in c.fills if l==ly and n not in ['GND',net]]) for ly in p.layers}
for i,ly in enumerate(p.layers):
 guard=reserved[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+p.width/2+.005)
 blocked[i]=unary_union([blocked[i],guard])
 if ly in bodies:
  own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=unary_union([blocked[i],bodies[ly].buffer(.252).difference(own.buffer(-.001))])
vf &= ~mask(unary_union([g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.255) for ly,g in reserved.items()]),p.xx,p.yy)
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
gs=p.routing_groups(net);main=max(range(len(gs)),key=lambda i:len(gs[i]['pads']));rows=[]
print(json.dumps({'main':main,'groups':[g['pads'] for g in gs]}),flush=True)
for i,g in enumerate(gs):
 if i==main:continue
 result=p.solve(gs[main],g,(free,vf,blocked,allowed),600000)
 row={'net':net,'source_sha256':c.sha,'scope':__doc__,'groups':[gs[main]['pads'],g['pads']],'result':result};rows.append(row)
 (out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps({'group':i,**{k:v for k,v in result.items() if k not in ['routes','activate_pth_layers']}}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
