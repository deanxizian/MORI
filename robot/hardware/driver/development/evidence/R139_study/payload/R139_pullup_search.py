"""Read-only joint D3/CLR search; nominal body checks and native rules retained.

Results are proposals, not acceptance. Full reference and original connections
must still be verified on the actual refilled candidate.
"""
import json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
from plan_existing_copper import groups

base=Path('robot/.state/c3-completion/trials')
revision=sys.argv[1]
out=base/(revision+'-pullup-search');out.mkdir(exist_ok=False)
p=Planner(str(base/revision/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2)
c=p.c
source=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
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
rows=[]
for net in sys.argv[2:] or ['Net-(U1001-D3_{slash}_current_ADC)','/CLR_N','/01 {slash} Core/ACT_CURRENT_ADC']:
 gs=p.routing_groups(net)
 free,vf,blocked,allowed=p.geometry(net)
 blocked=list(blocked)
 for k,ly in enumerate(p.layers):
  if ly in bodies:
   own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
   blocked[k]=unary_union([blocked[k],bodies[ly].buffer(.102).difference(own.buffer(-.001))])
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 if net=='Net-(U1001-D3_{slash}_current_ADC)':
  free[1:]=False;vf=np.zeros(vf.shape,dtype=bool)
 print(json.dumps({'net':net,'groups':[g['pads'] for g in gs]}),flush=True)
 for i,a in enumerate(gs):
  for j,b in enumerate(gs[i+1:],i+1):
   if net=='/CLR_N' and not ('R301.1' in a['pads'] or 'R301.1' in b['pads']):continue
   if net=='/CLR_N' and not any(set(a['pads'])<=set(g['pads']) and set(b['pads'])<=set(g['pads']) for g in groups(source,net)):continue
   r=p.solve(a,b,(free,vf,blocked,allowed),600000)
   row={'net':net,'groups':[a['pads'],b['pads']],'source_sha256':c.sha,'result':r}
   rows.append(row);(out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n')
   print(json.dumps({'net':net,'pair':[i,j],**{k:v for k,v in r.items() if k not in ['routes','activate_pth_layers']}}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
