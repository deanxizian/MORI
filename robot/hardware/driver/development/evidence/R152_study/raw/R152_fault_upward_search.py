"""Bounded FAULT replacement between retained existing vias. No new vias or source save. Native geometry and power/ground qualification remain separate."""
import sys,json,ast
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R152-FAULT-upward-search';out.mkdir(exist_ok=False)
p=Planner(b/'R152F/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','In2.Cu'],.2);c=p.c;net='/FAULT_N'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
ends=[]
for pos in [(44.2,26.825),(45.7,31.4125)]:
 v=next(v for v in c.vias if v.GetNetname()==net and Point(xy(v.GetPosition())).distance(Point(pos))<1e-6)
 ends.append({'pads':[], 'layers':{ly:Point(pos).buffer(.15) for ly in p.layers}})
free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)
for k,ly in enumerate(p.layers):
 if ly in ['F.Cu','B.Cu']:
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]);own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[k]=blocked[k].union(bodies.buffer(.102).difference(own.buffer(-.001)))
vf=np.zeros(vf.shape,dtype=bool)
results=[]
for mode in ['HEAD_BUCK_IN_upper_escape']:
 obs=list(blocked)
 for k,ly in enumerate(p.layers):
  if ly=='In2.Cu':
   power=unary_union([g for n,l,g in c.fills if n=='/09 {slash} Head_Buck/HEAD_BUCK_IN' and l==ly])
   departure=LineString([(44.2,26.825),(44.2,25.3)]).buffer(.13)
   obs[k]=obs[k].union(power.buffer(.405).difference(departure))
 window=box(38,23,50,34.2)
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al.intersection(window),p.xx,p.yy,True) for ob,al in zip(obs,allowed)])
 free[0:2]=False
 print(json.dumps({'phase':'search','mode':mode}),flush=True)
 r=p.solve(ends[0],ends[1],(free,vf,obs,allowed),250000)
 row={'mode':mode,'source_sha256':c.sha,'net':net,'endpoint_centres_mm':[[44.2,26.825],[45.7,31.4125]],'layers':p.layers,'In2_allowed':net in p.in2_nets,'new_vias_allowed':False,'result':r};results.append(row)
 (out/'searches.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(r),flush=True)
 if r['status']=='PROPOSAL':break
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
