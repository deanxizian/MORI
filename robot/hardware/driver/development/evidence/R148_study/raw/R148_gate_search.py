"""Read-only bounded Q1602 gate proposal on R147L, including native bodies, all holes, old reference and near-ground screening."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R148-gate-search';out.mkdir(exist_ok=False)
p=Planner('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',.05,['F.Cu','B.Cu','In3.Cu'],.2);c=p.c;net='/16 {slash} Actuator_Direct_Switch/ACT_GATE'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)
for k,ly in enumerate(p.layers):
 if ly in ['F.Cu','B.Cu']:
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]);own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);blocked[k]=unary_union([blocked[k],bodies.buffer(.102).difference(own.buffer(-.001))])
window=mask(box(30,4,44,18),p.xx,p.yy,True);free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True)&window for ob,al in zip(blocked,allowed)]);vf &= window
gs=p.routing_groups(net);a=next(g for g in gs if g['pads']==['Q1602.4']);target=next(g for g in gs if 'U1601.6' in g['pads'])
r=p.solve(a,target,(free,vf,blocked,allowed),400000);data={'scope':__doc__,'source_sha256':c.sha,'groups':[a['pads'],target['pads']],'result':r};(out/'search.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
