"""Bounded local gate routing and placement comparison; proposals only."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');width=float(sys.argv[1]);label=sys.argv[2];out=b/(label+'.json');assert not out.exists()
p=Planner('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',.05,['F.Cu','In3.Cu','B.Cu'],width);c=p.c
assert c.sha=='1d32097f2b72c2add4d9a2fd68a2c4ed088b23cbf7606aa1ae3256cc5e48330c'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
net='/16 {slash} Actuator_Direct_Switch/ACT_GATE';gs=p.routing_groups(net)
free,vf,blocked,allowed=p.geometry(net)
window=box(29,5,44.5,20)
for i,ly in enumerate(p.layers):
 if ly in ['F.Cu','B.Cu']:
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
  own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=unary_union([blocked[i],bodies.buffer(width/2+.002).difference(own.buffer(-.001))])
 allowed[i]=allowed[i].intersection(window)
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
rows=[]
for seed in ['Q1602.4','D1602.1']:
 a=next(g for g in gs if 'Q1601.4' in g['pads']);z=next(g for g in gs if seed in g['pads'])
 r=p.solve(a,z,(free,vf,blocked,allowed),350000)
 rows.append({'from':a['pads'],'to':z['pads'],'result':r});print(json.dumps(rows[-1]),flush=True)
# Compare four rotations and small translations of Q1601 against real same-face
# courtyards/pads, without assuming that old power copper may be discarded.
f=next(f for f in c.footprints if f.GetReference()=='Q1601');origin=xy(f.GetPosition());court=polyset(f.GetCourtyard(pcb.F_CrtYd));body=fab(f)
other=unary_union([polyset(q.GetCourtyard(pcb.F_CrtYd)) for q in c.footprints if q.GetReference()!='Q1601' and q.GetLayer()==pcb.F_Cu])
placement=[]
for angle in [0,90,180,270]:
 for dx in [0,.25,.5,.75,1.0]:
  g=translate(rotate(court,-angle,origin=origin),xoff=dx)
  placement.append({'angle_deg':angle,'delta_mm':[dx,0],'same_face_courtyard_overlap_mm2':g.intersection(other).area,'within_board':box(0,0,70,35).covers(g)})
result={'argv':[sys.executable,*sys.argv],'source_sha256':c.sha,'width_mm':width,'window':list(window.bounds),'searches':rows,'Q1601_preliminary_placement':placement,'scope':__doc__}
out.write_text(json.dumps(result,indent=2)+'\n')
print('PLACEMENT',json.dumps(placement),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
